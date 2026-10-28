"""CPU-only mocked evidence. Never call NVML, a network API or a GPU/server."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TEST_TMP = Path(os.environ.get("EPD_CPU_TEST_TMP", ROOT / "tests")).resolve()
sys.path.insert(0, str(ROOT))
import preflight_guard as guard
import live_evidence as live
import selected_g3
from experiment_plan import CANDIDATES, candidate_id, config_sha256


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEST_TMP)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(TEST_TMP)
        self.addCleanup(self.temp.cleanup)
        self.data = self.root / "runtime"
        self.data.mkdir()
        self.owner = self.data / "admission-input.json"
        self.uid = os.getuid() if hasattr(os, "getuid") else 0
        self.now = 100000000
        self.commit = "a" * 40
        self.uuids = [f"GPU-CPU-fixture-{i}" for i in range(3)]
        self.config = {"schema": "epd-preflight-static-v1", "state": "approved_preflight_only",
            "host": "cpu-fixture-host", "uid": self.uid, "root": str(self.root), "gpu_uuids": self.uuids,
            "numa_by_uuid": {uuid: 0 for uuid in self.uuids}, "resource_id": "h20/cpu-fixture-host",
            "booking_user": "cpu-fixture-user", "booking_windows": [{"id": "cpu-fixture-booking",
                "start_ms": self.now - 1000, "end_ms": self.now + 100000000}],
            "authorized_start_ms": self.now - 1000, "authorized_end_ms": self.now + 100000000,
            "cleanup_seconds": 120, "executor_id": "cpu-implementer", "reviewer_ids": ["cpu-independent-reviewer"],
            "phase_limits": {name: list(value) for name, value in guard.PHASE_LIMITS.items()},
            "runtime_prefix": "runtime/", "max_idle_bytes": 100, "max_auto_retries": 0}
        source_files = []
        for name in ("preflight_guard.py", "live_evidence.py", "selected_g3.py", "admission.py",
                     "experiment_plan.py", "benchmark.py", "client_window.py",
                     "fixed_unit.py", "preflight_controller.py", "production_identity.py"):
            shutil.copy2(ROOT / name, self.root / name)
            source_files.append({"path": name, "sha256": self.sha(self.root / name)})
        (self.root / "preflight-static.json").write_text(json.dumps(self.config), encoding="utf-8")
        source_files.append({"path": "preflight-static.json", "sha256": self.sha(self.root / "preflight-static.json")})
        manifest = self.write("source-manifest.json", {"files": source_files})
        self.source_sha = manifest["sha256"]
        self.deployment = {"commit": self.commit, "source_manifest_sha256": self.source_sha,
            "host": self.config["host"], "uid": self.uid, "root": str(self.root), "gpu_uuids": self.uuids,
            "numa_by_uuid": self.config["numa_by_uuid"], "boot_id": "cpu-fixture-boot"}
        deploy = self.write("deploy.json", self.deployment)
        self.deploy_sha = deploy["sha256"]
        remote = self.write("remote-original.json", {"sha": self.commit, "repository": "CPU-MOCK-only"})
        pushed = self.write("push.json", {"commit": self.commit, "remote_verified": True,
            "source_manifest_sha256": self.source_sha, "repository": "CPU-MOCK-only",
            "raw_remote_file": remote["path"], "raw_remote_sha256": remote["sha256"]})
        booking = self.write("booking.json", self.booking(self.now))
        instruction = self.write("human-original.json", {"text": "CPU MOCK instruction only, never GPU authorization"})
        user = self.write("human-scope.json", {"author": "human_user", "scope": "EPD_preflight_only",
            "static_config_sha256": guard.digest(self.config), "original_instruction_file": instruction["path"],
            "original_instruction_sha256": instruction["sha256"]})
        g1 = self.fake_review("G1.json", "G1", guard.digest(self.config))
        g2 = self.fake_review("G2.json", "G2", guard.digest({"static_config_sha256": guard.digest(self.config),
                                                            "source_manifest_sha256": self.source_sha}))
        self.inputs = {"run_id": "cpu-fixture-run", "prerequisite_file": None, "prerequisite_sha256": None}
        for key, value in (("booking", booking), ("source_manifest", manifest), ("deploy", deploy),
                           ("push", pushed), ("user", user), ("G1", g1), ("G2", g2)):
            self.inputs[key + "_file"], self.inputs[key + "_sha256"] = value["path"], value["sha256"]
        self.actual = {"host": self.config["host"], "uid": self.uid, "root": str(self.root)}

    def sha(self, path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def write(self, name, value, lines=False):
        path = self.data / name
        path.write_text("".join(json.dumps(row) + "\n" for row in value) if lines else json.dumps(value), encoding="utf-8")
        return {"path": name, "sha256": self.sha(path)}

    def fake_review(self, name, gate, scope):
        return self.write(name, {"gate": gate, "scope_sha256": scope, "reviewer_id": "cpu-independent-reviewer",
            "decision": "APPROVE", "blocking": 0, "original_review_text": "CPU-MOCK review fixture only; not an actual gate"})

    def booking(self, now):
        return {"origin": "gputime_read_only_api", "observed_ms": now, "read_only": True,
            "resources": [{"id": self.config["resource_id"], "active": True}],
            "bookings": [{**self.config["booking_windows"][0], "resource_id": self.config["resource_id"],
                "node": self.config["host"], "user": self.config["booking_user"], "kind": "gpu"}]}

    def resource(self):
        return {**self.actual, "run_id": self.inputs["run_id"], "boot_id": "cpu-fixture-boot", "observed_ms": self.now,
            "gpus": {uuid: {"numa": 0, "unit": "bytes", "capacity_bytes": 10000,
                            "used_bytes": 0, "name": "CPU-MOCK-H20", "processes": []} for uuid in self.uuids}}

    def command(self, args, text=True):
        return self.commit + "\n" if "rev-parse" in args else ""

    def claim(self, phase="numeric", unit="numeric", candidate=None):
        return guard.Claim(self.config, self.inputs, self.owner, unit, phase, candidate,
            self.resource(), now_ms=self.now, clock=lambda: 1000.0, command=self.command, actual=self.actual)


class GuardCPU(Fixture):
    def test_candidate_static_configuration_never_authorizes_hardware(self):
        candidate = copy.deepcopy(self.config)
        candidate["state"] = "candidate_no_gpu_authorization"
        with self.assertRaisesRegex(ValueError, "no GPU authorization"):
            guard.validate_static(candidate)
        candidate = copy.deepcopy(self.config)
        candidate["unexpected_gpu_permission"] = True
        with self.assertRaises(ValueError):
            guard.validate_static(candidate)

    def test_fresh_owned_booking_and_static_bounds(self):
        self.assertGreater(guard.booking_remaining(self.booking(self.now), self.config, self.now), 1800)
        for field, value in (("observed_ms", self.now - 300001), ("read_only", False), ("origin", "lockfile")):
            raw = self.booking(self.now); raw[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                guard.booking_remaining(raw, self.config, self.now)
        raw = self.booking(self.now); raw["bookings"][0]["user"] = "foreign"
        with self.assertRaises(ValueError):
            guard.booking_remaining(raw, self.config, self.now)
        raw = self.booking(self.now); raw["resources"][0]["active"] = False
        with self.assertRaises(ValueError):
            guard.booking_remaining(raw, self.config, self.now)

    def test_exact_source_commit_deploy_and_user_review_bindings(self):
        claim = self.claim()
        self.assertEqual(claim.deployed["commit"], self.commit)
        with self.assertRaises(ValueError):
            guard.verify_checkout(self.config, self.inputs, self.owner, lambda args, text=True: "b" * 40 if "rev-parse" in args else "")
        (self.root / "benchmark.py").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "file SHA"):
            self.claim()

    def test_foreign_uuid_numa_uid_root_and_stale_resources_rejected(self):
        deployed = {**self.deployment, "deploy_sha256": self.deploy_sha}
        for field, value in (("uid", 999), ("root", "/foreign"), ("run_id", "foreign"),
                             ("observed_ms", self.now - 300001)):
            state = self.resource(); state[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                guard.validate_resources(state, self.config, self.inputs["run_id"], deployed, self.now)
        state = self.resource(); state["gpus"][self.uuids[0]]["numa"] = 1
        with self.assertRaises(ValueError):
            guard.validate_resources(state, self.config, self.inputs["run_id"], deployed, self.now)
        state = self.resource(); state["gpus"][self.uuids[0]]["processes"] = [{"uid": 999}]
        with self.assertRaises(ValueError):
            guard.validate_resources(state, self.config, self.inputs["run_id"], deployed, self.now)

    def test_nonrefundable_unit_inventory_and_no_formal_permission(self):
        claim = self.claim()
        state = {"static_config_sha256": guard.digest(self.config), "spent": {}, "units": {}}
        claim.account(state)
        self.assertEqual(state["spent"]["numeric"], [0, 36, 1800])
        self.assertFalse(getattr(claim, "reserved", False))  # Pure accounting is not a durable claim.
        with self.assertRaises(ValueError):
            claim.account(state)
        with self.assertRaises(ValueError):
            guard.unit_budget("formal", "any")
        with self.assertRaises(ValueError):
            guard.unit_budget("qualification", "other", "other")
        requests = sum(guard.unit_budget("qualification", candidate_id(c), candidate_id(c))[0] for c in CANDIDATES)
        requests += sum(guard.unit_budget("calibration", f"{candidate_id(c)}/{r}/{l}", candidate_id(c))[0]
                        for c in CANDIDATES for r in (0, 1) for l in "CDE")
        requests += 3 * 120
        self.assertEqual(requests, 1440)

    def test_request_transfer_deadline_checks_require_durable_claim(self):
        claim = self.claim()
        with patch.object(guard.time, "time", return_value=self.now / 1000):
            with self.assertRaises(ValueError):
                claim.admit_transfer()
            claim.reserved = True
            with self.assertRaisesRegex(ValueError, "boolean is insufficient"):
                claim.admit_transfer()
            claim.verify_reservation = lambda: claim.check()  # Explicit CPU mock; real POSIX evidence is not claimed.
            claim.admit_transfer(36)
            with self.assertRaises(ValueError):
                claim.admit_transfer()
            with self.assertRaises(ValueError):
                claim.admit_request()
            claim.deadline = 999
            with self.assertRaises(TimeoutError):
                claim.check()

    def test_later_phase_requires_actual_independently_reviewed_prerequisite(self):
        with self.assertRaises((TypeError, ValueError)):
            self.claim("calibration", "replicas-p0-d0-b4/0/C", "replicas-p0-d0-b4")


class CollectorCPU(Fixture):
    def live_fixture(self):
        folder = self.root / "runtime/identities"; folder.mkdir()
        stages = ["FULL_REPLICA"] * 3
        identities = {}
        for index, uuid in enumerate(self.uuids):
            identity = {"pid": 100 + index, "uid": self.uid, "proc_start_ticks": 1000 + index,
                "cwd": str(self.root), "root": str(self.root), "boot_id": "cpu-fixture-boot",
                "host": self.config["host"], "run_id": self.inputs["run_id"], "gpu_uuid": uuid,
                "source_commit": self.commit, "deploy_sha256": self.deploy_sha, "engine_stage": stages[index]}
            (folder / f'{identity["pid"]}-{identity["proc_start_ticks"]}.json').write_text(json.dumps(identity), encoding="utf-8")
            identities[identity["pid"]] = identity
        class Proc:
            def boot(inner): return "cpu-fixture-boot"
            def numa(inner, bus): return 0
            def identity(inner, pid, uid):
                identity = identities[pid]
                if identity["uid"] != uid: raise ValueError("foreign PID")
                return {key: identity[key] for key in ("pid", "uid", "proc_start_ticks", "cwd", "boot_id")}
        class Backend:
            version = {"backend": "NVML", "unit": "bytes", "nvml": "CPU-MOCK", "driver": "CPU-MOCK", "calls": ["CPU-MOCK"]}
            closed = False
            def read(inner, uuid):
                index = self.uuids.index(uuid)
                return {"capacity_bytes": 10000, "used_bytes": 5000, "free_bytes": 5000,
                        "name": "CPU-MOCK-H20", "pci_bus_id": f"0000:0{index}:00.0", "processes": [{"pid": 100 + index, "used_bytes": 4500}]}
            def close(inner): inner.closed = True
        return identities, Proc(), Backend()

    def test_actual_api_interface_is_mocked_and_foreign_pid_fails_without_kill(self):
        identities, proc, backend = self.live_fixture()
        deployed = {**self.deployment, "deploy_sha256": self.deploy_sha}
        with patch.object(live.os, "getuid", return_value=self.uid, create=True), \
             patch.object(live.socket, "gethostname", return_value=self.config["host"]):
            state = live.snapshot(self.config, self.inputs["run_id"], deployed, backend, proc, utc_ms=self.now)
            self.assertEqual(set(state["gpus"]), set(self.uuids))
            identities[100]["uid"] = self.uid + 1
            with self.assertRaisesRegex(ValueError, "foreign PID"):
                live.snapshot(self.config, self.inputs["run_id"], deployed, backend, proc, utc_ms=self.now)
        self.assertNotIn("pynvml", sys.modules)

    def test_collector_requires_recorded_claim_and_preserves_raw_failure(self):
        identities, proc, backend = self.live_fixture()
        with self.assertRaises(ValueError):
            live.collect(object(), self.data / "capture", lambda: True, backend_factory=lambda: backend)
        claim = self.claim(); claim.reserved = True; claim.check = lambda: None
        claim.verify_reservation = lambda: None  # Explicit fake of POSIX durable reservation for collector unit tests.
        with patch.object(live.os, "getuid", return_value=self.uid, create=True), \
             patch.object(live.socket, "gethostname", return_value=self.config["host"]):
            files = live.collect(claim, self.data / "capture", lambda: True,
                                 backend_factory=lambda: backend, proc=proc, sleep=lambda seconds: None)
            self.assertIn("raw-api.jsonl", files)
            self.assertTrue(backend.closed)

            identities[100]["uid"] = self.uid + 1
            backend.closed = False
            with self.assertRaises(ValueError):
                live.collect(claim, self.data / "failed-capture", lambda: True,
                             backend_factory=lambda: backend, proc=proc)
            self.assertTrue((self.data / "failed-capture/failure.json").exists())
            self.assertTrue((self.data / "failed-capture/raw-api.jsonl").read_text())
            self.assertTrue(backend.closed)

class SelectedG3CPU(Fixture):
    def bundle(self):
        runtime = {"uid": self.uid, "host": self.config["host"], "boot_id": "cpu-fixture-boot",
            "gpu_capacity_bytes": {uuid: 10000 for uuid in self.uuids},
            "gpu_admission_free_bytes": {uuid: 10000 for uuid in self.uuids},
            "gpu_memory_cap_bytes": {uuid: 6500 for uuid in self.uuids},
            "memory_limit_fraction": .65, "memory_sample_max_gap_s": 1.0}
        runtime_file = self.write("g3-runtime.json", runtime)
        chosen = {"replicas": CANDIDATES[0], "pd": CANDIDATES[3], "epd": CANDIDATES[7]}
        selection = {"selected": {system: {"candidate": candidate_id(candidate)} for system, candidate in chosen.items()},
            "required_full_G3": {system: {"candidate": candidate_id(candidate), "candidate_config_sha256": config_sha256(candidate),
                "requests": 120, "source_manifest_sha256": self.source_sha,
                "runtime_binding_sha256": runtime_file["sha256"]} for system, candidate in chosen.items()}}
        fixtures = []
        for session in ("cold", "restart"):
            for images in (1, 4, 8):
                for tokens in (32, 128):
                    for concurrency in (1, 8):
                        case = f"i{images}-o{tokens}-c{concurrency}"
                        for i in range(2 if concurrency == 1 else 8):
                            fixtures.append({"fixture_id": f"{session}/{case}/{i}", "case": case, "session": session,
                                "input": {"prompt": "CPU fixture prompt", "images": [{"path": f"image-{j}.jpg",
                                    "rgb_sha256": hashlib.sha256(str(j).encode()).hexdigest()} for j in range(images)]},
                                "output_tokens": tokens})
        input_file = self.write("full-G3-inputs.json", {"fixtures": fixtures})
        proof = {"schema": "selected-three-G3-proof-v1", "static_config_sha256": guard.digest(self.config),
            "host": self.config["host"], "uid": self.uid, "root": str(self.root), "boot_id": "cpu-fixture-boot",
            "gpu_uuids": self.uuids, "numa_by_uuid": self.config["numa_by_uuid"], "commit": self.commit,
            "source_manifest_sha256": self.source_sha, "deploy_sha256": self.deploy_sha,
            "source_manifest": {"path": self.inputs["source_manifest_file"], "sha256": self.source_sha},
            "deployment": {"path": self.inputs["deploy_file"], "sha256": self.deploy_sha},
            "runtime_binding": runtime_file, "selection": self.write("selected.json", selection), "systems": {}}
        native_reference = []
        for system_index, (system, candidate) in enumerate(chosen.items()):
            cid, run_id = candidate_id(candidate), "CPU-fixture-G3-" + system
            group = {"candidate": cid, "candidate_config_sha256": config_sha256(candidate), "inputs": input_file, "sessions": {}}
            claim_time = self.now + system_index * 100000 - 1000
            claim_mono = system_index * 100.0
            timing = {"clock": "time.perf_counter", "host": self.config["host"], "boot_id": "cpu-fixture-boot",
                "start_utc_ms": claim_time, "start_monotonic": claim_mono,
                "deadline_utc_ms": claim_time + 1600000, "deadline_monotonic": claim_mono + 1600,
                "allocation_seconds": 1600}
            group["admission_booking"] = self.write(system + "-admission-booking.json", self.booking(claim_time))
            unit = {"phase": "selected_g3", "unit": system, "candidate": cid, "allocation": [120, 0, 1600],
                    "deploy_sha256": self.deploy_sha, "run_id": run_id, "booking_sha256": group["admission_booking"]["sha256"], "timing": timing}
            claim_resource = self.resource(); claim_resource.update(run_id=run_id, observed_ms=claim_time, monotonic_s=claim_mono)
            source = {**self.deployment, "deploy_sha256": self.deploy_sha}
            group["claim"] = self.write(system + "-claim.json", {"unit": unit, "static_config_sha256": guard.digest(self.config),
                "resources": claim_resource, "source": source, "timing": timing})
            group["ledger"] = self.write(system + "-ledger.json", {"static_config_sha256": guard.digest(self.config),
                "units": {"selected_g3/" + system: unit}, "spent": {"selected_g3": [120, 0, 1600]}})
            for session_index, name in enumerate(("cold", "restart")):
                prefix = f"{system}-{name}"
                start_utc = self.now + system_index * 100000 + session_index * 30000
                processes = []
                if system == "replicas": stages = ["FULL_REPLICA"] * 3
                elif system == "epd": stages = ["ENCODING", "CONTEXT", "DECODING"]
                else: stages = ["CONTEXT"] * candidate[1] + ["DECODING"] * candidate[2]
                for index, uuid in enumerate(self.uuids):
                    pid = 1000 + system_index * 200 + session_index * 50 + index
                    processes.append({"pid": pid, "proc_start_ticks": pid * 10, "uid": self.uid,
                        "root": str(self.root), "run_id": run_id, "boot_id": "cpu-fixture-boot",
                        "source_commit": self.commit, "deploy_sha256": self.deploy_sha,
                        "gpu_uuid": uuid, "engine_stage": stages[index]})
                session_mono = claim_mono + 1.0 + session_index * 30.0
                rows, windows = [], []
                cases = list(dict.fromkeys(f["case"] for f in fixtures if f["session"] == name))
                for case_index, case in enumerate(cases):
                    selected = [f for f in fixtures if f["session"] == name and f["case"] == case]
                    images = len(selected[0]["input"]["images"])
                    concurrency = int(case.split("-c")[1])
                    start = session_mono + case_index * 2.0
                    windows.append({"case": case, "images": images, "output_tokens": selected[0]["output_tokens"],
                        "concurrency": concurrency, "clock": "time.perf_counter", "host": self.config["host"],
                        "boot_id": "cpu-fixture-boot", "run_id": run_id, "start_monotonic": start, "end_monotonic": start + 1})
                    for index, fixture in enumerate(selected):
                        a, b = (start + .1 + index * .4, start + .3 + index * .4) if concurrency == 1 else (start + .1, start + .9)
                        row = {"fixture_id": fixture["fixture_id"], "request_id": fixture["fixture_id"], "case": case,
                            "session": name, "candidate": cid, "run_id": run_id, "success": True,
                            "input": fixture["input"], "processed_prompt_token_ids": [1, images],
                            "output_token_ids": [2] * fixture["output_tokens"], "submit_monotonic": a, "end_monotonic": b}
                        rows.append(row)
                services = []
                for api_index in range(3 if system == "replicas" else 1):
                    pid = processes[api_index]["pid"] if system == "replicas" else 9000 + system_index * 200 + session_index * 50
                    api = {"pid": pid, "proc_start_ticks": pid * 10, "uid": self.uid,
                        "host": self.config["host"], "root": str(self.root), "boot_id": "cpu-fixture-boot",
                        "run_id": run_id, "source_commit": self.commit, "deploy_sha256": self.deploy_sha}
                    workers = [processes[api_index]] if system == "replicas" else processes
                    api.update(candidate_config_sha256=config_sha256(candidate), endpoint=f"http://127.0.0.1:{17780 + api_index}")
                    for worker in workers:
                        worker.update(candidate_config_sha256=config_sha256(candidate), endpoint=api["endpoint"])
                    services.append({"url": f"http://127.0.0.1:{17780 + api_index}", "api_identity": api,
                        "worker_keys": [f'{worker["pid"]}:{worker["proc_start_ticks"]}' for worker in workers]})
                endpoint_manifest = {"host": self.config["host"], "boot_id": "cpu-fixture-boot", "run_id": run_id,
                    "source_commit": self.commit, "deploy_sha256": self.deploy_sha,
                    "candidate_config_sha256": config_sha256(candidate), "services": services}
                for dispatch, row in enumerate(rows):
                    service = services[dispatch % len(services)]
                    row.update(dispatch_index=dispatch, endpoint=service["url"], observed_api_identity=service["api_identity"])
                    if system == "replicas":
                        route = [processes[dispatch % 3]]
                    else:
                        route = []
                        for stage in ("ENCODING", "CONTEXT", "DECODING"):
                            workers = [worker for worker in processes if worker["engine_stage"] == stage]
                            if workers: route.append(workers[dispatch % len(workers)])
                    row["observed_worker_route"] = route
                registry = {"host": self.config["host"], "uid": self.uid, "boot_id": "cpu-fixture-boot", "run_id": run_id, "processes": processes}
                snapshots, samples = [], []
                for at in range(24):
                    snap = {"host": self.config["host"], "uid": self.uid, "root": str(self.root), "boot_id": "cpu-fixture-boot",
                        "run_id": run_id, "monotonic_s": session_mono + at, "observed_ms": start_utc + at * 1000, "gpus": {}}
                    for process in processes:
                        uuid = process["gpu_uuid"]
                        p = {**process, "used_bytes": 4500}
                        snap["gpus"][uuid] = {"used_bytes": 5000, "capacity_bytes": 10000, "name": "CPU-MOCK-H20", "processes": [p]}
                        samples.append({"gpu_uuid": uuid, "unit": "bytes", "capacity_bytes": 10000,
                            "device_used_bytes": 5000, "monotonic_s": session_mono + at, "processes": [p]})
                    snapshots.append(snap)
                session = {"run_id": run_id, "start_utc_ms": start_utc, "end_utc_ms": start_utc + 23000,
                    "start_monotonic": session_mono, "end_monotonic": session_mono + 23.0,
                    "endpoints": self.write(prefix + "-endpoints.json", endpoint_manifest),
                    "requests": self.write(prefix + "-requests.jsonl", rows, True),
                    "client_windows": self.write(prefix + "-windows.jsonl", windows, True),
                    "registry": self.write(prefix + "-registry.json", registry),
                    "booking": self.write(prefix + "-booking.json", self.booking(start_utc)),
                    "provider": self.write(prefix + "-provider.json", {"backend": "NVML", "unit": "bytes",
                        "driver": "CPU-MOCK", "nvml": "CPU-MOCK", "calls": ["CPU-MOCK"]}),
                    "raw_nvml": self.write(prefix + "-raw.jsonl", snapshots, True),
                    "memory_samples": self.write(prefix + "-samples.jsonl", samples, True),
                    "release": self.write(prefix + "-release.json", {"host": self.config["host"], "uid": self.uid,
                        "root": str(self.root), "run_id": run_id, "boot_id": "cpu-fixture-boot", "observed_ms": start_utc + 24000,
                        "monotonic_s": session_mono + 24.0,
                        "api_exit_observations": [{"pid": service["api_identity"]["pid"],
                            "proc_start_ticks": service["api_identity"]["proc_start_ticks"], "state": "not_present",
                            "observed_ms": start_utc + 24000, "monotonic_s": session_mono + 24.0} for service in services],
                        "gpus": {uuid: {"processes": [], "used_bytes": 0} for uuid in self.uuids}})}
                group["sessions"][name] = session
                if system == "replicas": native_reference.extend(rows)
            proof["systems"][system] = group
        reference = self.write("full-native-reference.jsonl", native_reference, True)
        for group in proof["systems"].values(): group["reference"] = reference
        return proof

    def consume_fake_fixture(self, proof):
        review = self.fake_review("CPU-MOCK-G3-review.json", "G3", guard.digest(proof))
        bundle = self.write("CPU-MOCK-G3-bundle.json", {"proof": proof, "review_file": review["path"], "review_sha256": review["sha256"]})
        return selected_g3.consume(self.owner, bundle["path"], bundle["sha256"], self.config, self.source_sha, self.deploy_sha)

    def test_complete_fixture_is_consumed_but_never_admits_formal(self):
        result = self.consume_fake_fixture(self.bundle())
        self.assertEqual(result["formal_admission"], "blocked_separate_user_formal_budget_required")
        self.assertEqual(result["new_GPU_requests"], 0)

    def test_missing_raw_or_summary_boolean_cannot_replace_full_proof(self):
        proof = self.bundle()
        proof["systems"]["pd"]["passed"] = True
        del proof["systems"]["pd"]["sessions"]["restart"]["memory_samples"]
        with self.assertRaises(KeyError): self.consume_fake_fixture(proof)

    def test_self_review_is_rejected(self):
        proof = self.bundle()
        review = self.write("self-review.json", {"gate": "G3", "decision": "APPROVE", "blocking": 0,
            "scope_sha256": guard.digest(proof), "reviewer_id": self.config["executor_id"], "original_review_text": "CPU MOCK"})
        bundle = self.write("self-bundle.json", {"proof": proof, "review_file": review["path"], "review_sha256": review["sha256"]})
        with self.assertRaises(ValueError):
            selected_g3.consume(self.owner, bundle["path"], bundle["sha256"], self.config, self.source_sha, self.deploy_sha)

    def test_changed_raw_ids_and_reused_restart_process_are_rejected(self):
        proof = self.bundle()
        session = proof["systems"]["pd"]["sessions"]["restart"]
        descriptor = session["requests"]
        rows = [json.loads(line) for line in (self.data / descriptor["path"]).read_bytes().splitlines()]
        rows[0]["output_token_ids"][0] = 3
        session["requests"] = self.write(descriptor["path"], rows, True)
        with self.assertRaisesRegex(ValueError, "reference"):
            self.consume_fake_fixture(proof)
        proof = self.bundle()
        group = proof["systems"]["pd"]
        old = json.loads((self.data / group["sessions"]["cold"]["registry"]["path"]).read_bytes())
        group["sessions"]["restart"]["registry"] = self.write("reused-registry.json", old)
        with self.assertRaisesRegex(ValueError, "Restart reused"):
            self.consume_fake_fixture(proof)

    def test_missing_endpoint_or_single_replica_dispatch_is_rejected(self):
        for mode in ("missing", "one_endpoint"):
            with self.subTest(mode=mode):
                proof = self.bundle()
                session = proof["systems"]["replicas"]["sessions"]["cold"]
                rows = [json.loads(line) for line in (self.data / session["requests"]["path"]).read_bytes().splitlines()]
                if mode == "missing":
                    rows[0].pop("endpoint")
                else:
                    endpoints = json.loads((self.data / session["endpoints"]["path"]).read_bytes())
                    for row in rows:
                        row["endpoint"] = endpoints["services"][0]["url"]
                        row["observed_api_identity"] = endpoints["services"][0]["api_identity"]
                        row["observed_worker_route"] = rows[0]["observed_worker_route"]
                session["requests"] = self.write(session["requests"]["path"], rows, True)
                with self.assertRaises((KeyError, ValueError)):
                    self.consume_fake_fixture(proof)

    def test_actual_endpoint_api_pid_and_worker_uuid_must_match(self):
        for mode in ("api_pid", "worker_uuid"):
            with self.subTest(mode=mode):
                proof = self.bundle()
                session = proof["systems"]["pd"]["sessions"]["restart"]
                rows = [json.loads(line) for line in (self.data / session["requests"]["path"]).read_bytes().splitlines()]
                if mode == "api_pid": rows[0]["observed_api_identity"]["pid"] += 1
                else: rows[0]["observed_worker_route"][0]["gpu_uuid"] = "foreign"
                session["requests"] = self.write(session["requests"]["path"], rows, True)
                with self.assertRaisesRegex(ValueError, "API PID|worker PID"):
                    self.consume_fake_fixture(proof)

    def test_nonfinite_session_snapshot_and_release_utc_are_rejected(self):
        for location in ("session", "snapshot", "release"):
            with self.subTest(location=location):
                proof = self.bundle()
                session = proof["systems"]["epd"]["sessions"]["restart"]
                if location == "session":
                    session["start_utc_ms"] = float("nan")
                elif location == "snapshot":
                    rows = [json.loads(line) for line in (self.data / session["raw_nvml"]["path"]).read_bytes().splitlines()]
                    rows[0]["observed_ms"] = float("nan")
                    session["raw_nvml"] = self.write(session["raw_nvml"]["path"], rows, True)
                else:
                    release = json.loads((self.data / session["release"]["path"]).read_bytes())
                    release["observed_ms"] = float("nan")
                    session["release"] = self.write(session["release"]["path"], release)
                with self.assertRaisesRegex(ValueError, "integer"):
                    self.consume_fake_fixture(proof)

    def test_snapshot_clock_anchor_mismatch_is_rejected(self):
        proof = self.bundle()
        session = proof["systems"]["pd"]["sessions"]["cold"]
        rows = [json.loads(line) for line in (self.data / session["raw_nvml"]["path"]).read_bytes().splitlines()]
        rows[0]["observed_ms"] += 1000
        session["raw_nvml"] = self.write(session["raw_nvml"]["path"], rows, True)
        with self.assertRaisesRegex(ValueError, "clock anchor"):
            self.consume_fake_fixture(proof)

    def test_actual_claim_deadline_is_not_reset_at_late_cold_start(self):
        proof = self.bundle()
        session = proof["systems"]["pd"]["sessions"]["restart"]
        claim = json.loads((self.data / proof["systems"]["pd"]["claim"]["path"]).read_bytes())
        session["end_utc_ms"] = claim["timing"]["deadline_utc_ms"] + 1
        session["end_monotonic"] = claim["timing"]["deadline_monotonic"] + .001
        with self.assertRaisesRegex(ValueError, "actual durable claim"):
            self.consume_fake_fixture(proof)

    def test_cross_system_claim_before_previous_release_is_rejected(self):
        proof = self.bundle()
        previous = proof["systems"]["replicas"]["sessions"]["restart"]
        release = json.loads((self.data / previous["release"]["path"]).read_bytes())
        group = proof["systems"]["pd"]
        claim = json.loads((self.data / group["claim"]["path"]).read_bytes())
        timing = claim["timing"]
        timing["start_utc_ms"] = release["observed_ms"] - 1
        timing["start_monotonic"] = (timing["start_utc_ms"] - (self.now - 1000)) / 1000
        timing["deadline_utc_ms"] = timing["start_utc_ms"] + 1600000
        timing["deadline_monotonic"] = timing["start_monotonic"] + 1600
        claim["unit"]["timing"] = timing
        group["claim"] = self.write(group["claim"]["path"], claim)
        ledger = json.loads((self.data / group["ledger"]["path"]).read_bytes())
        ledger["units"]["selected_g3/pd"] = claim["unit"]
        group["ledger"] = self.write(group["ledger"]["path"], ledger)
        with self.assertRaisesRegex(ValueError, "Cross-system overlap"):
            self.consume_fake_fixture(proof)



if __name__ == "__main__":
    unittest.main(verbosity=2)
