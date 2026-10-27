"""Print candidate schedules or select calibration settings; never launch a service."""
import argparse
import itertools
import json
import math
import hashlib
from pathlib import Path
from admission import bound_bytes, validate_memory, validate_reference, validate_runtime

LOADS = {"A": (1, 128, 1), "B": (4, 128, 8), "C": (1, 128, 8),
         "D": (8, 128, 8), "E": (8, 32, 8)}
SYSTEMS = ("replicas", "pd", "epd")
CANDIDATES = [(system, p, d, cap)
              for system, p, d in (("replicas", 0, 0), ("pd", 1, 2), ("pd", 2, 1), ("epd", 1, 1))
              for cap in (4, 8)]


def candidate_id(candidate):
    system, p, d, cap = candidate
    return f"{system}-p{p}-d{d}-b{cap}"


def candidate_arguments(candidate):
    system, p, d, cap = candidate
    if system == "replicas":
        return {"entrypoint": "baseline_server.py", "instances": 3,
                "arguments": ["--max-num-seqs", str(cap), "--gpu-memory-utilization", "0.65"]}
    return {"entrypoint": "-m epdserve.api_server", "instances": 1,
            "arguments": (["--pd-fused"] if system == "pd" else []) + [
                "--encoding-data-parallel-size", "0" if system == "pd" else "1",
                "--context-data-parallel-size", str(p), "--decoding-data-parallel-size", str(d),
                "--runtime-max-num-seqs", str(cap), "--encoding-max-batch-size", str(cap),
                "--context-max-batch-size", str(cap), "--decoding-max-batch-size", str(cap),
                "--context-max-tokens-per-batch", "4096", "--decoding-max-tokens-per-batch", "4096",
                "--gpu-memory-utilization", "0.65", "--swap-space", "0",
                "--limit-mm-per-prompt", "8", "--intra-request-dp", "0", "--seed", "0"]}


def config_sha256(candidate):
    return hashlib.sha256(json.dumps(candidate_arguments(candidate), sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def qualification_schedule():
    # Real C8 admission plus one C4 batch and three single-request shape cases.
    cases = (("one", 1, 32, 1, 1), ("four", 4, 128, 1, 1),
             ("eight", 8, 128, 1, 1), ("concurrent8", 8, 32, 8, 8),
             ("concurrent4", 4, 128, 4, 4))
    return [dict(candidate=candidate_id(candidate), case=case, images=images,
                 tokens=tokens, concurrency=concurrency, requests=requests)
            for candidate in CANDIDATES
            for case, images, tokens, concurrency, requests in cases]


def load_qualification(path, candidate, source_sha256, runtime_sha256,
                       inputs_sha256, reference_sha256):
    for value in (source_sha256, runtime_sha256):
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("Qualification requires canonical SHA256 bindings")
    path = Path(path)
    raw = path.read_bytes()
    receipt = json.loads(raw)
    cid = candidate_id(candidate)
    expected = {"candidate": cid, "candidate_config_sha256": config_sha256(candidate),
                "source_manifest_sha256": source_sha256,
                "runtime_binding_sha256": runtime_sha256,
                "scope": "candidate_eligibility_only"}
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("Qualification candidate/profile/source/runtime binding differs")
    log_path = (path.parent / receipt["requests_file"]).resolve()
    if not log_path.is_relative_to(path.parent.resolve()) or log_path.suffix != ".jsonl":
        raise ValueError("Qualification request log must stay in its artifact directory")
    log = log_path.read_bytes()
    if hashlib.sha256(log).hexdigest() != receipt["requests_sha256"]:
        raise ValueError("Qualification raw request SHA differs")
    records = [json.loads(line) for line in log.splitlines() if line.strip()]
    if len(records) > 15 or len({row["request_id"] for row in records}) != len(records):
        raise ValueError("Qualification exceeds budget or repeats request IDs")
    if receipt.get("status") not in ("passed", "failed", "not_run"):
        raise ValueError("Unknown qualification status")
    if receipt["status"] == "not_run" and records:
        raise ValueError("A not-run qualification cannot contain actual requests")
    passed = receipt["status"] == "passed"
    if passed:
        inputs_raw = bound_bytes(path, receipt["inputs_file"], inputs_sha256)
        reference_raw = bound_bytes(path, receipt["reference_file"], reference_sha256)
        if receipt["inputs_sha256"] != inputs_sha256 or receipt["reference_sha256"] != reference_sha256:
            raise ValueError("Qualification input/reference SHA binding differs")
        validate_reference(records, inputs_raw, reference_raw, cid)
        cases = [case for case in qualification_schedule() if case["candidate"] == cid]
        if len(records) != 15:
            raise ValueError("Passing qualification requires all 15 actual requests")
        for case in cases:
            rows = [row for row in records if row["case"] == case["case"]]
            if len(rows) != case["requests"] or any(
                    row.get("success") is not True or row.get("candidate") != cid
                    or row.get("images") != case["images"]
                    or len(row.get("output_token_ids", [])) != case["tokens"]
                    or not row.get("processed_prompt_token_ids") for row in rows):
                raise ValueError("Incomplete or failed actual qualification requests")
            intervals = [(row["submit_monotonic"], row["end_monotonic"]) for row in rows]
            if any(end <= start for start, end in intervals):
                raise ValueError("Invalid qualification timing")
            peak = max(sum(start <= at < end for start, end in intervals)
                       for at, _ in intervals)
            if peak < case["concurrency"]:
                raise ValueError("Qualification did not reach the requested concurrency")
    return {"passed": passed, "receipt_sha256": hashlib.sha256(raw).hexdigest(), **expected}


def calibration_schedule():
    cells = []
    for repeat in range(2):
        order = CANDIDATES if repeat == 0 else list(reversed(CANDIDATES))
        for candidate in order:
            for load in ("C", "D", "E"):
                cells.append(dict(candidate=candidate_id(candidate), repeat=repeat, load=load,
                                  warmup=4, requests=16))
    return cells


def formal_schedule(full=False):
    cells = []
    orders = ("CDE", "DEC", "ECD", "CED", "EDC", "DCE")
    for block, systems in enumerate(itertools.permutations(SYSTEMS)):
        loads = orders[block]
        if full:
            loads = ("AB" if block % 2 == 0 else "BA") + loads
        for system in systems:
            for load in loads:
                cells.append(dict(block=block, system=system, load=load,
                                  warmup=20, requests=100 if full else 50))
    return cells


def select_calibration(rows, qualifications, source_sha256, runtime_sha256,
                       *, runtime, artifact_root):
    validate_runtime(runtime)
    expected = {(cell["candidate"], cell["repeat"], cell["load"])
                for cell in calibration_schedule()}
    by_key = {}
    for row in rows:
        key = row["candidate"], row["repeat"], row["load"]
        if key not in expected or key in by_key:
            raise ValueError("Unknown or duplicate calibration cell")
        by_key[key] = row
    if set(by_key) != expected:
        raise ValueError("All 48 cells must be recorded, including failed/not-run cells")
    scores = {}
    for candidate in CANDIDATES:
        cid = candidate_id(candidate)
        qualification = qualifications.get(cid)
        if qualification is None:
            raise ValueError("Missing exact-candidate qualification receipt")
        if (qualification["source_manifest_sha256"] != source_sha256
                or qualification["runtime_binding_sha256"] != runtime_sha256
                or qualification["candidate_config_sha256"] != config_sha256(candidate)):
            raise ValueError("Qualification profile/source/runtime differs")
        measurements = [by_key[cid, repeat, load] for repeat in range(2) for load in "CDE"]
        if not qualification["passed"]:
            if any(row.get("status") == "ok" for row in measurements):
                raise ValueError("Calibration cannot run before exact-candidate qualification")
            continue
        if any(row.get("status") != "ok" or row.get("failures") != 0
               or row.get("qualification_receipt_sha256") != qualification["receipt_sha256"]
               or row.get("candidate_config_sha256") != config_sha256(candidate)
               or row.get("source_manifest_sha256") != source_sha256
               or row.get("runtime_binding_sha256") != runtime_sha256
               or row.get("warmup_completed") != 4 or row.get("requests_completed") != 16
               or row.get("fixed_output_length") is not True for row in measurements):
            continue
        rates = {}
        for row in measurements:
            evidence = validate_memory(row, config_sha256(candidate), source_sha256, runtime_sha256,
                                       runtime, artifact_root)
            rates[row["repeat"], row["load"]] = evidence["requests_per_s"]
        # Average repeats per load before the geometric mean across loads.
        load_means = [sum(rates[repeat, load] for repeat in range(2)) / 2
                      for load in "CDE"]
        scores[cid] = math.exp(sum(map(math.log, load_means)) / len(load_means))
    selected = {}
    for system in SYSTEMS:
        eligible = [candidate for candidate in CANDIDATES
                    if candidate[0] == system and candidate_id(candidate) in scores]
        if not eligible:
            raise ValueError(f"No valid {system} candidate; formal comparison blocked")
        best = max(scores[candidate_id(candidate)] for candidate in eligible)
        tied = [candidate for candidate in eligible if scores[candidate_id(candidate)] >= best / 1.03]
        chosen = min(tied, key=lambda candidate: (candidate[3], candidate[1]))
        selected[system] = {"candidate": candidate_id(chosen), "score": scores[candidate_id(chosen)]}
    return {"selected": selected, "all_eligible_scores": scores,
            "formal_admission": "blocked_pending_selected_config_full_G3",
            "required_full_G3": {system: {"candidate": value["candidate"],
                "requests": 120, "source_manifest_sha256": source_sha256,
                "runtime_binding_sha256": runtime_sha256,
                "candidate_config_sha256": config_sha256(next(candidate for candidate in CANDIDATES
                    if candidate_id(candidate) == value["candidate"]))}
                for system, value in selected.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--select", type=Path, help="calibration rows JSON; no GPU work")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    if args.select:
        payload = json.loads(args.select.read_text(encoding="utf-8"))
        source, runtime = payload["source_manifest_sha256"], payload["runtime_binding_sha256"]
        runtime_data = json.loads(bound_bytes(args.select, payload["runtime_binding_file"], runtime))
        inputs_sha256, reference_sha256 = payload["qualification_inputs_sha256"], payload["qualification_reference_sha256"]
        qualifications = {candidate_id(candidate): load_qualification(
            args.select.parent / payload["qualification_receipts"][candidate_id(candidate)],
            candidate, source, runtime, inputs_sha256, reference_sha256) for candidate in CANDIDATES}
        result = select_calibration(payload["rows"], qualifications, source, runtime,
                                    runtime=runtime_data, artifact_root=args.select.parent)
    else:
        result = {
        "state": "candidate_only_no_GPU_authorization", "loads": LOADS,
        "candidate_arguments": {candidate_id(candidate): candidate_arguments(candidate) for candidate in CANDIDATES},
        "qualification": qualification_schedule(),
        "calibration": calibration_schedule(), "formal_separate": formal_schedule(args.full)}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
