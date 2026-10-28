"""Fixed preflight request vectors, raw client and exact official argv. No GPU imports."""
import asyncio
import base64
import signal
import hashlib
import json
import math
from pathlib import Path
import sys
import time

from experiment_plan import CANDIDATES, candidate_arguments, candidate_id, config_sha256, qualification_schedule, LOADS
from preflight_guard import digest, unit_budget
SOURCE = Path(__file__).resolve().parent


def official_servers(spec, config):
    candidate = next(c for c in CANDIDATES if candidate_id(c) == spec["candidate"])
    root = SOURCE
    common = candidate_arguments(candidate)["arguments"]
    urls = spec["urls"]
    if len(urls) != (3 if candidate[0] == "replicas" else 1) or len(set(urls)) != len(urls):
        raise ValueError("Exactly three baseline endpoints or one disaggregated endpoint required")
    from urllib.parse import urlsplit
    result = []
    for index, url in enumerate(urls):
        parsed = urlsplit(url)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("Only exact loopback endpoints allowed")
        if candidate[0] == "replicas":
            argv = [sys.executable, str(root / "baseline_server.py"), "--model", spec["model"],
                    "--dataset", spec["dataset"], "--port", str(parsed.port), *common]
            visible = config["gpu_uuids"][index]
        else:
            argv = [sys.executable, "-m", "epdserve.api_server", "--host", "127.0.0.1",
                    "--port", str(parsed.port), "--model", spec["model"], "--tokenizer", spec["model"], *common]
            visible = ",".join(config["gpu_uuids"])
        result.append({"url": url, "argv": argv, "CUDA_VISIBLE_DEVICES": visible})
    return result


def validate_spec(spec, config, source_sha):
    if spec["schema"] != "epd-fixed-unit-v1" or spec["source_manifest_sha256"] != source_sha:
        raise ValueError("Fixed source/schema differs")
    candidate = next((c for c in CANDIDATES if candidate_id(c) == spec["candidate"]), None)
    if candidate is None or config_sha256(candidate) != spec["candidate_config_sha256"]:
        raise ValueError("Unknown candidate/profile SHA")
    n, transfers, seconds = unit_budget(spec["phase"], spec["unit"], spec["candidate"])
    if spec["phase"] not in ("qualification", "calibration"):
        raise NotImplementedError("Numeric geometry/transfer and full cold/restart adapters remain blocked in this unit")
    if spec["servers"] != official_servers(spec, config) or spec["max_requests"] != n or spec["wall_seconds"] != seconds:
        raise ValueError("Actual official argv/visibility/request budget differs")
    if spec["request_diagnostics"] is not (spec["phase"] == "qualification"):
        raise ValueError("Calibration diagnostics must be off for every group")
    for key in ("runtime_binding_sha256", "rgb_manifest_sha256"):
        if type(spec[key]) is not str or len(spec[key]) != 64 or any(c not in "0123456789abcdef" for c in spec[key]):
            raise ValueError("Missing runtime/cache binding")
    if "MiniCPM-V-2_6" not in spec["model"]:
        raise ValueError("Only the frozen MiniCPM model is supported")
    if hashlib.sha256(Path(spec["rgb_manifest"]).read_bytes()).hexdigest() != spec["rgb_manifest_sha256"]:
        raise ValueError("RGB input manifest differs")
    batches = spec["batches"]
    if spec["phase"] == "qualification":
        expected = [(row["case"], row["images"], row["tokens"], row["concurrency"], row["requests"], False)
                    for row in qualification_schedule() if row["candidate"] == spec["candidate"]]
    else:
        cid, repeat, load = spec["unit"].split("/")
        if cid != spec["candidate"] or int(repeat) != spec["repeat"] or load != spec["load"]:
            raise ValueError("Calibration unit identity differs")
        images, tokens, concurrency = LOADS[load]
        expected = [("warmup", images, tokens, concurrency, 4, True), ("measurement", images, tokens, concurrency, 16, False)]
    if any(type(b[key]) is not int or b[key] < 1 for b in batches for key in ("images", "tokens", "concurrency")):
        raise ValueError("Fixed geometry must use positive integers")
    actual = [(b["case"], b["images"], b["tokens"], b["concurrency"], len(b["requests"]), b["warmup"]) for b in batches]
    if actual != expected:
        raise ValueError("Fixed request geometry/order differs from reviewed schedule")
    seen, dispatch = set(), 0
    for batch in batches:
        for row in batch["requests"]:
            if row["fixture_id"] in seen or row["dispatch_index"] != dispatch:
                raise ValueError("Duplicate fixture or noncontinuous dispatch index")
            seen.add(row["fixture_id"]); dispatch += 1
            data = row["input"]
            if not isinstance(data["prompt"], str) or not data["prompt"] or len(data["images"]) != batch["images"]:
                raise ValueError("Actual request prompt/image vector differs")
            for image in data["images"]:
                if Path(image["path"]).resolve().parent != Path(spec["dataset"]).resolve() or len(image["rgb_sha256"]) != 64:
                    raise ValueError("Ordered image outside frozen dataset or missing RGB hash")
    if dispatch != n:
        raise ValueError("N+1/incomplete fixed request vector")
    return n


async def _run_client(spec, runtime, output):
    """Called only by the claimed benchmark subprocess, one POST per frozen vector item."""
    import aiohttp
    output = Path(output)
    claim_raw = Path(runtime["claim"]["path"]).read_bytes()
    if hashlib.sha256(claim_raw).hexdigest() != runtime["claim"]["sha256"]:
        raise ValueError("Actual durable claim bytes differ")
    claim = json.loads(claim_raw)
    if digest(claim["execution"]) != digest(spec) or claim["execution_sha256"] != digest(spec):
        raise ValueError("Client argv/vector differs from pre-start claim")
    deadline = claim["timing"]["deadline_monotonic"]
    stop_file = Path(runtime["stop_file"])
    # Fresh connections + no redirects; no retry loop or proxy environment.
    connector = aiohttp.TCPConnector(force_close=True)
    timeout = aiohttp.ClientTimeout(total=120)
    issued, windows = 0, []
    with (output / "requests.jsonl").open("x", encoding="utf-8") as raw, \
         (output / "request-events.jsonl").open("x", encoding="utf-8") as events:
        def event(kind, row, **fields):
            events.write(json.dumps({"event": kind, "request_id": row["request_id"], "unit_id": row["unit_id"],
                "run_id": row["run_id"], **fields}) + "\n"); events.flush()
        async with aiohttp.ClientSession(connector=connector, timeout=timeout, trust_env=False) as session:
            if hasattr(session, "_retry_connection"): session._retry_connection = False
            for batch in spec["batches"]:
                semaphore = asyncio.Semaphore(batch["concurrency"])
                async def one(item):
                    nonlocal issued
                    async with semaphore:
                        if stop_file.exists() or time.perf_counter() >= deadline or issued >= spec["max_requests"]:
                            raise RuntimeError("Unit stopped/deadline/N+1: do not submit")
                        issued += 1
                        endpoint = spec["urls"][item["dispatch_index"] % len(spec["urls"])]
                        images = []
                        for image in item["input"]["images"]:
                            actual_hash = runtime["rgb_by_path"][image["path"]]
                            if actual_hash != image["rgb_sha256"]: raise ValueError("Actual server RGB differs")
                            images.append({"path": image["path"], "rgb_sha256": actual_hash})
                        actual_input = {"prompt": item["input"]["prompt"], "images": images}
                        body = {"input": {"prompt": actual_input["prompt"], "multi_modal_data": {
                            "images_paths": [i["path"] for i in images]}}, "stream": False,
                            "max_tokens": batch["tokens"], "temperature": 0.0, "ignore_eos": True}
                        row = {"fixture_id": item["fixture_id"], "request_id": item["fixture_id"],
                            "unit_id": runtime["unit_id"], "run_id": runtime["run_id"], "candidate": spec["candidate"],
                            "case": batch["case"], "images": len(images), "input": actual_input,
                            "dispatch_index": item["dispatch_index"], "endpoint": endpoint, "warmup": batch["warmup"],
                            "submit_monotonic": time.perf_counter()}
                        if spec["phase"] == "calibration": row.update(repeat=spec["repeat"], load=spec["load"])
                        row.update(request_body=body, status="submitted")
                        event("submitted", row, submitted=dict(row))  # Flush submission before POST; no per-request fsync/hash.
                        cancelled = False
                        try:
                            async with session.post(endpoint + "/generate", json=body, allow_redirects=False) as response:
                                body_bytes = await response.read()
                                received = time.perf_counter()
                                event("http_body", row, http_status=response.status, received_monotonic=received,
                                      body_base64=base64.b64encode(body_bytes).decode("ascii"))
                                row.update(http_status=response.status, raw_response=body_bytes.decode("utf-8", errors="replace"), end_monotonic=received)
                                if response.status != 200: raise RuntimeError("HTTP status " + str(response.status))
                                result = json.loads(body_bytes)
                            row.update(response=result, processed_prompt_token_ids=result["processed_prompt_token_ids"],
                                output_token_ids=result["output_token_ids"], observed_api_identity=result.get("repro_api_identity"),
                                observed_worker_route=result.get("repro_worker_route"), server_request_id=result.get("repro_request_id"))
                            stamps = result["timestamps"]
                            if (len(row["output_token_ids"]) != batch["tokens"] or len(stamps) != batch["tokens"]
                                    or not row["processed_prompt_token_ids"] or any(not math.isfinite(t) for t in stamps)
                                    or not row["submit_monotonic"] <= stamps[0] <= stamps[-1] <= row["end_monotonic"]):
                                raise ValueError("Actual token IDs/count/server clock differ")
                            if spec["request_diagnostics"] and (row["server_request_id"] is None or not row["observed_worker_route"]):
                                raise ValueError("Actual server RID/worker route missing")
                            row.update(success=True, status="complete")
                            event("complete", row, end_monotonic=row["end_monotonic"])
                        except BaseException as error:
                            cancelled = isinstance(error, asyncio.CancelledError)
                            row.update(success=False, status="cancelled" if cancelled else "failed",
                                       end_monotonic=time.perf_counter(), error=repr(error))
                            event(row["status"], row, end_monotonic=row["end_monotonic"], error=row["error"])
                        raw.write(json.dumps(row) + "\n"); raw.flush()
                        try:
                            if not row["success"]: stop_file.touch(exist_ok=True)
                        finally:
                            if cancelled: raise asyncio.CancelledError()
                        return row
                start = time.perf_counter()
                results = await asyncio.gather(*(one(item) for item in batch["requests"]), return_exceptions=True)
                end = time.perf_counter()
                window = {"case": batch["case"], "images": batch["images"], "output_tokens": batch["tokens"],
                          "concurrency": batch["concurrency"], "clock": "time.perf_counter",
                          "start_monotonic": start, "end_monotonic": end, **runtime["clock_scope"]}
                windows.append(window)
                with (output / "case-windows.jsonl").open("a", encoding="utf-8") as file:
                    file.write(json.dumps(window) + "\n")
                if any(isinstance(row, BaseException) or row.get("success") is not True for row in results):
                    raise RuntimeError("Actual fixed batch failed; preserve raw, no retry")
    if issued != spec["max_requests"]: raise RuntimeError("Fixed vector incomplete")
    if spec["phase"] == "calibration":
        from client_window import write_window
        metadata = {**runtime["clock_scope"], "candidate": spec["candidate"], "candidate_config_sha256": spec["candidate_config_sha256"],
            "uid": runtime["uid"], "repeat": spec["repeat"], "load": spec["load"],
            "source_manifest_sha256": spec["source_manifest_sha256"], "runtime_binding_sha256": spec["runtime_binding_sha256"]}
        warm, measured = windows
        write_window(output, metadata, warm["start_monotonic"], warm["end_monotonic"], measured["start_monotonic"], measured["end_monotonic"])
        (output / "summary.json").write_text(json.dumps({"requests_per_s": 16 / (measured["end_monotonic"] - measured["start_monotonic"])}))
    return windows


async def run_client(spec, runtime, output):
    """TERM/INT cancel in-flight tasks so their submitted/cancelled journal survives."""
    loop, task = asyncio.get_running_loop(), asyncio.current_task()
    previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    installed = []
    try:
        for number in previous:
            loop.add_signal_handler(number, task.cancel)
            installed.append(number)
        return await _run_client(spec, runtime, output)
    finally:
        for number in installed:
            loop.remove_signal_handler(number)
            signal.signal(number, previous[number])
