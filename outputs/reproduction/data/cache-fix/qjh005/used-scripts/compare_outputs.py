"""Compare paired formal inputs and generated token IDs without inference traffic."""
import argparse
import json
import pathlib


parser = argparse.ArgumentParser()
parser.add_argument("roots", nargs="+", type=pathlib.Path)
parser.add_argument("--output", required=True, type=pathlib.Path)
args = parser.parse_args()
matrices = {directory.name: directory for root in args.roots for directory in root.iterdir()
            if directory.is_dir() and (directory / "COMPLETED").exists()}
pairs = [("baseline-space-4090-mps", "space-4090-mps"),
         ("baseline-epd-l20", "epd-l20"),
         ("baseline-space-l20-mps", "space-l20-mps"),
         ("baseline-space-l20-mps", "space-mask-l20-mps")]


def measured(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    return {(row["repetition"], row["index"]): row for row in rows if not row["warmup"]}


def repeated_input_variation(rows):
    outputs = {}
    for row in rows.values():
        key = tuple(pathlib.Path(path).name for path in row["images"])
        outputs.setdefault(key, set()).add(tuple(row["response"]["output_token_ids"]))
    return {"image_sequences": len(outputs), "with_multiple_outputs": sum(len(values) > 1 for values in outputs.values())}


results = []
for baseline, target in pairs:
    for case in sorted(matrices[target].glob("images*-c*")):
        references = measured(matrices[baseline] / case.name / "requests.jsonl")
        candidates = measured(case / "requests.jsonl")
        assert references.keys() == candidates.keys() and len(candidates) == 300
        differences = []
        for key, candidate in candidates.items():
            reference = references[key]
            assert [pathlib.Path(path).name for path in reference["images"]] == [pathlib.Path(path).name for path in candidate["images"]]
            assert reference["response"]["processed_prompt_token_ids"] == candidate["response"]["processed_prompt_token_ids"], (target, case.name, key)
            if reference["response"]["output_token_ids"] != candidate["response"]["output_token_ids"]:
                differences.append({"repetition": key[0], "index": key[1]})
        results.append({"baseline": baseline, "target": target, "case": case.name,
                        "requests": len(candidates), "processed_inputs_equal": len(candidates),
                        "exact_output_token_ids_equal": len(candidates) - len(differences),
                        "baseline_repeated_input_variation": repeated_input_variation(references),
                        "target_repeated_input_variation": repeated_input_variation(candidates),
                        "different_output_requests": differences})
assert len(results) == 16
args.output.write_text(json.dumps(results, indent=2))
print(json.dumps({"paired_configurations": len(results), "paired_requests": sum(row["requests"] for row in results),
                  "exact_output_matches": sum(row["exact_output_token_ids_equal"] for row in results)}, indent=2))
