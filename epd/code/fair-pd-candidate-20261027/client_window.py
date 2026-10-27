"""Record the calibration client's actual outer perf_counter windows."""
import hashlib
import json
import os
import socket
from pathlib import Path


def load_metadata(args):
    if args.calibration_metadata is None:
        return None
    if (args.warmup, args.requests, args.repetitions) != (4, 16, 1):
        raise ValueError("Calibration client requires exactly 4 warmup and 16 measured requests")
    raw = args.calibration_metadata.read_bytes()
    metadata = json.loads(raw)
    loads = {"C": (1, 128, 8), "D": (8, 128, 8), "E": (8, 32, 8)}
    if loads.get(metadata["load"]) != (args.images, args.tokens, args.concurrency):
        raise ValueError("Calibration load arguments differ from bound metadata")
    if metadata["repeat"] not in (0, 1) or type(metadata["repeat"]) is not int:
        raise ValueError("Calibration repeat must be 0 or 1")
    if not metadata.get("candidate") or not metadata.get("run_id"):
        raise ValueError("Calibration candidate/run identity missing")
    for key in ("candidate_config_sha256", "source_manifest_sha256", "runtime_binding_sha256"):
        digest = metadata[key]
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("Calibration source/config/runtime SHA binding missing")
    if not hasattr(os, "getuid"):
        raise ValueError("Actual calibration client requires the reviewed Linux runtime")
    if (metadata["uid"] != os.getuid() or metadata["host"] != socket.gethostname()
            or metadata["boot_id"] != Path("/proc/sys/kernel/random/boot_id").read_text().strip()):
        raise ValueError("Calibration client UID/host/boot differs from metadata")
    return {**metadata, "calibration_metadata_sha256": hashlib.sha256(raw).hexdigest()}


def write_window(output, metadata, warm_start, warm_end, measure_start, measure_end):
    window = {**metadata, "scope": "calibration_client_window",
              "schema": "calibration-client-window-v1", "clock": "time.perf_counter",
              "warmup_requests": 4, "measured_requests": 16,
              "warmup_start_monotonic": warm_start, "warmup_end_monotonic": warm_end,
              "measurement_start_monotonic": measure_start,
              "measurement_end_monotonic": measure_end,
              "requests_sha256": hashlib.sha256((output / "requests.jsonl").read_bytes()).hexdigest()}
    with (output / "client-window.json").open("x", encoding="utf-8") as file:
        json.dump(window, file, indent=2)
    return window
