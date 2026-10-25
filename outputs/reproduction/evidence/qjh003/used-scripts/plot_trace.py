"""Render a short CUDA-kernel overlap window from the audited trace pair."""
import argparse
import gzip
import json
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analyze_trace import merge


parser = argparse.ArgumentParser()
parser.add_argument("analysis", type=pathlib.Path)
parser.add_argument("trace_directory", type=pathlib.Path)
parser.add_argument("--output", type=pathlib.Path, required=True)
parser.add_argument("--title", required=True)
args = parser.parse_args()
analysis = json.loads(args.analysis.read_text())
intervals = {}
for role in ("encoder", "decoder"):
    filename = pathlib.Path(analysis["roles"][role]["trace"]).name
    with gzip.open(args.trace_directory / filename, "rt") as source:
        trace = json.load(source)
    base = trace["baseTimeNanoseconds"] / 1000
    intervals[role] = merge([(base + event["ts"], base + event["ts"] + event["dur"])
                             for event in trace["traceEvents"] if event.get("cat") == "kernel" and event.get("dur", 0) > 0])
first, second, overlaps = intervals["encoder"], intervals["decoder"], []
i, j = 0, 0
while i < len(first) and j < len(second):
    start, end = max(first[i][0], second[j][0]), min(first[i][1], second[j][1])
    if end > start:
        overlaps.append((start, end))
    if first[i][1] < second[j][1]:
        i += 1
    else:
        j += 1
assert overlaps
center = sum(max(overlaps, key=lambda interval: interval[1] - interval[0])) / 2
origin, limit = center - 1500, center + 1500
fig, axis = plt.subplots(figsize=(11, 2.8), constrained_layout=True)
for position, (role, color) in enumerate([("encoder", "#2563eb"), ("decoder", "#d97706")]):
    bars = [(max(start, origin) - origin, min(end, limit) - max(start, origin))
            for start, end in intervals[role] if end > origin and start < limit]
    axis.broken_barh([(start / 1000, duration / 1000) for start, duration in bars], (position - .28, .56), facecolors=color)
axis.set(yticks=[0, 1], yticklabels=["Encoder kernels", "Decoder kernels"],
         xlabel="Time within selected 3 ms diagnostic window", xlim=(0, 3), title=args.title)
axis.grid(axis="x", alpha=.25)
fig.savefig(args.output, dpi=180)
plt.close(fig)
