"""Qualification identity CPU tests; use the fixed runner and its controlled tmp."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import production_identity as bridge
from experiment_plan import config_sha256


class ProductionIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp_root = Path(os.environ["EPD_CPU_TEST_TMP"]).resolve(strict=True)
        self.temp = tempfile.TemporaryDirectory(dir=self.tmp_root)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(self.tmp_root)
        self.uuids = ["GPU-" + str(i) * 8 + "-1111-1111-1111-111111111111" for i in range(3)]
        self.env = {"REPRO_IDENTITY": "1", "EXP_ROOT": str(self.root), "REPRO_RUN_ID": "cpu-unit-only",
                    "REPRO_SOURCE_COMMIT": "a" * 40, "REPRO_DEPLOY_SHA256": "b" * 64,
                    "REPRO_PROFILE_SHA256": config_sha256(("replicas", 0, 0, 4)),
                    "REPRO_ENDPOINT": "http://127.0.0.1:17778", "REPRO_GPU_UUIDS": json.dumps(self.uuids)}
        self.environ = patch.dict(os.environ, self.env)
        self.environ.start()
        self.cwd = patch.object(Path, "cwd", return_value=self.root)
        self.cwd.start()

    def tearDown(self):
        self.cwd.stop()
        self.environ.stop()
        self.temp.cleanup()

    def test_disabled_does_not_read_identity_inputs(self):
        with patch.dict(os.environ, {"REPRO_IDENTITY": "0"}), patch.dict(sys.modules, {"torch": None}):
            self.assertEqual(bridge.environment(), {})
            self.assertIsNone(bridge.worker_identity(None, "CONTEXT"))

    def test_actual_uuid_forwarded_to_self_capture_not_expected_rank(self):
        cuda = NS(get_device_properties=lambda device: NS(uuid=self.uuids[2]))
        with patch.dict(sys.modules, {"torch": NS(cuda=cuda)}), patch.object(bridge, "capture_own_identity", return_value={}) as capture:
            bridge.worker_identity("actual-device", "CONTEXT")
            self.assertEqual(capture.call_args.args[4:6], (self.uuids[2], "CONTEXT"))
            self.assertEqual(capture.call_args.kwargs["endpoint"], self.env["REPRO_ENDPOINT"])

    def test_foreign_uuid_refused_before_sidecar(self):
        cuda = NS(get_device_properties=lambda device: NS(uuid="GPU-foreign"))
        with patch.dict(sys.modules, {"torch": NS(cuda=cuda)}), patch.object(bridge, "capture_own_identity") as capture:
            with self.assertRaises(ValueError): bridge.worker_identity(0, "DECODING")
            capture.assert_not_called()

    def test_actual_profile_and_cli_mismatch_refused(self):
        args = NS(max_num_seqs=4, gpu_memory_utilization=0.65)
        bridge.validate_profile(args, baseline=True)
        args.max_num_seqs = 8
        with self.assertRaises(ValueError): bridge.validate_profile(args, baseline=True)
        args.max_num_seqs, args.gpu_memory_utilization = 4, 0.9
        with self.assertRaises(ValueError): bridge.validate_profile(args, baseline=True)

    def test_route_uses_only_selected_stage_workers_and_does_not_grow_per_token(self):
        request = NS()
        batch = NS(requests=[request])
        p2 = {"pid": 22, "proc_start_ticks": 220, "engine_stage": "CONTEXT"}
        d1 = {"pid": 31, "proc_start_ticks": 310, "engine_stage": "DECODING"}
        bridge.mark_batch(batch, [p2]); bridge.mark_batch(batch, [d1]); bridge.mark_batch(batch, [d1])
        self.assertEqual(request.repro_worker_route, [p2, d1])
        service = {"api_identity": {"pid": 1}}
        self.assertEqual(bridge.response_identity(service, request.repro_worker_route)["repro_worker_route"], [p2, d1])
        with self.assertRaises(ValueError): bridge.response_identity(service, [])

    def test_baseline_only_accepts_loaded_local_TP1_driver(self):
        Worker = type("Worker", (), {"__module__": "vllm.worker.worker"})
        worker = Worker()
        worker.device, worker.model_runner = "cuda:0", NS(model=object())
        Executor = type("GPUExecutorAsync", (), {})
        executor = Executor()
        executor.driver_worker = NS(worker=worker)
        engine = NS(engine=NS(model_executor=executor, parallel_config=NS(tensor_parallel_size=1)))
        with patch.object(bridge, "worker_identity", return_value={"pid": 12}) as capture:
            self.assertEqual(bridge.baseline_worker_identity(engine), {"pid": 12})
            capture.assert_called_once_with("cuda:0", "FULL_REPLICA")
        engine.engine.parallel_config.tensor_parallel_size = 2
        with self.assertRaises(ValueError): bridge.baseline_worker_identity(engine)

    def test_server_produces_manifest_and_actual_cached_response(self):
        identity = {"pid": os.getpid(), "uid": os.getuid(), "proc_start_ticks": 123,
                    "cwd": str(self.root), "boot_id": "cpu-mock-boot"}
        proc = NS(identity=lambda pid, uid: dict(identity), boot=lambda: "cpu-mock-boot")
        worker = {**identity, **bridge.scope(), "root": str(self.root),
                  "endpoint": self.env["REPRO_ENDPOINT"], "gpu_uuid": self.uuids[0], "engine_stage": "FULL_REPLICA"}
        with patch.object(bridge, "ProcReader", return_value=proc):
            service = bridge.publish_service([worker], 17778)
            paths = list((self.root / "runtime/endpoints").glob("*.json"))
            self.assertEqual(len(paths), 1)
            manifest = bridge.assemble_services(paths, self.root / "runtime/endpoints-merged.json")
            self.assertEqual(manifest["services"], [service])
            response = bridge.response_identity(service, [worker])
            self.assertEqual(response["repro_api_identity"], service["api_identity"])
            self.assertEqual(response["repro_worker_route"], [worker])
            worker["candidate_config_sha256"] = "f" * 64
            with self.assertRaises(ValueError): bridge.publish_service([worker], 17778)

    def test_port_mismatch_does_not_publish_service(self):
        with self.assertRaises(ValueError): bridge.publish_service([{}], 17779)

    def test_bad_endpoint_and_missing_source_fail_closed(self):
        with patch.dict(os.environ, {"REPRO_ENDPOINT": "http://remote:17778"}):
            with self.assertRaises(ValueError): bridge.environment()
        with patch.dict(os.environ, {"REPRO_SOURCE_COMMIT": ""}):
            with self.assertRaises(ValueError): bridge.environment()


if __name__ == "__main__":
    unittest.main()
