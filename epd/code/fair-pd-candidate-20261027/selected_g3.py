"""Consume original independently reviewed full selected-three G3 evidence.

Does not author a G3 approval or admit formal work. All evidence paths are bound.
"""
import json
import math
from collections import Counter
from urllib.parse import urlsplit

from admission import bound_bytes, integer, timestamp, validate_runtime
from experiment_plan import CANDIDATES, candidate_id, config_sha256
from preflight_guard import booking_remaining, digest, load_bound, require_review, validate_resources, validate_static

CLOCK_TOLERANCE_MS = 100


def clock_point(utc_ms, monotonic, anchor):
    integer(utc_ms, "UTC milliseconds")
    timestamp(monotonic)
    expected = anchor["start_utc_ms"] + (monotonic - anchor["start_monotonic"]) * 1000
    if not math.isfinite(expected) or abs(utc_ms - expected) > CLOCK_TOLERANCE_MS:
        raise ValueError("Actual UTC/perf_counter point differs from the same-boot claim clock anchor")


def endpoint_bindings(manifest, processes, config, proof, session, cid):
    expected = {"host": config["host"], "boot_id": proof["boot_id"], "run_id": session["run_id"],
                "source_commit": proof["commit"], "deploy_sha256": proof["deploy_sha256"],
                "candidate_config_sha256": proof["systems"][cid.split("-p")[0]]["candidate_config_sha256"]}
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("Actual endpoint manifest source/run/host scope differs")
    by_worker = {f'{p["pid"]}:{p["proc_start_ticks"]}': p for p in processes}
    services = manifest["services"]
    baseline = cid.startswith("replicas-")
    if len(services) != (3 if baseline else 1) or len({s["url"] for s in services}) != len(services):
        raise ValueError("Actual API endpoint count/uniqueness differs")
    apis, urls, assigned = set(), [], []
    for service in services:
        url = urlsplit(service["url"])
        if url.scheme != "http" or url.hostname not in ("127.0.0.1", "::1") or not url.port or url.path not in ("", "/") or url.query or url.fragment:
            raise ValueError("Endpoint must be an exact same-host loopback API URL")
        api = service["api_identity"]
        for key, value in {"uid": config["uid"], "root": config["root"], "host": config["host"],
                "boot_id": proof["boot_id"], "run_id": session["run_id"],
                "source_commit": proof["commit"], "deploy_sha256": proof["deploy_sha256"]}.items():
            if api.get(key) != value:
                raise ValueError("Actual API process UID/root/RUNID/source identity differs")
        identity = integer(api["pid"], "API PID", 1), integer(api["proc_start_ticks"], "API start ticks", 1)
        if identity in apis:
            raise ValueError("Baseline endpoints share an API process identity")
        apis.add(identity)
        keys = service["worker_keys"]
        if len(keys) != len(set(keys)) or any(key not in by_worker for key in keys):
            raise ValueError("Endpoint maps to an unknown/duplicate actual worker identity")
        if baseline and (len(keys) != 1 or by_worker[keys[0]]["engine_stage"] != "FULL_REPLICA"):
            raise ValueError("Each baseline API must bind its own full-model GPU worker")
        assigned.extend(keys); urls.append(service["url"])
    if set(assigned) != set(by_worker) or baseline and len(assigned) != 3:
        raise ValueError("Actual service manifest does not bind all three model workers")
    return services, by_worker, apis, urls


def consume(owner, bundle_file, bundle_sha256, config, source_sha256, deploy_sha256):
    validate_static(config)
    bundle = load_bound(owner, bundle_file, bundle_sha256)
    proof = bundle["proof"]
    expected = {"schema": "selected-three-G3-proof-v1", "static_config_sha256": digest(config),
                "host": config["host"], "uid": config["uid"], "root": config["root"],
                "gpu_uuids": config["gpu_uuids"], "numa_by_uuid": config["numa_by_uuid"],
                "source_manifest_sha256": source_sha256, "deploy_sha256": deploy_sha256}
    if any(proof.get(key) != value for key, value in expected.items()):
        raise ValueError("Selected G3 proof/source/deploy/static scope differs")
    require_review(owner, bundle["review_file"], bundle["review_sha256"], "G3", digest(proof), config)

    def raw(descriptor):
        return bound_bytes(owner, descriptor["path"], descriptor["sha256"])

    def document(descriptor):
        return json.loads(raw(descriptor))

    def records(descriptor):
        return [json.loads(line) for line in raw(descriptor).splitlines() if line.strip()]

    deployment = document(proof["deployment"])
    if proof["deployment"]["sha256"] != deploy_sha256 or any(deployment.get(key) != proof[key]
            for key in ("commit", "host", "uid", "root", "boot_id", "gpu_uuids", "numa_by_uuid", "source_manifest_sha256")):
        raise ValueError("Actual deployment evidence differs")
    if proof["source_manifest"]["sha256"] != source_sha256 or not document(proof["source_manifest"])["files"]:
        raise ValueError("Full actual source manifest missing")
    runtime = document(proof["runtime_binding"])
    validate_runtime(runtime)
    if set(runtime["gpu_capacity_bytes"]) != set(config["gpu_uuids"]):
        raise ValueError("Actual memory runtime UUID set differs")
    selection = document(proof["selection"])
    if set(selection["selected"]) != {"replicas", "pd", "epd"} or set(proof["systems"]) != set(selection["selected"]):
        raise ValueError("All selected three systems are required")
    candidates = {candidate_id(candidate): candidate for candidate in CANDIDATES}
    common_input = None
    common_reference = None
    native_rows = []
    all_system_rows = {}
    global_release_utc = None
    global_clock_anchor = None
    for system in ("replicas", "pd", "epd"):
        group = proof["systems"][system]
        cid = selection["selected"][system]["candidate"]
        if cid not in candidates or candidates[cid][0] != system or group["candidate"] != cid:
            raise ValueError("G3 did not validate the exact selected candidate")
        if group["candidate_config_sha256"] != config_sha256(candidates[cid]):
            raise ValueError("Selected profile/distribution config SHA differs")
        required = selection["required_full_G3"][system]
        if (required["candidate"] != cid or required["requests"] != 120
                or required["candidate_config_sha256"] != group["candidate_config_sha256"]
                or required["source_manifest_sha256"] != source_sha256
                or required["runtime_binding_sha256"] != proof["runtime_binding"]["sha256"]):
            raise ValueError("Selection source/runtime/full-G3 requirement differs")
        input_sha, reference_sha = group["inputs"]["sha256"], group["reference"]["sha256"]
        if common_input is None:
            common_input, common_reference = input_sha, reference_sha
        if input_sha != common_input or reference_sha != common_reference:
            raise ValueError("Systems must share identical input/reference artifacts")
        fixtures = document(group["inputs"])["fixtures"]
        fixture_map = {fixture["fixture_id"]: fixture for fixture in fixtures}
        if len(fixtures) != 120 or len(fixture_map) != 120:
            raise ValueError("Full cold/restart G3 requires 120 unique input fixtures")
        reference = records(group["reference"])
        refs = {row["fixture_id"]: row for row in reference}
        if len(reference) != 120 or len(refs) != 120:
            raise ValueError("Actual full native reference must contain 120 rows")
        if set(group["sessions"]) != {"cold", "restart"}:
            raise ValueError("Cold and complete-process restart sessions are mandatory")
        claim = document(group["claim"])
        unit = claim["unit"]
        if (unit["phase"] != "selected_g3" or unit["unit"] != system or unit["candidate"] != cid
                or unit["allocation"] != [120, 0, 1600] or unit["deploy_sha256"] != deploy_sha256
                or claim["static_config_sha256"] != digest(config)):
            raise ValueError("Full selected G3 is not bound to its exact consumed budget claim")
        timing = claim["timing"]
        if (timing["clock"] != "time.perf_counter" or timing["host"] != config["host"]
                or timing["boot_id"] != proof["boot_id"] or timing["allocation_seconds"] != 1600
                or unit["timing"] != timing):
            raise ValueError("Durable actual claim timing/boot/allocation differs")
        integer(timing["start_utc_ms"], "actual claim start UTC")
        integer(timing["deadline_utc_ms"], "actual claim deadline UTC")
        timestamp(timing["start_monotonic"]); timestamp(timing["deadline_monotonic"])
        if (timing["deadline_utc_ms"] - timing["start_utc_ms"] != 1600000
                or timing["deadline_monotonic"] - timing["start_monotonic"] != 1600):
            raise ValueError("G3 budget is not exactly 1600s from actual durable claim")
        if global_clock_anchor is not None:
            clock_point(timing["start_utc_ms"], timing["start_monotonic"], global_clock_anchor)
        else:
            global_clock_anchor = timing
        if global_release_utc is not None and timing["start_utc_ms"] < global_release_utc:
            raise ValueError("Cross-system overlap: next unit claimed before prior actual release")
        clock_point(claim["resources"]["observed_ms"], claim["resources"]["monotonic_s"], timing)
        if any(claim["source"].get(key) != proof[key] for key in
               ("commit", "host", "uid", "root", "boot_id", "gpu_uuids", "numa_by_uuid", "source_manifest_sha256", "deploy_sha256")):
            raise ValueError("Original claim deployment/source identity differs")
        validate_resources(claim["resources"], config, unit["run_id"], claim["source"], claim["resources"]["observed_ms"])
        admission_booking = document(group["admission_booking"])
        if (group["admission_booking"]["sha256"] != unit["booking_sha256"]
                or booking_remaining(admission_booking, config, claim["resources"]["observed_ms"]) < 1600):
            raise ValueError("Actual claimed G3 did not have a fresh complete booking budget")
        ledger = document(group["ledger"])
        if ledger["static_config_sha256"] != digest(config) or ledger["units"].get("selected_g3/" + system) != unit:
            raise ValueError("Original durable ledger does not contain this exact consumed G3 unit")
        previous_pids = None
        previous_apis = None
        previous_release_ms = None
        combined = []
        for name in ("cold", "restart"):
            session = group["sessions"][name]
            integer(session["start_utc_ms"], "G3 session start UTC")
            integer(session["end_utc_ms"], "G3 session end UTC")
            clock_point(session["start_utc_ms"], session["start_monotonic"], timing)
            clock_point(session["end_utc_ms"], session["end_monotonic"], timing)
            if (session["start_utc_ms"] < timing["start_utc_ms"] or session["end_utc_ms"] > timing["deadline_utc_ms"]
                    or session["start_monotonic"] < timing["start_monotonic"]
                    or session["end_monotonic"] > timing["deadline_monotonic"]):
                raise ValueError("G3 session exceeded the actual durable claim window")
            if session["run_id"] != unit["run_id"]:
                raise ValueError("Cold/restart RUNID differs from the claimed unit")
            rows, windows = records(session["requests"]), records(session["client_windows"])
            if len(rows) != 60 or len(windows) != 12 or len({r["request_id"] for r in rows}) != 60:
                raise ValueError("Each session requires 60 actual requests/12 complete case windows")
            case_set = {f"i{images}-o{tokens}-c{concurrency}" for images in (1, 4, 8)
                        for tokens in (32, 128) for concurrency in (1, 8)}
            if {window["case"] for window in windows} != case_set:
                raise ValueError("Full 1/4/8-image, 32/128-output, C1/C8 case coverage missing")
            registry = document(session["registry"])
            if any(registry.get(key) != value for key, value in {"uid": config["uid"], "host": config["host"],
                    "boot_id": proof["boot_id"], "run_id": session["run_id"]}.items()):
                raise ValueError("Cold/restart actual process registry identity differs")
            processes = registry["processes"]
            if len(processes) != 3 or {p["gpu_uuid"] for p in processes} != set(config["gpu_uuids"]):
                raise ValueError("Full G3 requires exactly one actual model process per GPU")
            counts = Counter(p["engine_stage"] for p in processes)
            _, p_count, d_count, _ = candidates[cid]
            expected_counts = ({"FULL_REPLICA": 3} if system == "replicas" else
                {"CONTEXT": p_count, "DECODING": d_count} if system == "pd" else
                {"ENCODING": 1, "CONTEXT": 1, "DECODING": 1})
            if counts != expected_counts:
                raise ValueError("Actual actor-stage allocation differs from selected topology")
            pids = {(p["pid"], p["proc_start_ticks"]) for p in processes}
            if len(pids) != 3:
                raise ValueError("TP1 model processes are not three distinct PID/start identities")
            for pid, ticks in pids:
                integer(pid, "G3 PID", 1); integer(ticks, "G3 process start ticks", 1)
            if previous_pids is not None and pids & previous_pids:
                raise ValueError("Restart reused live old model processes")
            for process in processes:
                expected_process = {"uid": config["uid"], "root": config["root"], "run_id": session["run_id"],
                    "boot_id": proof["boot_id"], "source_commit": proof["commit"], "deploy_sha256": deploy_sha256}
                if any(process.get(key) != value for key, value in expected_process.items()):
                    raise ValueError("Actual process root/RUNID/source/UID differs")
            services, by_worker, api_keys, urls = endpoint_bindings(document(session["endpoints"]), processes, config, proof, session, cid)
            if previous_apis is not None and previous_apis & api_keys:
                raise ValueError("Restart reused old API process identities")
            by_url = {service["url"]: service for service in services}
            if system == "replicas":
                indices = [integer(row["dispatch_index"], "actual client dispatch index") for row in rows]
                if sorted(indices) != list(range(60)):
                    raise ValueError("Baseline dispatch indices must cover the complete 60-request round robin")
                if Counter(row["endpoint"] for row in rows) != Counter({url: 20 for url in urls}):
                    raise ValueError("Each cold/restart baseline session must actually cover all three endpoints equally")
            for row in rows:
                if row["endpoint"] not in by_url:
                    raise ValueError("Request used an endpoint outside the actual service manifest")
                service = by_url[row["endpoint"]]
                if row["observed_api_identity"] != service["api_identity"]:
                    raise ValueError("Actual per-request API PID/start response differs from endpoint binding")
                if system == "replicas" and row["endpoint"] != urls[row["dispatch_index"] % 3]:
                    raise ValueError("Baseline request did not follow the actual client round-robin command")
                route = row["observed_worker_route"]
                route_keys = [f'{worker["pid"]}:{worker["proc_start_ticks"]}' for worker in route]
                if len(route_keys) != len(set(route_keys)) or any(key not in service["worker_keys"] for key in route_keys):
                    raise ValueError("Actual request route used an unbound/duplicate worker")
                for worker, key in zip(route, route_keys):
                    if any(worker.get(field) != by_worker[key][field] for field in
                           ("pid", "proc_start_ticks", "gpu_uuid", "engine_stage", "uid", "root", "run_id", "boot_id", "source_commit", "deploy_sha256")):
                        raise ValueError("Actual per-request worker PID/UUID/source identity differs")
                wanted = {"FULL_REPLICA": 1} if system == "replicas" else ({"CONTEXT": 1, "DECODING": 1} if system == "pd" else
                    {"ENCODING": 1, "CONTEXT": 1, "DECODING": 1})
                if Counter(worker["engine_stage"] for worker in route) != wanted:
                    raise ValueError("Actual request did not traverse the selected model-stage path")
            booking = document(session["booking"])
            remaining = booking_remaining(booking, config, session["start_utc_ms"])
            if (session["end_utc_ms"] <= session["start_utc_ms"]
                    or session["end_utc_ms"] > session["start_utc_ms"] + remaining * 1000
                    or previous_release_ms is not None and session["start_utc_ms"] < previous_release_ms):
                raise ValueError("G3/restart exceeds actual owned booking or overlaps old session")
            for window in windows:
                if (window["clock"] != "time.perf_counter" or window["host"] != config["host"]
                        or window["boot_id"] != proof["boot_id"] or window["run_id"] != session["run_id"]):
                    raise ValueError("Actual G3 case window clock/host/run differs")
                timestamp(window["start_monotonic"]); timestamp(window["end_monotonic"])
                if not session["start_monotonic"] <= window["start_monotonic"] < window["end_monotonic"] <= session["end_monotonic"]:
                    raise ValueError("Actual G3 case window escaped the anchored session")
                if (window["images"] not in (1, 4, 8) or window["output_tokens"] not in (32, 128)
                        or window["case"] != f'i{window["images"]}-o{window["output_tokens"]}-c{window["concurrency"]}'):
                    raise ValueError("Actual G3 window visual/output/concurrency geometry differs")
                matching = [row for row in rows if row["case"] == window["case"]]
                expected_n = 2 if window["concurrency"] == 1 else 8
                if window["concurrency"] not in (1, 8) or len(matching) != expected_n:
                    raise ValueError("G3 case concurrency/request count differs")
                if any(len(row["input"]["images"]) != window["images"] or len(row["output_token_ids"]) != window["output_tokens"]
                       for row in matching):
                    raise ValueError("G3 actual visual/output length differs from case")
                intervals = [(r["submit_monotonic"], r["end_monotonic"]) for r in matching]
                for a, b in intervals: timestamp(a); timestamp(b)
                if any(not window["start_monotonic"] <= a < b <= window["end_monotonic"] for a, b in intervals):
                    raise ValueError("G3 requests lie outside actual case window")
                peak = max(sum(a <= at < b for a, b in intervals) for at, _ in intervals)
                if peak != window["concurrency"]:
                    raise ValueError("G3 did not achieve actual C8 concurrency")
            provider = document(session["provider"])
            if (provider.get("backend") != "NVML" or provider.get("unit") != "bytes"
                    or not provider.get("calls") or not provider.get("driver") or not provider.get("nvml")):
                raise ValueError("Original actual NVML provider/version evidence missing")
            snapshots = records(session["raw_nvml"])
            samples = records(session["memory_samples"])
            if not snapshots or not samples:
                raise ValueError("Actual raw NVML/memory samples are mandatory")
            raw_samples = {(snap["monotonic_s"], uuid): gpu for snap in snapshots for uuid, gpu in snap["gpus"].items()}
            for snap in snapshots:
                integer(snap["observed_ms"], "raw snapshot UTC")
                clock_point(snap["observed_ms"], snap["monotonic_s"], timing)
                if not session["start_utc_ms"] <= snap["observed_ms"] <= session["end_utc_ms"]:
                    raise ValueError("Raw NVML clock lies outside actual session bounds")
                if (any(snap.get(key) != value for key, value in {"host": config["host"], "uid": config["uid"],
                        "root": config["root"], "boot_id": proof["boot_id"], "run_id": session["run_id"]}.items())
                        or set(snap["gpus"]) != set(config["gpu_uuids"])):
                    raise ValueError("Raw NVML host/UID/root/RUNID/boot/UUID evidence differs")
            times = {uuid: [] for uuid in config["gpu_uuids"]}
            for sample in samples:
                timestamp(sample["monotonic_s"])
                integer(sample["capacity_bytes"], "G3 capacity bytes", 1)
                integer(sample["device_used_bytes"], "G3 device bytes")
                key = sample["monotonic_s"], sample["gpu_uuid"]
                actual = raw_samples[key]
                uuid = sample["gpu_uuid"]
                if (sample["unit"] != "bytes" or sample["capacity_bytes"] != runtime["gpu_capacity_bytes"][uuid]
                        or sample["device_used_bytes"] != actual["used_bytes"]
                        or not 0 <= sample["device_used_bytes"] <= runtime["gpu_memory_cap_bytes"][uuid]):
                    raise ValueError("G3 actual sampled memory/raw/capacity/cap differs")
                target = {(p["pid"], p["proc_start_ticks"]) for p in processes if p["gpu_uuid"] == uuid}
                if ({(p["pid"], p["proc_start_ticks"]) for p in sample["processes"]} != target
                        or {(p["pid"], p["proc_start_ticks"]) for p in actual["processes"]} != target):
                    raise ValueError("G3 memory attribution differs from actual registry/raw")
                for process in sample["processes"]:
                    if process["uid"] != config["uid"] or process["run_id"] != session["run_id"]:
                        raise ValueError("Foreign G3 memory process")
                    original = next(p for p in actual["processes"] if p["pid"] == process["pid"])
                    if type(process["used_bytes"]) is not int or not 0 <= process["used_bytes"] <= sample["device_used_bytes"] or process["used_bytes"] != original["used_bytes"]:
                        raise ValueError("Actual G3 process byte attribution differs")
                times[uuid].append(sample["monotonic_s"])
            first, last = min(w["start_monotonic"] for w in windows), max(w["end_monotonic"] for w in windows)
            for stamps in times.values():
                if (not stamps or stamps != sorted(set(stamps)) or stamps[0] > first or stamps[-1] < last
                        or any(b - a > 1.0 for a, b in zip(stamps, stamps[1:]))):
                    raise ValueError("Actual G3 memory sampling does not cover full case windows")
            release = document(session["release"])
            integer(release["observed_ms"], "actual release UTC")
            clock_point(release["observed_ms"], release["monotonic_s"], timing)
            if release["observed_ms"] > timing["deadline_utc_ms"] or release["monotonic_s"] > timing["deadline_monotonic"]:
                raise ValueError("Actual release exceeded the claimed unit deadline")
            if (any(release.get(key) != value for key, value in {"host": config["host"], "uid": config["uid"],
                        "root": config["root"], "boot_id": proof["boot_id"], "run_id": session["run_id"]}.items())
                    or release["observed_ms"] < session["end_utc_ms"]
                    or release["observed_ms"] > config["authorized_end_ms"] - config["cleanup_seconds"] * 1000
                    or set(release["gpus"]) != set(config["gpu_uuids"])
                    or any(g["processes"] or g["used_bytes"] > config["max_idle_bytes"] for g in release["gpus"].values())):
                raise ValueError("Actual owned process release/restart boundary is unconfirmed")
            exits = release["api_exit_observations"]
            if {(entry["pid"], entry["proc_start_ticks"]) for entry in exits} != api_keys:
                raise ValueError("Actual API exit evidence does not cover the exact service endpoints")
            for entry in exits:
                clock_point(entry["observed_ms"], entry["monotonic_s"], timing)
                if entry["state"] != "not_present" or not session["end_utc_ms"] <= entry["observed_ms"] <= release["observed_ms"]:
                    raise ValueError("Actual API process release is unconfirmed")
            previous_pids, previous_apis, previous_release_ms = pids, api_keys, release["observed_ms"]
            for row in rows:
                fixture = fixture_map[row["fixture_id"]]
                reference_row = refs[row["fixture_id"]]
                if (row["run_id"] != session["run_id"] or row["candidate"] != cid or row.get("success") is not True
                        or row["session"] != name or fixture["session"] != name or row["case"] != fixture["case"]
                        or row["input"] != fixture["input"] or not row["processed_prompt_token_ids"]
                        or row["processed_prompt_token_ids"] != reference_row["processed_prompt_token_ids"]
                        or row["output_token_ids"] != reference_row["output_token_ids"]
                        or len(row["output_token_ids"]) != fixture["output_tokens"]):
                    raise ValueError("Actual selected G3 input/processed/output/reference differs")
                if any(type(token) is not int or token < 0 for token in row["processed_prompt_token_ids"] + row["output_token_ids"]):
                    raise ValueError("Actual G3 token IDs must be nonnegative integers")
                if type(row["input"]["prompt"]) is not str or not row["input"]["prompt"]:
                    raise ValueError("Actual G3 prompt is invalid")
                for image in row["input"]["images"]:
                    if not image["path"] or len(image["rgb_sha256"]) != 64:
                        raise ValueError("Actual G3 ordered image/RGB identity is missing")
            combined.extend(rows)
        global_release_utc = previous_release_ms
        if len({row["fixture_id"] for row in combined}) != 120:
            raise ValueError("G3 fixtures were omitted/repeated across cold/restart")
        all_system_rows[system] = combined
        if system == "replicas":
            native_rows = combined
        if {r["fixture_id"]: (r["processed_prompt_token_ids"], r["output_token_ids"])
                for r in reference} != {r["fixture_id"]: (r["processed_prompt_token_ids"], r["output_token_ids"])
                for r in native_rows}:
            raise ValueError("Reference is not the actual selected native full-G3 output")
    return {"state": "independent_full_selected_G3_consumed", "proof_sha256": digest(proof),
            "original_review_sha256": bundle["review_sha256"], "formal_admission": "blocked_separate_user_formal_budget_required",
            "new_GPU_requests": 0}
