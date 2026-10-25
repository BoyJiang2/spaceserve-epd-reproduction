"""Verify raw data against the requested experiment before accepting a matrix."""
import argparse
import datetime
import json
import pathlib


def audit(directory, validation_only=False, low_load_only=False):
    assert not (validation_only and low_load_only)
    expected = [(1, 1), (4, 8)] if validation_only else [(images, concurrency) for images in (1, 4) for concurrency in (1, 4, 8)]
    if low_load_only:
        expected = [(1, 1)]
    memory = [json.loads(line) for line in (directory / "gpu-memory.jsonl").read_text().splitlines()]
    assert memory, "GPU memory samples missing"
    verified = []
    for images, concurrency in expected:
        case = directory / f"images{images}-c{concurrency}"
        config = json.loads((case / "config.json").read_text())
        assert (config["images"], config["concurrency"], config["tokens"], config["warmup"], config["requests"], config["repetitions"]) == (images, concurrency, 128, 20, 100, 3), case
        rows = [json.loads(line) for line in (case / "requests.jsonl").read_text().splitlines()]
        warm = [row for row in rows if row["warmup"]]
        measured = [row for row in rows if not row["warmup"]]
        assert len(rows) == 320 and len(warm) == 20 and len(measured) == 300, (case, len(rows))
        expected_visual = (64 if "MiniCPM" in config["model"] else 256) * images
        for row in rows:
            assert row["success"] and row["output_tokens"] == 128, (case, row["index"])
            assert len(row["images"]) == images and len(set(row["images"])) == images
            assert row["visual_tokens"] == expected_visual, (case, row.get("visual_tokens"))
            response = row["response"]
            assert len(response["output_token_ids"]) == 128 and len(response["timestamps"]) == 128
            assert all(first <= second for first, second in zip(response["timestamps"], response["timestamps"][1:]))
            assert row["ttft_s"] >= 0 and row["tpot_s"] > 0 and row["latency_s"] >= row["ttft_s"]
        summaries = json.loads((case / "summary.json").read_text())
        assert len(summaries) == 3
        for repetition in range(3):
            group = [row for row in measured if row["repetition"] == repetition]
            assert sorted(row["index"] for row in group) == list(range(100))
            summary = summaries[repetition]
            assert summary["requests"] == summary["successes"] == 100 and summary["failure_rate"] == 0
            assert summary["duration_s"] > 0
            assert abs(summary["output_tokens_per_s"] - 12800 / summary["duration_s"]) < 1e-6
            assert any(summary["start_perf_counter"] <= item["perf_counter"] <= summary["end_perf_counter"] for item in memory), "no memory sample during repetition"
        verified.append({"images": images, "concurrency": concurrency, "warmup_requests": 20, "measured_requests": 300,
                         "repetitions": 3, "output_tokens_per_request": 128, "visual_tokens_per_request": expected_visual})
    return {"audited_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "directory": str(directory),
            "audit_scope": "Request completion, protocol coverage, and data format; not peer-copy correctness or performance validity",
            "passed": True, "cases": verified, "measured_requests": len(verified) * 300, "gpu_memory_samples": len(memory)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=pathlib.Path)
    parser.add_argument("--validation-only", action="store_true")
    parser.add_argument("--low-load-only", action="store_true")
    parser.add_argument("--write-completed", action="store_true")
    args = parser.parse_args()
    result = audit(args.directory, args.validation_only, args.low_load_only)
    (args.directory / "audit.json").write_text(json.dumps(result, indent=2))
    if args.write_completed:
        (args.directory / "COMPLETED").write_text(json.dumps({"completion_basis": "independent full raw-data audit", "audited_utc": result["audited_utc"]}))
    print(json.dumps(result, indent=2))
