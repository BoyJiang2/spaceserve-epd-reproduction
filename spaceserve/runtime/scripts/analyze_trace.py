"""Check encoder/decoder kernel overlap using two Kineto CUDA timelines."""
import argparse
import gzip
import json
import pathlib
import re


def merge(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=pathlib.Path)
    parser.add_argument("--server-log", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    log = args.server_log.read_text()
    pids = {role: int(re.findall(label + r" is (\d+)", log)[-1])
            for role, label in [("encoder", "EncoderProcess"), ("decoder", "EngineCore")]}
    records, intervals = {}, {}
    for role, pid in pids.items():
        files = list(args.directory.glob(f"*_{pid}.*.pt.trace.json.gz"))
        assert len(files) == 1, (role, pid, files)
        with gzip.open(files[0], "rt") as source:
            trace = json.load(source)
        assert "baseTimeNanoseconds" in trace, "Cannot align clocks without Kineto baseTimeNanoseconds"
        base_us = trace["baseTimeNanoseconds"] / 1000
        kernels = [event for event in trace["traceEvents"] if event.get("cat") == "kernel" and event.get("dur", 0) > 0]
        assert kernels, f"no CUDA kernels in {files[0]}"
        intervals[role] = merge([(base_us + event["ts"], base_us + event["ts"] + event["dur"]) for event in kernels])
        records[role] = {"pid": pid, "trace": str(files[0]), "base_time_ns": trace["baseTimeNanoseconds"],
                         "cuda_kernels": len(kernels), "kernel_name_examples": sorted({event["name"] for event in kernels})[:8],
                         "context_ids": sorted({str(event.get("args", {}).get("context")) for event in kernels}),
                         "gpu_active_us": sum(end - start for start, end in intervals[role])}
    first, second = intervals["encoder"], intervals["decoder"]
    i, j, overlap, examples = 0, 0, 0, []
    while i < len(first) and j < len(second):
        start, end = max(first[i][0], second[j][0]), min(first[i][1], second[j][1])
        if end > start:
            overlap += end - start
            if len(examples) < 10:
                examples.append([start, end])
        if first[i][1] < second[j][1]:
            i += 1
        else:
            j += 1
    result = {"clock_alignment": "Kineto baseTimeNanoseconds / 1000 + event ts (microseconds)",
              "roles": records, "kernel_overlap_us": overlap, "overlap_examples_absolute_us": examples,
              "kernel_overlap_observed": overlap > 0,
              "encoder_active_fraction_overlapping_decoder": overlap / records["encoder"]["gpu_active_us"]}
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
