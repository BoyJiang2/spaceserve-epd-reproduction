"""Audit completed matrices, aggregate raw records, and render comparison plots."""
import argparse
import csv
import json
import pathlib
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from audit_matrix import audit


EXPECTED = {
    "epd-l20": False, "baseline-epd-l20": False,
    "baseline-space-4090-mps": False, "space-4090-mps": False,
    "baseline-space-l20-mps": True, "space-l20-mps": True, "space-mask-l20-mps": True,
}


def quantile(values, fraction):
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    low = int(index)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (index - low)


def collect(matrix):
    audit(matrix, EXPECTED[matrix.name])
    validity_path = matrix / "validity.json"
    validity = json.loads(validity_path.read_text()) if validity_path.exists() else {"status": "unreviewed"}
    memory = [json.loads(line) for line in (matrix / "gpu-memory.jsonl").read_text().splitlines()]
    runtime = json.loads((matrix / "runtime-config.json").read_text())
    expected_version = "0.6.1.post2" if "epd" in matrix.name else "0.7.2"
    assert runtime["packages"]["vllm"] == expected_version, (matrix, runtime["packages"])
    expected_gpus = 3 if "epd" in matrix.name else 1
    assert len(runtime["devices"].split(",")) == expected_gpus
    if "space" in matrix.name:
        assert all(server["environment"]["CUDA_MPS_PIPE_DIRECTORY"] for server in runtime["servers"])
    result = []
    for case in sorted(matrix.glob("images*-c*")):
        if not case.is_dir():
            continue
        config = json.loads((case / "config.json").read_text())
        assert len(config["urls"]) == (3 if matrix.name == "baseline-epd-l20" else 1)
        all_rows = [json.loads(line) for line in (case / "requests.jsonl").read_text().splitlines()]
        rows = [row for row in all_rows if not row["warmup"]]
        summaries = json.loads((case / "summary.json").read_text())
        start = min(row["submission_perf_counter"] for row in all_rows)
        end = summaries[-1]["end_perf_counter"]
        samples = [item for item in memory if start <= item["perf_counter"] <= end]
        assert samples
        record = {"role": matrix.name, "images": config["images"], "concurrency": config["concurrency"],
                  "result_validity": validity["status"],
                  "requests": len(rows), "successes": sum(row["success"] for row in rows),
                  "failure_rate": 1 - sum(row["success"] for row in rows) / len(rows),
                  "assigned_gpu_count": len(runtime["devices"].split(",")),
                  "vllm": runtime["packages"]["vllm"], "model": pathlib.Path(config["model"]).name,
                  "visual_tokens": sorted({row["visual_tokens"] for row in rows}),
                  "output_tokens": sorted({row["output_tokens"] for row in rows}),
                  "request_throughput_mean": statistics.mean(item["requests_per_s"] for item in summaries),
                  "request_throughput_sd": statistics.stdev(item["requests_per_s"] for item in summaries),
                  "output_tokens_per_s_mean": statistics.mean(item["output_tokens_per_s"] for item in summaries),
                  "output_tokens_per_s_sd": statistics.stdev(item["output_tokens_per_s"] for item in summaries),
                  "sampled_physical_memory_peak_gib": max(sum(gpu["physical_used_bytes"] for gpu in item["gpus"]) for item in samples) / 2 ** 30,
                  "memory_sampling_interval_median_s": statistics.median(second["perf_counter"] - first["perf_counter"] for first, second in zip(samples, samples[1:])),
                  "repetitions": summaries}
        for metric in ("latency_s", "ttft_s", "tpot_s"):
            for label, fraction in (("p50", .5), ("p95", .95)):
                record[metric.replace("_s", "") + "_" + label + "_ms"] = quantile([row[metric] for row in rows], fraction) * 1000
        pairs = {"encoding_ms": ("encoding_begin", "encoding_end"),
                 "embedding_migration_ms": ("encoding_migration_begin", "encoding_migration_end"),
                 "prefill_ms": ("context_begin", "context_end"), "kv_migration_ms": ("migration_begin", "migration_end")}
        for label, (first, last) in pairs.items():
            values = []
            for row in rows:
                events = {item["event_type"]: item["timestamp"] for item in row["response"].get("lifetime_events", [])}
                if first in events and last in events:
                    values.append((events[last] - events[first]) * 1000)
            if values:
                record[label + "_median"] = statistics.median(values)
        result.append(record)
    return result


def compare_plot(rows, roles, title, destination):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    colors = ["#4b5563", "#2563eb", "#d97706"]
    metrics = [("output_tokens_per_s_mean", "Output throughput (tokens/s)"),
               ("ttft_p95_ms", "TTFT p95 (ms, server token time)"), ("tpot_p95_ms", "TPOT p95 (ms)")]
    for role_index, (role, label) in enumerate(roles):
        for images in (1, 4):
            points = sorted([row for row in rows if row["role"] == role and row["images"] == images], key=lambda row: row["concurrency"])
            if not points:
                continue
            for axis, (metric, ylabel) in zip(axes, metrics):
                x, y = [row["concurrency"] for row in points], [row[metric] for row in points]
                options = dict(marker="o", linestyle="-" if images == 1 else "--", color=colors[role_index], label=f"{label}, {images} image(s)")
                if metric == "output_tokens_per_s_mean":
                    axis.errorbar(x, y, yerr=[row["output_tokens_per_s_sd"] for row in points], capsize=3, **options)
                else:
                    axis.plot(x, y, **options)
                axis.set(xlabel="Concurrency", ylabel=ylabel, xticks=[1, 4, 8])
                axis.grid(alpha=.25)
    for axis in axes:
        axis.set_ylim(bottom=0)
    axes[0].legend(fontsize=8)
    if any(row.get("result_validity") == "diagnostic_only" for row in rows if row["role"] in [role for role, _ in roles]):
        title += "\nDIAGNOSTIC ONLY: peer-copy data validation failed"
    fig.suptitle(title)
    fig.savefig(destination, dpi=170)
    plt.close(fig)


def l20_plot(rows, destination):
    roles = [("baseline-space-l20-mps", "vLLM"), ("space-l20-mps", "SpaceServe"), ("space-mask-l20-mps", "SpaceServe + mask")]
    if not all(any(row["role"] == role for row in rows) for role, _ in roles):
        return
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    for metric_index, (metric, ylabel) in enumerate([("output_tokens_per_s_mean", "Output tokens/s"), ("ttft_p95_ms", "TTFT p95 (ms)"), ("tpot_p95_ms", "TPOT p95 (ms)")]):
        for offset, (role, label) in enumerate(roles):
            points = [next(row for row in rows if row["role"] == role and row["images"] == images and row["concurrency"] == concurrency) for images, concurrency in [(1, 1), (4, 8)]]
            axes[metric_index].bar([position + (offset - 1) * .24 for position in (0, 1)], [row[metric] for row in points], width=.23, label=label)
        axes[metric_index].set(xticks=[0, 1], xticklabels=["1 image / C=1", "4 images / C=8"], ylabel=ylabel)
        axes[metric_index].grid(axis="y", alpha=.25)
    axes[0].legend(fontsize=8)
    fig.suptitle("Qwen2-VL-2B on one L20: MPS enabled for every role")
    fig.savefig(destination, dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", type=pathlib.Path, nargs="+")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--require-all", action="store_true")
    args = parser.parse_args()
    matrices = {}
    for root in args.roots:
        for directory in root.iterdir():
            if directory.name in EXPECTED and (directory / "COMPLETED").exists():
                assert directory.name not in matrices, "duplicate matrix"
                matrices[directory.name] = directory
    if args.require_all:
        assert set(matrices) == set(EXPECTED), f"missing matrices: {set(EXPECTED) - set(matrices)}"
    rows = [row for matrix in matrices.values() for row in collect(matrix)]
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(rows, indent=2))
    if rows:
        fields = sorted({key for row in rows for key in row if key != "repetitions"})
        with (args.output / "summary.csv").open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows({key: row.get(key) for key in fields} for row in rows)
    for roles, title, filename in [
        ([("baseline-epd-l20", "Three full replicas"), ("epd-l20", "EPD 1:1:1")], "MiniCPM-V-2.6 on three L20 GPUs", "epd-l20.png"),
        ([("baseline-space-4090-mps", "vLLM"), ("space-4090-mps", "SpaceServe")], "Qwen2-VL-2B on one RTX 4090 (MPS)", "spaceserve-4090.png"),
    ]:
        if all(role in matrices for role, _ in roles):
            compare_plot(rows, roles, title, args.output / filename)
    l20_plot(rows, args.output / "spaceserve-l20.png")
    print(json.dumps({"matrices": sorted(matrices), "cases": len(rows), "measured_requests": sum(row["requests"] for row in rows)}, indent=2))


if __name__ == "__main__":
    main()
