"""Opt-in qualification identities; imported without Ray, CUDA or NVML."""
import json
import os
from pathlib import Path
import re
import socket
from urllib.parse import urlsplit

from live_evidence import ProcReader, capture_own_identity, write_exclusive

KEYS = ("EXP_ROOT", "REPRO_RUN_ID", "REPRO_SOURCE_COMMIT", "REPRO_DEPLOY_SHA256",
        "REPRO_PROFILE_SHA256", "REPRO_ENDPOINT", "REPRO_GPU_UUIDS")


def enabled():
    value = os.environ.get("REPRO_IDENTITY", "0")
    if value not in ("0", "1"):
        raise ValueError("REPRO_IDENTITY must be 0 or 1")
    return value == "1"


def environment():
    if not enabled():
        return {}
    values = {key: os.environ[key] for key in KEYS}
    root = Path(values["EXP_ROOT"]).resolve(strict=True)
    if str(root) != values["EXP_ROOT"] or not Path.cwd().resolve().is_relative_to(root):
        raise ValueError("Qualification identity root/cwd differs")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", values["REPRO_RUN_ID"]):
        raise ValueError("Invalid qualification RUNID")
    for key, length in (("REPRO_SOURCE_COMMIT", 40), ("REPRO_DEPLOY_SHA256", 64), ("REPRO_PROFILE_SHA256", 64)):
        if not re.fullmatch("[0-9a-f]{%d}" % length, values[key]):
            raise ValueError("Invalid qualification source/deploy/profile hash")
    url = urlsplit(values["REPRO_ENDPOINT"])
    if (url.scheme != "http" or url.hostname not in ("127.0.0.1", "::1") or not url.port
            or url.path or url.query or url.fragment or url.username or url.password):
        raise ValueError("Qualification endpoint must be an exact loopback URL")
    uuids = json.loads(values["REPRO_GPU_UUIDS"])
    if len(uuids) != 3 or len(set(uuids)) != 3 or any(not re.fullmatch(r"GPU-[0-9a-f-]{36}", uuid) for uuid in uuids):
        raise ValueError("Qualification identity requires exactly three full GPU UUIDs")
    return {"REPRO_IDENTITY": "1", **values}


def scope():
    values = environment()
    return {"host": socket.gethostname(), "run_id": values["REPRO_RUN_ID"],
            "source_commit": values["REPRO_SOURCE_COMMIT"], "deploy_sha256": values["REPRO_DEPLOY_SHA256"],
            "candidate_config_sha256": values["REPRO_PROFILE_SHA256"]}


def worker_identity(device, stage):
    if not enabled():
        return None
    values = environment()
    # Actual CUDA device property, never the expected placement or a Ray GPU index.
    import torch
    uuid = str(torch.cuda.get_device_properties(device).uuid)
    if uuid not in json.loads(values["REPRO_GPU_UUIDS"]):
        raise ValueError("Actual CUDA UUID differs from qualification GPU set")
    return capture_own_identity(values["EXP_ROOT"], values["REPRO_RUN_ID"], values["REPRO_SOURCE_COMMIT"],
        values["REPRO_DEPLOY_SHA256"], uuid, stage,
        candidate_config_sha256=values["REPRO_PROFILE_SHA256"], endpoint=values["REPRO_ENDPOINT"])


def publish_service(workers, port):
    values = environment()
    url = values["REPRO_ENDPOINT"]
    if urlsplit(url).port != port or not workers:
        raise ValueError("Actual listening port/worker binding differs")
    current = scope()
    api = ProcReader().identity(os.getpid(), os.getuid())
    api.update(current, root=values["EXP_ROOT"], endpoint=url)
    for worker in workers:
        if (any(worker[key] != current[key] for key in current)
                or worker["endpoint"] != url or worker["uid"] != api["uid"]
                or worker["root"] != api["root"] or worker["boot_id"] != api["boot_id"]):
            raise ValueError("Actual API/worker scope differs")
    service = {"url": url, "api_identity": api,
               "worker_keys": [f'{w["pid"]}:{w["proc_start_ticks"]}' for w in workers]}
    envelope = {**current, "boot_id": api["boot_id"], "services": [service]}
    folder = Path(values["EXP_ROOT"]) / "runtime/endpoints"
    folder.mkdir(parents=True, exist_ok=True)
    write_exclusive(folder / f'{api["run_id"]}-{api["pid"]}-{api["proc_start_ticks"]}.json', envelope)
    return service


def mark_batch(batch, workers):
    # Once per visited stage, no extra RPC, hashing, disk write or per-token growth.
    for request in batch.requests:
        route = getattr(request, "repro_worker_route", [])
        known = {(worker["pid"], worker["proc_start_ticks"]) for worker in route}
        request.repro_worker_route = route + [worker for worker in workers
            if (worker["pid"], worker["proc_start_ticks"]) not in known]


def response_identity(service, route):
    if not route:
        raise ValueError("Successful qualification response has no actual worker route")
    return {"repro_api_identity": service["api_identity"], "repro_worker_route": route}


def assemble_services(paths, output):
    """Join server-produced sidecars after rechecking only their exact owned PIDs."""
    values, current, proc = environment(), scope(), ProcReader()
    services = []
    boot = proc.boot()
    for path in paths:
        path = Path(path).resolve(strict=True)
        folder = (Path(values["EXP_ROOT"]) / "runtime/endpoints").resolve()
        if path.parent != folder or path.stat().st_uid != os.getuid():
            raise ValueError("Endpoint sidecar outside owned runtime folder")
        envelope = json.loads(path.read_bytes())
        if any(envelope[key] != value for key, value in {**current, "boot_id": boot}.items()):
            raise ValueError("Server-produced endpoint scope differs")
        for service in envelope["services"]:
            api = service["api_identity"]
            actual = proc.identity(api["pid"], os.getuid())
            if any(actual[key] != api[key] for key in actual):
                raise ValueError("Endpoint API PID/start/cwd changed")
            services.append(service)
    if not services or len({s["url"] for s in services}) != len(services):
        raise ValueError("Missing or duplicate live endpoints")
    output = Path(output).resolve()
    if not output.is_relative_to((Path(values["EXP_ROOT"]) / "runtime").resolve()):
        raise ValueError("Endpoint manifest must remain runtime data")
    manifest = {**current, "boot_id": boot, "services": services}
    write_exclusive(output, manifest)
    return manifest


def validate_profile(args, baseline=False):
    if not enabled():
        return
    from experiment_plan import CANDIDATES, candidate_arguments, config_sha256
    values = environment()
    if baseline:
        candidate = ("replicas", 0, 0, args.max_num_seqs)
    else:
        candidate = ("pd" if args.pd_fused else "epd", args.context_data_parallel_size,
                     args.decoding_data_parallel_size, args.runtime_max_num_seqs)
        if any(getattr(args, stage + "_" + parallel + "_parallel_size") != 1
               for stage in ("encoding", "context", "decoding") for parallel in ("tensor", "pipeline")):
            raise ValueError("Qualification identity requires actual TP1/PP1")
    if candidate not in CANDIDATES or config_sha256(candidate) != values["REPRO_PROFILE_SHA256"]:
        raise ValueError("Actual entrypoint profile differs from frozen profile SHA")
    argv = candidate_arguments(candidate)["arguments"]
    index = 0
    while index < len(argv):
        name = argv[index][2:].replace("-", "_")
        if name == "pd_fused":
            if not args.pd_fused:
                raise ValueError("Actual fused-PD flag differs")
            index += 1
        else:
            if str(getattr(args, name)) != argv[index + 1]:
                raise ValueError("Actual qualification CLI differs: " + name)
            index += 2


def baseline_worker_identity(engine):
    executor = engine.engine.model_executor
    if executor.__class__.__name__ != "GPUExecutorAsync" or engine.engine.parallel_config.tensor_parallel_size != 1:
        raise ValueError("Qualification baseline requires the local vLLM 0.6.1 TP1 GPUExecutorAsync")
    driver = executor.driver_worker
    worker = getattr(driver, "worker", driver)  # vLLM local WorkerWrapperBase, never a remote RPC.
    if worker.__class__.__module__ != "vllm.worker.worker" or worker.model_runner.model is None:
        raise ValueError("Qualification baseline cannot establish actual in-process loaded worker")
    return worker_identity(worker.device, "FULL_REPLICA")
