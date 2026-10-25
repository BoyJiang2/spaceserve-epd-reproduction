import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
for directory in ("formal/epd-l20/images1-c1", "epd-c8-warmup", "epd-parent-profile-request", "epd-rpc-split-request"):
    path = root / "results" / directory / "requests.jsonl"
    if not path.exists():
        continue
    for row in [json.loads(line) for line in path.read_text().splitlines()][:2]:
        response = row.get("response", {})
        events = {event["event_type"]: event["timestamp"] for event in response.get("lifetime_events", [])}
        spans = {}
        for first, last in [("encoding_begin", "encoding_end"), ("context_begin", "context_end"),
                            ("migration_begin", "migration_end"), ("encoding_migration_begin", "encoding_migration_end")]:
            if first in events and last in events:
                spans[first] = events[last] - events[first]
        stamps = response.get("timestamps", [])
        gaps = [b-a for a, b in zip(stamps, stamps[1:])]
        print(json.dumps({"directory": directory, "index": row["index"], "e2e_s": row.get("latency_s"), "stages_s": spans,
                          "first_gap_s": gaps[0] if gaps else None, "maximum_gap_s": max(gaps) if gaps else None,
                          "mean_remaining_gap_s": sum(gaps[1:])/len(gaps[1:]) if len(gaps)>1 else None}))
