"""Guarded NVML bytes and selected-PID evidence. Never scan environ or signal PIDs."""
import hashlib
import json
import os
from pathlib import Path
import socket
import time


def write_exclusive(path, value):
    with Path(path).open("x", encoding="utf-8") as file:
        json.dump(value, file, indent=2)
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ProcReader:
    def boot(self):
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()

    def identity(self, pid, expected_uid):
        base = Path("/proc") / str(pid)
        status = (base / "status").read_text()
        uid_line = next(line for line in status.splitlines() if line.startswith("Uid:"))
        uids = list(map(int, uid_line.split()[1:]))
        if any(uid != expected_uid for uid in uids):
            raise ValueError("Foreign selected-GPU PID; stop without further inspection or signalling")
        stat = (base / "stat").read_text()
        fields = stat[stat.rfind(")") + 2:].split()
        ticks = int(fields[19])  # /proc stat field 22, after pid/comm.
        return {"pid": pid, "uid": expected_uid, "proc_start_ticks": ticks,
                "cwd": str((base / "cwd").resolve(strict=True)), "boot_id": self.boot()}

    def numa(self, pci_bus_id):
        # NVML may use an eight-digit PCI domain; sysfs uses four digits.
        domain, bus, device = pci_bus_id.lower().split(":")
        return int((Path("/sys/bus/pci/devices") / f"{int(domain,16):04x}:{bus}:{device}" / "numa_node").read_text())


def capture_own_identity(root, run_id, source_commit, deploy_sha256, gpu_uuid, engine_stage, proc=None, *, candidate_config_sha256=None, endpoint=None):
    """Called inside the pinned owned worker; reads only two explicit env keys."""
    proc = proc or ProcReader()
    root = Path(root).resolve()
    if (os.environ.get("EXP_ROOT") != str(root) or os.environ.get("REPRO_RUN_ID") != run_id
            or not Path.cwd().resolve().is_relative_to(root)):
        raise ValueError("Owned worker root/RUNID environment identity is unconfirmed")
    identity = proc.identity(os.getpid(), os.getuid())
    identity.update(root=str(root), run_id=run_id, source_commit=source_commit,
                    deploy_sha256=deploy_sha256, gpu_uuid=gpu_uuid, host=socket.gethostname(),
                    engine_stage=engine_stage)
    if candidate_config_sha256 is not None:
        identity.update(candidate_config_sha256=candidate_config_sha256, endpoint=endpoint)
    folder = root / "runtime/identities"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{identity["pid"]}-{identity["proc_start_ticks"]}.json'
    write_exclusive(path, identity)
    return identity


class NvmlBackend:
    def __init__(self):
        # Metadata-only admission after original GPU scope validation; model sampling after Claim.
        import pynvml
        self.api = pynvml
        self.api.nvmlInit()
        self.version = {"backend": "NVML", "nvml": str(self.api.nvmlSystemGetNVMLVersion()),
                        "driver": str(self.api.nvmlSystemGetDriverVersion()),
                        "calls": ["nvmlDeviceGetMemoryInfo", "nvmlDeviceGetComputeRunningProcesses_v3",
                                  "nvmlDeviceGetPciInfo", "nvmlDeviceGetName", "nvmlDeviceGetHandleByUUID"], "unit": "bytes"}

    def read(self, uuid):
        handle = self.api.nvmlDeviceGetHandleByUUID(uuid)
        memory = self.api.nvmlDeviceGetMemoryInfo(handle)
        pci = self.api.nvmlDeviceGetPciInfo(handle).busId
        if isinstance(pci, bytes):
            pci = pci.decode("ascii")
        processes = self.api.nvmlDeviceGetComputeRunningProcesses_v3(handle)
        result = {"capacity_bytes": int(memory.total), "used_bytes": int(memory.used),
                  "free_bytes": int(memory.free), "pci_bus_id": pci,
                  "processes": [{"pid": int(p.pid), "used_bytes": p.usedGpuMemory} for p in processes]}
        name = self.api.nvmlDeviceGetName(handle)
        result["name"] = name.decode("ascii") if isinstance(name, bytes) else str(name)
        return result

    def close(self):
        self.api.nvmlShutdown()


def snapshot(config, run_id, deployed, backend, proc, *, monotonic=time.perf_counter, utc_ms=None,
             raw_observer=None):
    result = {"host": socket.gethostname(), "uid": os.getuid(), "root": config["root"],
              "boot_id": proc.boot(), "run_id": run_id,
              "observed_ms": int(time.time() * 1000) if utc_ms is None else utc_ms,
              "monotonic_s": monotonic(), "provider": backend.version, "gpus": {}}
    if result["host"] != config["host"] or result["uid"] != config["uid"] or result["boot_id"] != deployed["boot_id"]:
        raise ValueError("Actual NVML host/UID/boot differs from the approved deployment")
    for uuid in config["gpu_uuids"]:
        raw = backend.read(uuid)
        if raw_observer is not None:
            raw_observer({"gpu_uuid": uuid, "monotonic_s": result["monotonic_s"],
                          "observed_ms": result["observed_ms"], "provider": backend.version, "raw": raw})
        if any(type(p["used_bytes"]) is not int or not 0 <= p["used_bytes"] <= raw["capacity_bytes"] for p in raw["processes"]):
            raise ValueError("NVML process memory is unavailable/unresolved")
        gpu = {**raw, "numa": proc.numa(raw["pci_bus_id"]), "unit": "bytes", "processes": []}
        for process in raw["processes"]:
            actual = proc.identity(process["pid"], config["uid"])
            identity_path = Path(config["root"]) / "runtime/identities" / f'{actual["pid"]}-{actual["proc_start_ticks"]}.json'
            if not identity_path.resolve().is_relative_to((Path(config["root"]) / "runtime/identities").resolve()):
                raise ValueError("Identity sidecar escaped the owned runtime directory")
            if identity_path.stat().st_uid != config["uid"]:
                raise ValueError("Identity sidecar is not owned")
            saved = json.loads(identity_path.read_bytes())
            expected = {"pid": actual["pid"], "uid": config["uid"], "root": config["root"],
                        "run_id": run_id, "proc_start_ticks": actual["proc_start_ticks"],
                        "boot_id": result["boot_id"], "host": result["host"], "gpu_uuid": uuid,
                        "source_commit": deployed["commit"], "deploy_sha256": deployed["deploy_sha256"]}
            if saved.get("engine_stage") not in ("ENCODING", "CONTEXT", "DECODING", "FULL_REPLICA"):
                raise ValueError("Actual owned compute stage is not recorded")
            if (any(saved.get(key) != value for key, value in expected.items())
                    or not Path(actual["cwd"]).is_relative_to(Path(config["root"]))):
                raise ValueError("Selected PID root/RUNID/source/start identity differs; do not kill it")
            if proc.identity(process["pid"], config["uid"]) != actual:
                raise ValueError("Selected PID identity changed during collection")
            gpu["processes"].append({**expected, "engine_stage": saved["engine_stage"], "used_bytes": process["used_bytes"],
                **{key: saved[key] for key in ("candidate_config_sha256", "endpoint") if key in saved}})
        if raw["processes"] and sum(p["used_bytes"] for p in raw["processes"]) > raw["used_bytes"]:
            raise ValueError("Unresolved NVML memory attribution")
        result["gpus"][uuid] = gpu
    return result


def collect(permit, output, stop_requested, *, backend_factory=NvmlBackend, proc=None,
            clock=time.perf_counter, sleep=time.sleep, ready_callback=None):
    """Caller must keep it running across the actual outer client window."""
    from preflight_guard import Claim, validate_resources
    if not isinstance(permit, Claim) or not getattr(permit, "reserved", False):
        raise ValueError("Collector requires an actual recorded preflight Claim")
    permit.verify_reservation()
    output = Path(output).resolve()
    runtime = (Path(permit.config["root"]) / "runtime").resolve()
    if not output.is_relative_to(runtime):
        raise ValueError("Collector output must stay in the approved runtime whitelist")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(mode=0o700, exist_ok=False)
    proc = proc or ProcReader()
    backend = backend_factory()
    seen = {}
    try:
        write_exclusive(output / "provider.json", backend.version)
        with (output / "samples.jsonl").open("x", encoding="utf-8") as samples, \
             (output / "raw-nvml.jsonl").open("x", encoding="utf-8") as raw_file, \
             (output / "raw-api.jsonl").open("x", encoding="utf-8") as raw_api:
            def preserve(value):
                raw_api.write(json.dumps(value) + "\n"); raw_api.flush()
            while True:
                permit.check()
                observed = snapshot(permit.config, permit.inputs["run_id"], permit.deployed, backend, proc,
                                    monotonic=clock, raw_observer=preserve)
                # Preserve the actual API/identity data before any validation failure.
                raw_file.write(json.dumps(observed) + "\n"); raw_file.flush()
                validate_resources(observed, permit.config, permit.inputs["run_id"], permit.deployed, observed["observed_ms"])
                for uuid, gpu in observed["gpus"].items():
                    processes = gpu["processes"]
                    if not processes:
                        raise ValueError("Expected owned model compute process missing from selected GPU")
                    for process in processes:
                        key = uuid, process["pid"], process["proc_start_ticks"]
                        seen[key] = {"gpu_uuid": uuid, **{name: process[name] for name in
                            ("pid", "uid", "run_id", "proc_start_ticks", "root", "boot_id", "source_commit", "deploy_sha256")}}
                        seen[key]["engine_stage"] = process["engine_stage"]
                        seen[key].update({name: process[name] for name in ("candidate_config_sha256", "endpoint") if name in process})
                    row = {"gpu_uuid": uuid, "unit": "bytes", "capacity_bytes": gpu["capacity_bytes"],
                           "device_used_bytes": gpu["used_bytes"], "monotonic_s": observed["monotonic_s"],
                           "processes": [{key: process[key] for key in ("pid", "uid", "run_id", "proc_start_ticks", "used_bytes")}
                                         for process in processes]}
                    samples.write(json.dumps(row) + "\n")
                samples.flush()
                if ready_callback is not None:
                    ready_callback()
                if stop_requested():
                    break
                sleep(.1)
        registry = {"host": permit.config["host"], "boot_id": permit.deployed["boot_id"],
                    "uid": permit.config["uid"], "run_id": permit.inputs["run_id"], "processes": list(seen.values())}
        write_exclusive(output / "process-registry.json", registry)
        artifacts = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
        write_exclusive(output / "capture-receipt.json", {"state": "captured_not_G3_approved", "files": artifacts,
            "source_commit": permit.deployed["commit"], "deploy_sha256": permit.deployed["deploy_sha256"],
            "claim_phase": permit.phase, "claim_unit": permit.unit, "run_id": permit.inputs["run_id"]})
        return artifacts
    except Exception as error:
        write_exclusive(output / "failure.json", {"state": "stopped_unapproved", "error": str(error),
            "phase": permit.phase, "unit": permit.unit, "run_id": permit.inputs["run_id"],
            "partial_files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}})
        raise
    finally:
        backend.close()
