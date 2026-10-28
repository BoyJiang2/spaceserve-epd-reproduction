"""Read only bound CPU artifacts; no NVML, model imports or GPU operations."""
import hashlib
import json
import math
from pathlib import Path


def bound_bytes(owner, filename, expected_sha256):
    root = Path(owner).resolve().parent
    path = (root / filename).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Bound artifact must stay in its artifact directory")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Bound artifact SHA256 differs")
    return raw


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"Invalid {name}: integer required")
    return value


def timestamp(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Invalid finite monotonic timestamp")
    return value


def validate_runtime(runtime):
    integer(runtime["uid"], "UID")
    if any(type(runtime.get(key)) is not str or not runtime[key] for key in ("host", "boot_id")):
        raise ValueError("Runtime host/boot binding missing")
    capacities = runtime["gpu_capacity_bytes"]
    if len(capacities) != 3 or any(not uuid for uuid in capacities):
        raise ValueError("Runtime must bind exactly three GPU UUIDs")
    for capacity in capacities.values():
        integer(capacity, "capacity bytes", 1)
    if runtime["memory_limit_fraction"] != 0.65 or runtime["memory_sample_max_gap_s"] != 1.0:
        raise ValueError("Memory cap/sampling policy differs from frozen plan")
    if set(runtime["gpu_admission_free_bytes"]) != set(capacities) or set(runtime["gpu_memory_cap_bytes"]) != set(capacities):
        raise ValueError("Available memory cap must bind all three GPU UUIDs")
    for uuid, capacity in capacities.items():
        available = integer(runtime["gpu_admission_free_bytes"][uuid], "admission free bytes")
        cap = integer(runtime["gpu_memory_cap_bytes"][uuid], "available cap bytes", 1)
        if available > capacity or cap != min(capacity * 65 // 100, available):
            raise ValueError("Available memory cap differs from frozen capacity/free-byte policy")


def validate_memory(row, candidate_config_sha256, source_sha256, runtime_sha256,
                    runtime, artifact_root):
    validate_runtime(runtime)
    # Memory evidence is required for every successful warmup/measurement cell.
    path = Path(artifact_root) / row["memory_receipt_file"]
    raw = bound_bytes(Path(artifact_root) / "selection.json", row["memory_receipt_file"],
                      row["memory_receipt_sha256"])
    receipt = json.loads(raw)
    expected = {"candidate": row["candidate"], "repeat": row["repeat"], "load": row["load"],
                "candidate_config_sha256": candidate_config_sha256,
                "source_manifest_sha256": source_sha256, "runtime_binding_sha256": runtime_sha256,
                "scope": "calibration_memory", "host": runtime["host"],
                "boot_id": runtime["boot_id"], "uid": runtime["uid"], "unit": "bytes"}
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("Memory candidate/interval/host/UID/source/runtime/unit binding differs")
    if type(receipt.get("run_id")) is not str or not receipt["run_id"] or receipt["run_id"] != row["run_id"]:
        raise ValueError("Memory RUNID differs")
    start, end = timestamp(receipt["start_monotonic"]), timestamp(receipt["end_monotonic"])
    if start != timestamp(row["warmup_start_monotonic"]) or end != timestamp(row["measure_end_monotonic"]) or end <= start:
        raise ValueError("Memory interval must cover the complete warmup/measurement cell")
    requests_raw = bound_bytes(path, receipt["requests_file"], receipt["requests_sha256"])
    requests = [json.loads(line) for line in requests_raw.splitlines() if line.strip()]
    window_raw = bound_bytes(path, receipt["client_window_file"], receipt["client_window_sha256"])
    window = json.loads(window_raw)
    window_expected = {**expected, "scope": "calibration_client_window",
                       "schema": "calibration-client-window-v1", "clock": "time.perf_counter",
                       "run_id": receipt["run_id"], "requests_sha256": receipt["requests_sha256"],
                       "warmup_requests": 4, "measured_requests": 16}
    window_expected.pop("unit")
    if any(window.get(key) != value for key, value in window_expected.items()):
        raise ValueError("Client window clock/host/identity/request raw binding differs")
    warm_start, warm_end = timestamp(window["warmup_start_monotonic"]), timestamp(window["warmup_end_monotonic"])
    measure_start = timestamp(window["measurement_start_monotonic"])
    measure_end = timestamp(window["measurement_end_monotonic"])
    if not warm_start < warm_end <= measure_start < measure_end:
        raise ValueError("Invalid client outer warmup/measurement windows")
    if start != warm_start or end != measure_end or measure_start != timestamp(row["measurement_start_monotonic"]):
        raise ValueError("Memory interval differs from bound client outer windows")
    if len(requests) != 20 or len({record["request_id"] for record in requests}) != 20:
        raise ValueError("Calibration memory requires the 4+16 actual request interval")
    warm, measured = [], []
    for record in requests:
        if (any(record.get(key) != row[key] for key in ("candidate", "repeat", "load", "run_id"))
                or record.get("success") is not True or type(record.get("warmup")) is not bool):
            raise ValueError("Calibration request identity/phase/status differs")
        interval = timestamp(record["submit_monotonic"]), timestamp(record["end_monotonic"])
        if interval[1] <= interval[0]:
            raise ValueError("Invalid calibration raw request interval")
        (warm if record["warmup"] else measured).append(interval)
    if (len(warm) != 4 or len(measured) != 16
            or any(a < warm_start or b > warm_end for a, b in warm)
            or any(a < measure_start or b > measure_end for a, b in measured)):
        raise ValueError("Memory interval differs from actual warmup/measurement raw requests")
    derived_rate = 16 / (measure_end - measure_start)
    if (type(row.get("requests_per_s")) not in (int, float)
            or not math.isfinite(row["requests_per_s"])
            or not math.isclose(row["requests_per_s"], derived_rate, rel_tol=1e-9, abs_tol=1e-12)):
        raise ValueError("Summary requests_per_s differs from actual client outer-window 16/duration")
    registry_raw = bound_bytes(path, receipt["process_registry_file"], receipt["process_registry_sha256"])
    registry = json.loads(registry_raw)
    if any(registry.get(key) != receipt[key] for key in ("run_id", "uid", "host", "boot_id")):
        raise ValueError("Process registry UID/RUNID/host/boot differs")
    capacities = runtime["gpu_capacity_bytes"]
    owned = {uuid: {} for uuid in capacities}
    for process in registry["processes"]:
        uuid = process["gpu_uuid"]
        if uuid not in owned or integer(process["uid"], "process UID") != runtime["uid"] or process["run_id"] != receipt["run_id"]:
            raise ValueError("Foreign process registry attribution")
        pid = integer(process["pid"], "PID", 1)
        ticks = integer(process["proc_start_ticks"], "process start ticks", 1)
        if pid in owned[uuid]:
            raise ValueError("Duplicate process registry entry")
        owned[uuid][pid] = ticks
    if any(not processes for processes in owned.values()):
        raise ValueError("Each GPU requires a bound owned process")
    samples_raw = bound_bytes(path, receipt["samples_file"], receipt["samples_sha256"])
    samples = [json.loads(line) for line in samples_raw.splitlines() if line.strip()]
    times, peaks = {uuid: [] for uuid in capacities}, {uuid: 0 for uuid in capacities}
    for sample in samples:
        uuid = sample["gpu_uuid"]
        if uuid not in capacities or sample.get("unit") != "bytes":
            raise ValueError("Unknown GPU UUID or illegal memory unit")
        if type(sample["capacity_bytes"]) is not int or sample["capacity_bytes"] != capacities[uuid]:
            raise ValueError("Memory sample capacity differs")
        at = timestamp(sample["monotonic_s"])
        if at < start - 1 or at > end + 1:
            raise ValueError("Memory sample lies outside the bound interval")
        used = integer(sample["device_used_bytes"], "device used bytes")
        total, seen = 0, set()
        for process in sample["processes"]:
            pid = integer(process["pid"], "PID", 1)
            if (pid in seen or pid not in owned[uuid] or integer(process["uid"], "sample UID") != runtime["uid"]
                    or process["run_id"] != receipt["run_id"]
                    or integer(process["proc_start_ticks"], "sample process start ticks", 1) != owned[uuid][pid]):
                raise ValueError("Foreign/reused PID or UID/RUNID memory attribution")
            seen.add(pid)
            total += integer(process["used_bytes"], "process used bytes")
        if seen != set(owned[uuid]) or used < total:
            raise ValueError("Incomplete process memory attribution")
        cap = runtime["gpu_memory_cap_bytes"][uuid]
        if used > cap or total > cap:
            raise ValueError("Actual sampled GPU memory exceeds the per-GPU cap")
        peaks[uuid] = max(peaks[uuid], used)
        times[uuid].append(at)
    for uuid, stamps in times.items():
        if not stamps or stamps != sorted(set(stamps)) or stamps[0] > start or stamps[-1] < end:
            raise ValueError("Memory samples do not cover the complete cell interval")
        if any(b - a > 1.0 for a, b in zip(stamps, stamps[1:])):
            raise ValueError("Memory sampling gap exceeds one second")
    return {"sampled_peaks_bytes": peaks, "requests_per_s": derived_rate}


def validate_reference(records, inputs_raw, reference_raw, candidate):
    fixtures = json.loads(inputs_raw)["fixtures"]
    reference = [json.loads(line) for line in reference_raw.splitlines() if line.strip()]
    expected = {fixture["fixture_id"]: fixture for fixture in fixtures}
    refs = {row["fixture_id"]: row for row in reference}
    actual = {row["fixture_id"]: row for row in records}
    if len(fixtures) != 15 or len(reference) != 15 or len(refs) != 15 or len(actual) != 15 or set(expected) != set(refs) or set(expected) != set(actual):
        raise ValueError("Qualification/reference fixture IDs differ or repeat")
    for key, fixture in expected.items():
        row, ref = actual[key], refs[key]
        data = fixture["input"]
        if type(data["prompt"]) is not str or not data["prompt"] or len(data["images"]) != row["images"]:
            raise ValueError("Invalid actual prompt/image fixture")
        for image in data["images"]:
            if (type(image["path"]) is not str or not image["path"]
                    or len(image["rgb_sha256"]) != 64
                    or any(ch not in "0123456789abcdef" for ch in image["rgb_sha256"])):
                raise ValueError("Invalid ordered image/RGB fixture")
        if ref["candidate"] != "replicas-p0-d0-b4" or row["candidate"] != candidate:
            raise ValueError("Qualification reference must be actual native replica S records")
        if row.get("success") is not True or ref.get("success") is not True:
            raise ValueError("Failed qualification/reference request")
        for record in (row, ref):
            if record["case"] != fixture["case"] or record["input"] != fixture["input"]:
                raise ValueError("Actual prompt or ordered image/RGB input differs from fixture")
            for field in ("processed_prompt_token_ids", "output_token_ids"):
                ids = record[field]
                if not ids or any(type(token) is not int or token < 0 for token in ids):
                    raise ValueError("Actual processed/output token IDs are invalid")
            if len(record["output_token_ids"]) != fixture["output_tokens"]:
                raise ValueError("Actual fixed output length differs")
        if (row["processed_prompt_token_ids"] != ref["processed_prompt_token_ids"]
                or row["output_token_ids"] != ref["output_token_ids"]):
            raise ValueError("Actual processed/output token IDs differ from bound native reference")
