"""Check independent images under concurrency and compare greedy outputs."""
import argparse
import asyncio
import json
import pathlib
import re
import aiohttp
from transformers import AutoTokenizer


async def run(args):
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    marker = "<|vision_start|><|image_pad|><|vision_end|>" if "Qwen2-VL" in args.model else "(<image>./</image>)"
    manifest = json.loads((args.dataset / "manifest.json").read_text())
    cases = []
    for color in ("red", "green", "blue", "yellow"):
        cases.append({"id": color, "images": [f"routing_{color}.png"], "expected": [color],
                      "question": "What is the single dominant color of this image? Reply with one color word."})
    cases.append({"id": "four-colors", "images": [f"routing_{color}.png" for color in ("red", "green", "blue", "yellow")],
                  "expected": ["red", "green", "blue", "yellow"],
                  "question": "List the dominant colors of all four images in order. Reply only with comma-separated color names."})
    if "Qwen2-VL" in args.model and not args.color_diagnostic:
        subjects = [("bench", 0), ("dog", 1), ("bear", 2), ("cat", 5)]
        cases = [{"id": subject, "images": [manifest["images"][index]["file"]], "expected_keywords": [subject],
                  "question": "Describe the main subject in this image in one short sentence."}
                 for subject, index in subjects]
        cases.append({"id": "four-coco-subjects", "images": [manifest["images"][index]["file"] for _, index in subjects],
                      "expected_keywords": [subject for subject, _ in subjects], "tokens": 128,
                      "question": "Describe each of the four images separately, in order, using one short sentence per image."})
    for count in (1, 4):
        cases.append({"id": f"coco-{count}", "images": [item["file"] for item in manifest["images"][:count]],
                      "question": manifest["prompt"]})
    concurrent_count = 8 if args.concurrency8_only else 4
    if args.concurrency8_only:
        cases = cases[:4] * 2
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
        async def request(url, case):
            prompt = tokenizer.apply_chat_template([{"role": "user", "content": marker * len(case["images"]) + case["question"]}],
                                                   tokenize=False, add_generation_prompt=True)
            body = {"input": {"prompt": prompt, "multi_modal_data": {"images_paths": [str(args.dataset / name) for name in case["images"]]}},
                    "stream": False, "temperature": 0.0, "max_tokens": case.get("tokens", 32), "ignore_eos": True}
            async with session.post(url + "/generate", json=body) as response:
                text = await response.text()
                if response.status != 200:
                    return {"error": text, "status": response.status}
                return json.loads(text)

        results = []
        # All single-color requests arrive concurrently, followed by multi-image cases.
        targets = await asyncio.gather(*(request(args.url, case) for case in cases[:concurrent_count]))
        golden = json.loads(args.reference_file.read_text()) if args.reference_file else None
        if golden and args.concurrency8_only:
            golden = golden[:4] * 2
        if golden:
            assert [item["case"]["id"] for item in golden] == [case["id"] for case in cases]
            references = [item["reference"] for item in golden[:concurrent_count]]
        else:
            references = await asyncio.gather(*(request(args.reference, case) for case in cases[:concurrent_count]))
        for case in cases[concurrent_count:]:
            targets.append(await request(args.url, case))
            if golden:
                references.append(golden[len(references)]["reference"])
            else:
                references.append(await request(args.reference, case))
        for case, target, reference in zip(cases, targets, references):
            item = {"case": case, "target": target, "reference": reference}
            if "output" in target and "output" in reference:
                item["exact_text_equal"] = target["output"] == reference["output"]
                if "output_token_ids" in target and "output_token_ids" in reference:
                    item["exact_token_ids_equal"] = target["output_token_ids"] == reference["output_token_ids"]
                item["normalized_text_equal"] = tokenizer.decode(tokenizer.encode(target["output"]), skip_special_tokens=True) == reference["output"]
                if "expected" in case:
                    actual = re.findall(r"\b(red|green|blue|yellow)\b", target["output"].lower())
                    expected = case["expected"]
                    item["routing_passed"] = actual[:len(expected)] == expected
                    reference_colors = re.findall(r"\b(red|green|blue|yellow)\b", reference["output"].lower())
                    item["reference_routing_passed"] = reference_colors[:len(expected)] == expected
                if "expected_keywords" in case:
                    def matches(text):
                        locations = [text.lower().find(word) for word in case["expected_keywords"]]
                        return all(position >= 0 for position in locations) and locations == sorted(locations)
                    item["routing_passed"] = matches(target["output"])
                    item["reference_routing_passed"] = matches(reference["output"])
                if "processed_prompt_token_ids" in target and "processed_prompt_token_ids" in reference:
                    item["exact_processed_input_equal"] = target["processed_prompt_token_ids"] == reference["processed_prompt_token_ids"]
                item["reference_quality_limit"] = item.get("reference_routing_passed") is False
                if len(case["images"]) > 1 and item["reference_quality_limit"]:
                    item["engine_check_passed"] = item.get("exact_token_ids_equal", False)
                else:
                    item["engine_check_passed"] = item.get("routing_passed", True)
            results.append(item)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2))
        for item in results:
            print(json.dumps({"case": item["case"]["id"], "routing_passed": item.get("routing_passed"),
                              "reference_routing_passed": item.get("reference_routing_passed"),
                              "exact_text_equal": item.get("exact_text_equal"),
                              "exact_token_ids_equal": item.get("exact_token_ids_equal"),
                              "target": item["target"].get("output", item["target"]),
                              "reference": item["reference"].get("output", item["reference"])}), flush=True)
        first_four_distinct = len({item.get("output") for item in references[:4]}) == 4
        if not first_four_distinct or any("output" not in item["target"] or "output" not in item["reference"]
               or not item.get("engine_check_passed", False)
               for item in results):
            raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    reference = parser.add_mutually_exclusive_group(required=True)
    reference.add_argument("--reference")
    reference.add_argument("--reference-file", type=pathlib.Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--color-diagnostic", action="store_true")
    parser.add_argument("--concurrency8-only", action="store_true")
    asyncio.run(run(parser.parse_args()))
