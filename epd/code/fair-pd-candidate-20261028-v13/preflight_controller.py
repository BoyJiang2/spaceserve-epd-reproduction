"""Fixed qualification/calibration production bridge. Candidate scopes cannot run.

Numeric full-cache and selected cold/restart orchestration are explicitly blocked.
No GPU dependency is imported until original GPU authorization/source checks pass.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

from admission import bound_bytes
from fixed_unit import validate_spec
from live_evidence import ProcReader, NvmlBackend, snapshot, collect, write_exclusive
from preflight_guard import (Claim, digest, load_bound, validate_static, verify_checkout,
                             require_review, validate_resources, booking_remaining)
from production_identity import assemble_services


def authorize(config, inputs, owner):
    validate_static(config)  # candidate rejection before NVML, spawn or claim.
    if len(set(config["numa_by_uuid"].values())) != 1:
        raise ValueError("Exactly three approved GPUs in one NUMA group required")
    if (socket.gethostname(), os.getuid(), str(Path.cwd().resolve())) != (config["host"], config["uid"], config["root"]):
        raise ValueError("Actual host/UID/root differs")
    user = load_bound(owner, inputs["user_file"], inputs["user_sha256"])
    if (user.get("author") != "human_user" or user.get("scope") != "EPD_preflight_only"
            or user.get("static_config_sha256") != digest(config)
            or not bound_bytes(owner, user["original_instruction_file"], user["original_instruction_sha256"]).strip()):
        raise ValueError("Original exact GPU grant required; CPU grant is insufficient")
    require_review(owner, inputs["G1_file"], inputs["G1_sha256"], "G1", digest(config), config)
    require_review(owner, inputs["G2_file"], inputs["G2_sha256"], "G2", digest({
        "static_config_sha256": digest(config), "source_manifest_sha256": inputs["source_manifest_sha256"]}), config)
    return verify_checkout(config, inputs, owner)


def booking_for_unit(config, inputs, owner, spec, now_ms):
    raw = load_bound(owner, inputs["booking_file"], inputs["booking_sha256"])
    if type(raw.get("observed_ms")) is not int or raw["observed_ms"] > now_ms:
        raise ValueError("GPU booking observation is missing or from the future")
    remaining = booking_remaining(raw, config, now_ms)  # Also validates exact user/ticket/window/freshness.
    if spec["wall_seconds"] > remaining:
        raise ValueError("Complete fixed unit plus cleanup cannot fit owned booking")
    return raw


def load_execution(template_path, config, inputs, owner):
    template_path = Path(template_path).resolve(strict=True)
    root = Path(config["root"])
    rel = template_path.relative_to(root).as_posix()
    manifest = load_bound(owner, inputs["source_manifest_file"], inputs["source_manifest_sha256"])
    pin = next((item for item in manifest["files"] if item["path"] == rel), None)
    if pin is None or hashlib.sha256(template_path.read_bytes()).hexdigest() != pin["sha256"]:
        raise ValueError("Unit template is not a pinned committed source member")
    template = json.loads(template_path.read_bytes())
    # Avoid an impossible source-manifest/spec self-hash cycle: only runtime envelope binds sourceSHA.
    if "source_manifest_sha256" in template: raise ValueError("Static template cannot self-reference its source manifest")
    spec = {**template, "source_manifest_sha256": inputs["source_manifest_sha256"]}
    validate_spec(spec, config, inputs["source_manifest_sha256"])
    output = root / "runtime" / inputs["run_id"]
    spec["client_argv"] = [sys.executable, str(root / "benchmark.py"), "--fixed-unit", str(output / "execution.json"),
                           "--unit-runtime", str(output / "client-runtime.json"), "--unit-output", str(output)]
    return spec


def child_environment(server, spec, config, inputs, deployed):
    return {"PATH": os.environ.get("PATH", ""), "LD_LIBRARY_PATH": os.environ.get("LD_LIBRARY_PATH", ""),
        "CUDA_VISIBLE_DEVICES": server["CUDA_VISIBLE_DEVICES"], "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "RAY_ADDRESS": "local",
        "REPRO_RAY_TMP": str(Path(config["root"]) / "runtime" / inputs["run_id"] / "ray"),
        "EXP_ROOT": config["root"], "REPRO_RUN_ID": inputs["run_id"], "REPRO_SOURCE_COMMIT": deployed["commit"],
        "REPRO_DEPLOY_SHA256": inputs["deploy_sha256"], "REPRO_PROFILE_SHA256": spec["candidate_config_sha256"],
        "REPRO_GPU_UUIDS": json.dumps(config["gpu_uuids"]), "REPRO_ENDPOINT": server["url"],
        "REPRO_IDENTITY": "1", "REPRO_REQUEST_IDENTITY": "1" if spec["request_diagnostics"] else "0",
        "REPRO_RGB_MANIFEST": spec["rgb_manifest"]}


def observe_owned(pid, config, run_id, proc):
    identity = proc.identity(pid, config["uid"])
    if identity["boot_id"] != proc.boot() or not Path(identity["cwd"]).is_relative_to(Path(config["root"])):
        raise ValueError("PID boot/cwd outside this owned unit; refuse to signal")
    return {**identity, "root": config["root"], "run_id": run_id}


def descendants(owned, config, run_id, proc):
    # Only descendants of exact already registered PIDs, never a machine-wide process scan.
    for saved in list(owned.values()):
        try:
            current = observe_owned(saved["pid"], config, run_id, proc)
            if current != saved: raise ValueError("Known parent PID identity changed")
            for task in (Path("/proc") / str(saved["pid"]) / "task").iterdir():
                for value in (task / "children").read_text().split():
                    pid = int(value)
                    if pid not in owned: owned[pid] = observe_owned(pid, config, run_id, proc)
        except FileNotFoundError:
            continue  # Gone parent is checked again in terminal cleanup.


def stop_owned(saved, config, run_id, proc, deadline, process=None):
    observations = []
    if process is not None:
        process.poll()  # Reap the exact Popen child before examining an already-exited /proc entry.
    for number in (signal.SIGTERM, signal.SIGKILL):
        if time.perf_counter() >= deadline: break
        try:
            current = observe_owned(saved["pid"], config, run_id, proc)
            if current != saved: return {"identity": saved, "state": "identity_changed_refused"}
        except FileNotFoundError:
            state = "gone" if not Path('/proc/' + str(saved["pid"])).exists() else "zombie_or_unknown_unconfirmed"
            return {"identity": saved, "state": state}
        except Exception as error:
            return {"identity": saved, "state": "identity_unknown_refused", "error": str(error)}
        os.kill(saved["pid"], number); observations.append(int(number))
        until = min(deadline, time.perf_counter() + 2)
        while time.perf_counter() < until:
            if process is not None: process.poll()  # Reap exact own Popen child.
            if not Path('/proc/' + str(saved["pid"])).exists():
                return {"identity": saved, "state": "gone", "signals": observations}
            time.sleep(.05)
    return {"identity": saved, "state": "deadline_unconfirmed", "signals": observations}


def listener_owned(pid, url):
    """Match a selected loopback listen inode to this exact owned API's FDs."""
    port = urlsplit(url).port
    inodes = set()
    for fd in (Path('/proc') / str(pid) / 'fd').iterdir():
        try: target = os.readlink(fd)
        except FileNotFoundError: continue
        if target.startswith('socket:['): inodes.add(target[8:-1])
    with Path('/proc/net/tcp').open() as file:
        for line in file:
            fields = line.split()
            if len(fields) > 9 and fields[1] == '0100007F:' + format(port, '04X') and fields[3] == '0A' and fields[9] in inodes:
                return True
    return False


def rgb_cache(url, spec):
    parsed = urlsplit(url)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
    try:
        connection.request("GET", "/repro/rgb-cache")
        response = connection.getresponse(); raw = response.read()
        if response.status != 200: raise ValueError("Actual RGB cache endpoint failed; no retry")
        actual = json.loads(raw)
    finally:
        connection.close()
    if actual["manifest_sha256"] != spec["rgb_manifest_sha256"]:
        raise ValueError("Actual server cache manifest differs")
    images = {str(Path(spec["dataset"]) / image["file"]): image["rgb_sha256"] for image in actual["images"]}
    for batch in spec["batches"]:
        for request in batch["requests"]:
            for image in request["input"]["images"]:
                if images.get(image["path"]) != image["rgb_sha256"]:
                    raise ValueError("Actual server RGB buffer differs from frozen vector")
    return actual, images


def run(config, inputs, owner, template):
    deployed = authorize(config, inputs, owner)
    spec = load_execution(template, config, inputs, owner)
    root, proc = Path(config["root"]), ProcReader()
    runtime = root / "runtime"; runtime.mkdir(mode=0o700, exist_ok=True)
    if runtime.resolve() != runtime or runtime.stat().st_uid != config["uid"]:
        raise ValueError("Runtime escaped the exact owned source root")
    import fcntl
    fd = os.open(runtime / "controller.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+") as lock:
        import stat
        info = os.fstat(lock.fileno())
        if info.st_uid != config["uid"] or not stat.S_ISREG(info.st_mode): raise ValueError("Unknown controller lock owner/type")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        active = runtime / "controller-active.json"
        if active.exists() and json.loads(active.read_bytes()).get("state") != "released":
            raise ValueError("Previous unit release unconfirmed; no next unit")
        booking_for_unit(config, inputs, owner, spec, int(time.time()*1000))
        backend = NvmlBackend()  # Original GPU grant, current booking and complete-unit time already verified.
        try:
            fresh = snapshot(config, inputs["run_id"], deployed, backend, proc)
            if any(gpu["processes"] for gpu in fresh["gpus"].values()):
                raise ValueError("Startup requires all three approved GPUs free of compute PIDs")
            booking_for_unit(config, inputs, owner, spec, int(time.time()*1000))
            claim = Claim(config, inputs, owner, spec["unit"], spec["phase"], spec["candidate"], fresh,
                          now_ms=int(time.time()*1000))
            envs = [child_environment(server, spec, config, inputs, deployed) for server in spec["servers"]]
            spec["server_environments"] = envs
            spec["client_environment"] = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1",
                "CUDA_VISIBLE_DEVICES": "", "NVIDIA_VISIBLE_DEVICES": "void"}
            ledger = runtime / "gpu-budget.json"
            if ledger.exists():
                old_units = json.loads(ledger.read_bytes())["units"].values()
                first = min((unit["timing"]["start_monotonic"] for unit in old_units), default=time.perf_counter())
                if time.perf_counter() + spec["wall_seconds"] + 600 > first + 340 * 60:
                    raise TimeoutError("Complete next unit plus cleanup cannot fit global340min")
            claim.reserve(ledger, spec)
            claim.admit_request(spec["max_requests"])  # Once, before startup; finite vector only.
            output = runtime / inputs["run_id"]; output.mkdir(mode=0o700, exist_ok=False)
            write_exclusive(output / "execution.json", spec)
            active.write_text(json.dumps({"state": "claimed", "claim": claim.reservation_receipt, "run_id": inputs["run_id"]}))
            return execute_claimed(config, inputs, deployed, spec, claim, backend, proc, output, active)
        finally:
            backend.close()


def execute_claimed(config, inputs, deployed, spec, claim, backend, proc, output, active):
    root, run_id = Path(config["root"]), inputs["run_id"]
    owned, processes, logs, bootstrap_seen = {}, {}, [], {}
    cancelled, collect_stop, sample_ready = threading.Event(), threading.Event(), threading.Event()
    errors, cleanup, failure, sampler = [], [], None, None
    by_pid = {}
    previous = {n: signal.getsignal(n) for n in (signal.SIGTERM, signal.SIGINT)}
    for number in previous: signal.signal(number, lambda number, frame: cancelled.set())
    def check():
        claim.check()
        if time.perf_counter() >= claim.deadline - config["cleanup_seconds"]:
            raise TimeoutError("Reserved in-unit cleanup interval reached")
        if cancelled.is_set() or errors: raise RuntimeError("Unit cancelled/collector failed")
    def spawn(argv, env):
        check()
        log = (output / ('process-' + str(len(logs)) + '.log')).open('xb'); logs.append(log)
        process = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        processes[process.pid] = process
        owned[process.pid] = observe_owned(process.pid, config, run_id, proc)
        write_exclusive(output / ('spawn-' + str(process.pid) + '.json'), {"argv": argv, "identity": owned[process.pid]})
        check()  # Deferred TERM/INT is handled only after the owned Popen and identity are bound.
        return process
    try:
        for server, env in zip(spec["servers"], spec["server_environments"]): spawn(server["argv"], env)
        # Actual bootstrap raw, including own UID/startticks before late self-registration.
        with (output / 'bootstrap-nvml.jsonl').open('x', encoding='utf-8') as raw:
            while True:
                check(); descendants(owned, config, run_id, proc)
                for uuid in config["gpu_uuids"]:
                    observed = backend.read(uuid)
                    raw.write(json.dumps({"gpu_uuid": uuid, "clock": time.perf_counter(), "raw": observed}) + '\n'); raw.flush()
                    if observed["used_bytes"] > observed["capacity_bytes"] * 65 // 100:
                        raise ValueError("Bootstrap sampled memory exceeds common cap")
                    for process in observed["processes"]:
                        identity = observe_owned(process["pid"], config, run_id, proc)
                        if process["pid"] not in owned: raise ValueError("Bootstrap compute PID is not a known own descendant")
                        bootstrap_seen[process["pid"]] = {**identity, "gpu_uuid": uuid}
                paths = list((root / 'runtime/endpoints').glob(run_id + '-*.json'))
                if len(paths) == len(spec["servers"]): break
                if any(p.poll() is not None for p in processes.values()): raise RuntimeError("Official service exited before registration")
                time.sleep(.1)
        env = spec["server_environments"][0]
        saved_env = {key: os.environ.get(key) for key in env}
        try:
            os.environ.update(env)
            endpoints = assemble_services(paths, output / 'endpoints.json')
        finally:
            for key, value in saved_env.items():
                if value is None: os.environ.pop(key, None)
                else: os.environ[key] = value
        ready = snapshot(config, run_id, deployed, backend, proc)
        validate_resources(ready, config, run_id, deployed, int(time.time()*1000))
        by_pid = {p["pid"]: p for gpu in ready["gpus"].values() for p in gpu["processes"]}
        expected_roles = ["FULL_REPLICA"] * 3 if spec["candidate"].startswith('replicas-') else (["ENCODING", "CONTEXT", "DECODING"] if spec["candidate"].startswith('epd-') else
            ["CONTEXT"] * int(spec["candidate"].split('-p')[1].split('-')[0]) + ["DECODING"] * int(spec["candidate"].split('-d')[1].split('-')[0]))
        if sorted(p["engine_stage"] for p in by_pid.values()) != sorted(expected_roles): raise ValueError("Actual stage/worker count differs")
        for pid, before in bootstrap_seen.items():
            after = by_pid.get(pid)
            if after is None or any(after[k] != before[k] for k in ('proc_start_ticks', 'gpu_uuid', 'uid', 'boot_id', 'run_id', 'root')):
                raise ValueError("Bootstrap identity cannot bind to actual registered worker")
        from selected_g3 import endpoint_bindings
        system = spec["candidate"].split('-p')[0]
        endpoint_bindings(endpoints, list(by_pid.values()), config,
            {"boot_id": deployed["boot_id"], "commit": deployed["commit"], "deploy_sha256": inputs["deploy_sha256"],
             "systems": {system: {"candidate_config_sha256": spec["candidate_config_sha256"]}}}, {"run_id": run_id}, spec["candidate"])
        while not all(listener_owned(service["api_identity"]["pid"], service["url"]) for service in endpoints["services"]):
            check()
            if any(p.poll() is not None for p in processes.values()): raise RuntimeError("API exited before actual listening")
            time.sleep(.05)
        rgb = None
        for index, server in enumerate(spec["servers"]):
            actual_cache, observed_rgb = rgb_cache(server["url"], spec)
            write_exclusive(output / ('rgb-' + str(index) + '.json'), actual_cache)
            if rgb is not None and rgb != observed_rgb: raise ValueError("Baseline/endpoint RGB caches differ")
            rgb = observed_rgb
        def sampling():
            try: collect(claim, output / 'memory', lambda: collect_stop.is_set(), backend_factory=NvmlBackend,
                         ready_callback=sample_ready.set)
            except BaseException as error:
                errors.append(repr(error)); (output / 'STOP').touch(exist_ok=True); sample_ready.set()
        sampler = threading.Thread(target=sampling, daemon=True); sampler.start()
        while not sample_ready.wait(.05): check()
        check()
        write_exclusive(output / 'client-runtime.json', {"claim": {"path": claim.reservation_receipt["claim"],
            "sha256": claim.reservation_receipt["claim_sha256"]}, "unit_id": claim.reservation_receipt["key"],
            "run_id": run_id, "uid": config["uid"], "rgb_by_path": rgb, "stop_file": str(output / 'STOP'),
            "clock_scope": {"host": config["host"], "boot_id": deployed["boot_id"], "run_id": run_id}})
        client = spawn(spec["client_argv"], spec["client_environment"])
        while client.poll() is None:
            check(); descendants(owned, config, run_id, proc); time.sleep(.1)
        if client.returncode != 0: raise RuntimeError("Actual fixed client failed; no retry")
        time.sleep(.15); check()  # Tail memory sample after actual outer window.
    except BaseException as error:
        failure = {"type": type(error).__name__, "error": repr(error)}
    finally:
        try: (output / 'STOP').touch(exist_ok=True)
        except Exception as error: errors.append('stop-file:' + repr(error))
        collect_stop.set()
        if sampler is not None: sampler.join(timeout=2)
        deadline = min(time.perf_counter() + config["cleanup_seconds"], claim.deadline)
        try:
            descendants(owned, config, run_id, proc)
            for saved in reversed(list(owned.values())):
                current_gpus = {p["pid"]: uuid for uuid in config["gpu_uuids"] for p in backend.read(uuid)["processes"]}
                if saved["pid"] in current_gpus:
                    binding = by_pid.get(saved["pid"])
                    if binding is None or binding["gpu_uuid"] != current_gpus[saved["pid"]]:
                        cleanup.append({"identity": saved, "state": "GPU_identity_unknown_refused"}); continue
                    sidecar = root / 'runtime/identities' / (str(saved["pid"]) + '-' + str(saved["proc_start_ticks"]) + '.json')
                    actual_binding = json.loads(sidecar.read_bytes())
                    if any(actual_binding.get(k) != binding[k] for k in ('pid','uid','root','run_id','boot_id','proc_start_ticks','gpu_uuid','engine_stage','source_commit','deploy_sha256','candidate_config_sha256','endpoint')):
                        cleanup.append({"identity": saved, "state": "GPU_binding_changed_refused"}); continue
                cleanup.append(stop_owned(saved, config, run_id, proc, deadline, processes.get(saved["pid"])))
        except BaseException as error: cleanup.append({"state": "cleanup_unknown_unconfirmed", "error": repr(error)})
        for log in logs:
            try: log.close()
            except Exception: pass
        released = bool(owned) and set(processes) <= set(owned) and len(cleanup) == len(owned) and all(item["state"] == 'gone' for item in cleanup)
        release_raw = {}
        try:
            for uuid in config['gpu_uuids']:
                release_raw[uuid] = backend.read(uuid)
                if release_raw[uuid]['processes'] or release_raw[uuid]['used_bytes'] > config['max_idle_bytes']: released = False
        except Exception as error:
            released = False; errors.append(repr(error))
        if sampler is not None and sampler.is_alive(): released = False; errors.append('collector_not_stopped')
        try: verify_checkout(config, inputs, claim.owner)
        except Exception as error: errors.append(repr(error)); failure = failure or {"error": "source_changed"}
        artifacts = {}
        try:
            for artifact in output.iterdir():
                if artifact.is_file():
                    try: artifacts[artifact.name] = hashlib.sha256(artifact.read_bytes()).hexdigest()
                    except Exception as error: errors.append('artifact:' + repr(error))
        except Exception as error: errors.append('artifact-list:' + repr(error))
        report = {"state": 'released' if released else 'release_unconfirmed', 'run_id': run_id,
            'failure': failure, 'errors': errors, 'cleanup': cleanup, 'actual_gpu_release': release_raw,
            'claim': claim.reservation_receipt, 'source_commit': deployed['commit'],
            'finished_utc_ms': int(time.time()*1000), 'formal_admission': 'blocked',
            'evidence_state': 'raw_not_independently_reviewed', 'files': artifacts}
        try:
            write_exclusive(output / 'terminal.json', report)
            active.write_text(json.dumps({'state': report['state'] if failure is None and not errors else 'stopped_no_next_unit', 'terminal': str(output / 'terminal.json'),
                'terminal_sha256': hashlib.sha256((output / 'terminal.json').read_bytes()).hexdigest()}))
        finally:
            for number, handler in previous.items(): signal.signal(number, handler)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--unit-template', type=Path, required=True)
    args = parser.parse_args()
    inputs = json.loads(args.inputs.read_bytes())
    config = json.loads((Path.cwd() / 'preflight-static.json').read_bytes())
    report = run(config, inputs, args.inputs.resolve(), args.unit_template)
    return 0 if report['state'] == 'released' and report['failure'] is None and not report['errors'] else 1


if __name__ == '__main__': sys.exit(main())
