import collections
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
path = next((root / "results/epd-restart-profile").glob("*.json"))
trace = json.loads(path.read_text())
totals, counts = collections.Counter(), collections.Counter()
for event in trace["traceEvents"]:
    if event.get("ph") == "X" and event.get("dur", 0) > 0:
        key = (event.get("cat", ""), event["name"])
        totals[key] += event["dur"]
        counts[key] += 1
result = {"trace": path.name, "top_kernels": [{"name": name, "total_ms": value / 1000, "calls": counts[cat, name]}
          for (cat, name), value in totals.most_common() if cat == "kernel"][:15],
          "top_runtime_calls": [{"name": name, "total_ms": value / 1000, "calls": counts[cat, name]}
          for (cat, name), value in totals.most_common() if cat == "cuda_runtime"][:15]}
events = [event for event in trace["traceEvents"] if event.get("ph") == "X" and event.get("dur", 0) > 0]
result["span_ms"] = (max(event["ts"] + event["dur"] for event in events) - min(event["ts"] for event in events)) / 1000
result["top_cpu_ops"] = [{"name": name, "total_ms": value / 1000, "calls": counts[cat, name]} for (cat, name), value in totals.most_common() if cat == "cpu_op"][:12]
(root / "results/epd-profile-analysis.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
