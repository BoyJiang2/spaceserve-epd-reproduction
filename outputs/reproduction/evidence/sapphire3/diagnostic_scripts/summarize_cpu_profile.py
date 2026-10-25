import json
import pathlib
import pstats
import sys

root = pathlib.Path(sys.argv[1])
stats = pstats.Stats(str(root / "results/epd-parent-profile.pstats"))
rows = [{"file": key[0], "line": key[1], "function": key[2], "primitive_calls": value[0],
         "calls": value[1], "self_seconds": value[2], "cumulative_seconds": value[3]}
        for key, value in stats.stats.items()]
result = {"total_calls": stats.total_calls, "total_seconds": stats.total_tt,
          "top_self": sorted(rows, key=lambda row: row["self_seconds"], reverse=True)[:30],
          "top_cumulative": sorted(rows, key=lambda row: row["cumulative_seconds"], reverse=True)[:35]}
(root / "results/epd-parent-profile-analysis.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
