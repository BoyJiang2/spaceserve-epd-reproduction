"""Execute production control methods with CPU fakes; never import torch/ray/vllm."""
import ast
import os
import asyncio
import importlib.util
import sys
import time
import types
import unittest
import json
import hashlib
import tempfile
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
TEST_TMP = Path(os.environ.get("EPD_CPU_TEST_TMP", ROOT / "tests")).resolve()
package = types.ModuleType("epdserve")
package.__path__ = [str(ROOT / "epdserve")]
sys.modules["epdserve"] = package
spec = importlib.util.spec_from_file_location("epdserve.pd", ROOT / "epdserve/pd.py")
pd = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pd
spec.loader.exec_module(pd)
options_spec = importlib.util.spec_from_file_location("runtime_options", ROOT / "runtime_options.py")
options_module = importlib.util.module_from_spec(options_spec)
options_spec.loader.exec_module(options_module)
admission_spec = importlib.util.spec_from_file_location("admission", ROOT / "admission.py")
admission = importlib.util.module_from_spec(admission_spec)
sys.modules["admission"] = admission
admission_spec.loader.exec_module(admission)
window_spec = importlib.util.spec_from_file_location("client_window", ROOT / "client_window.py")
client_window = importlib.util.module_from_spec(window_spec)
window_spec.loader.exec_module(client_window)
plan_spec = importlib.util.spec_from_file_location("experiment_plan", ROOT / "experiment_plan.py")
plan = importlib.util.module_from_spec(plan_spec)
plan_spec.loader.exec_module(plan)


def method(file, cls, name, **namespace):
    tree = ast.parse((ROOT / "epdserve" / file).read_text(encoding="utf-8"))
    target = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == cls)
    fn = next(node for node in target.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)
    fn.decorator_list = []
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), fn], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(ROOT / "epdserve" / file), "exec"), namespace)
    return namespace[name]


def request(rid=7, tokens=32):
    return NS(request_id=rid, enable_irp=False, is_sharded=False,
              get_num_input_tokens=lambda: tokens, is_finished=False,
              generated_tokens=["first"], generated_token_ids=[11],
              vllm_seq_metadata=NS(seq_data={rid: object()}),
              multi_modal_data={"image": [f"image-{rid}"]})


def engine(waiting=(), capacity=100):
    return NS(sched_config=NS(max_tokens_per_batch=4096),
              block_manager=NS(max_num_gpu_blocks=capacity),
              cache_config=NS(block_size=16),
              scheduler=NS(waiting_queue=list(waiting), num_on_fly_request_block=0,
                           _get_block_needed=lambda n: (n + 15) // 16))


class PDConfigAndRouting(unittest.TestCase):
    def config(self, p=1, d=2):
        def stage(n):
            return NS(data_parallel_size=n, tensor_parallel_size=1, pipeline_parallel_size=1)
        return NS(encoding=stage(0), context=stage(p), decoding=stage(d))

    def test_three_gpu_allocations_and_reject_extra_actor(self):
        model = NS(model="MiniCPM-V-2_6", dtype="fp16")
        for p, d in ((1, 2), (2, 1)):
            pd.validate_pd_config(model, self.config(p, d))
        for p, d in ((1, 1), (2, 2), (0, 3), (3, 0)):
            with self.assertRaises(ValueError):
                pd.validate_pd_config(model, self.config(p, d))
        cfg = self.config()
        cfg.encoding.data_parallel_size = 1
        with self.assertRaises(ValueError):
            pd.validate_pd_config(model, cfg)
        cfg = self.config()
        cfg.context.tensor_parallel_size = 2
        with self.assertRaises(ValueError):
            pd.validate_pd_config(model, cfg)
        for model in (NS(model="other", dtype="fp16"), NS(model="MiniCPM-V-2_6", dtype="fp32")):
            with self.assertRaises(ValueError):
                pd.validate_pd_config(model, self.config())

    def test_routes_to_less_pending_tokens_without_migration(self):
        engines = [engine([request(9, 100)]), engine()]
        req = request()
        pd.enqueue_pd_request(engines, req)
        self.assertIs(engines[1].scheduler.waiting_queue[0], req)
        self.assertEqual(engines[0].scheduler.waiting_queue[0].request_id, 9)

    def test_running_work_and_capacity_affect_routing(self):
        engines = [engine(), engine()]
        engines[0].scheduler.num_on_fly_request_block = 3
        pd.enqueue_pd_request(engines, request())
        self.assertEqual(len(engines[1].scheduler.waiting_queue), 1)
        with self.assertRaises(ValueError):
            pd.enqueue_pd_request([engine(capacity=1)], request(tokens=32))
        with self.assertRaises(ValueError):
            pd.enqueue_pd_request([], request())
        with self.assertRaises(ValueError):
            pd.enqueue_pd_request([engine()], request(tokens=4097))

    def test_rejects_shards_and_batch_id_reordering(self):
        reqs = [request(7), request(13)]
        seqs = [r.vllm_seq_metadata for r in reqs]
        pd.validate_pd_batch([7, 13], seqs, reqs)
        for ids, metadata in (([13, 7], seqs), ([7, 7], seqs), ([7], seqs), ([], [])):
            with self.assertRaises(ValueError):
                pd.validate_pd_batch(ids, metadata, reqs)
        for invalid in ("7_1_2", True):
            with self.assertRaises(ValueError):
                pd.enqueue_pd_request([engine()], request(invalid))
        reqs[0].enable_irp = True
        with self.assertRaises(ValueError):
            pd.validate_pd_batch([7, 13], seqs, reqs)


class WorkerMethods(unittest.TestCase):
    def test_one_call_uses_local_embedding_identity_and_order(self):
        step = method("worker.py", "Worker", "step_pd", EngineStage=NS(CONTEXT="P"))
        reqs = [request(7), request(13)]
        tensor = object()
        calls = []
        def encode(batch):
            calls.append(("vision", [r.request_id for r in batch.requests]))
            return tensor
        def prefill(ids, seqs, local_vision_embeddings):
            self.assertIs(local_vision_embeddings, tensor)
            calls.append(("prefill", ids))
            return [41, 42]
        worker = NS(stage="P", model_config=NS(pd_fused=True),
                    _encode_vision=encode, step_llm=prefill)
        self.assertEqual(step(worker, [7, 13], [r.vllm_seq_metadata for r in reqs], NS(requests=reqs)), [41, 42])
        self.assertEqual(calls, [("vision", [7, 13]), ("prefill", [7, 13])])
        self.assertFalse(hasattr(worker, "ve_cache"))
        calls.clear()
        with self.assertRaises(ValueError):
            step(worker, [13, 7], [r.vllm_seq_metadata for r in reqs], NS(requests=reqs))
        self.assertEqual(calls, [])

    def test_shared_encoder_preserves_each_images_and_crop_sizes(self):
        calls = []
        def map_input(model_config, data):
            calls.append(data)
            return {"pixel_values": data["image"], "tgt_sizes": [len(data["image"])]}
        captured = {}
        model = NS(_parse_and_validate_inputs=lambda placeholder, **kwargs: kwargs,
                   get_vision_hidden_states=lambda inputs: captured.setdefault("inputs", inputs))
        encode = method("worker.py", "Worker", "_encode_vision",
                        MultiModalInputs=NS(as_kwargs=lambda data, device: data),
                        torch=NS(randn=lambda n: "CPU placeholder"))
        worker = NS(model_config=NS(model="MiniCPM-V-2_6"),
                    mm_registry=NS(map_input=map_input), vllm_model_config=object(),
                    model_runner=NS(model=model), device="fake-cpu")
        reqs = [request(7), request(13)]
        reqs[1].multi_modal_data["image"] = ["b", "c", "d", "e"]
        result = encode(worker, NS(requests=reqs))
        self.assertEqual(result["pixel_values"], [["image-7"], ["b", "c", "d", "e"]])
        self.assertEqual(result["tgt_sizes"], [[1], [4]])
        self.assertIs(calls[0], reqs[0].multi_modal_data)
        self.assertIs(calls[1], reqs[1].multi_modal_data)

    def test_worker_waits_for_cuda_completion_before_kv_ack(self):
        events = []
        migrate = method("worker.py", "Worker", "migrate_blocks_context",
                         torch=NS(ops=NS(block_migration_ops=NS(migrate_blocks_context=lambda *args: events.append("copy"))),
                                  cuda=NS(synchronize=lambda: events.append("synchronize"))))
        config = NS(pipeline_parallel_size=1, tensor_parallel_size=1,
                    data_parallel_rank=1, pipeline_parallel_rank=0, tensor_parallel_rank=0)
        worker = NS(parallel_config=config, kv_cache=object())
        migrate(worker, [9], config, [11])
        self.assertEqual(events, ["copy", "synchronize"])


class CommonEngineOptions(unittest.TestCase):
    supported = {"model", "dtype", "tensor_parallel_size", "enforce_eager", "trust_remote_code",
                 "seed", "max_model_len", "max_num_seqs", "max_num_batched_tokens",
                 "enable_prefix_caching", "disable_mm_preprocessor_cache",
                 "gpu_memory_utilization", "limit_mm_per_prompt"}

    def test_profiles_share_context_limits_and_cache_policy(self):
        for cap in (4, 8):
            options = options_module.engine_options("MiniCPM-V-2_6", .65, cap, self.supported)
            self.assertEqual(options["limit_mm_per_prompt"], {"image": 8})
            self.assertEqual(options["max_num_seqs"], cap)
            self.assertEqual(options["max_model_len"], 4096)
            self.assertFalse(options["enable_prefix_caching"])
            self.assertTrue(options["disable_mm_preprocessor_cache"])
            self.assertEqual(options["seed"], 0)

    def test_unsupported_required_option_fails_instead_of_silent_weak_baseline(self):
        with self.assertRaises(ValueError):
            options_module.engine_options("MiniCPM-V-2_6", .65, 8, self.supported - {"limit_mm_per_prompt"})
        for memory, cap in ((.9, 8), (.65, 16)):
            with self.assertRaises(ValueError):
                options_module.engine_options("MiniCPM-V-2_6", memory, cap, self.supported)
        options = options_module.engine_options("MiniCPM-V-2_6", .65, 8, self.supported - {"disable_mm_preprocessor_cache"})
        self.assertNotIn("disable_mm_preprocessor_cache", options)


def run_immediate(coroutine):
    # No socketpair/event loop in Windows sandbox; these CPU fakes never suspend.
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    finally:
        coroutine.close()
    raise AssertionError("CPU fake unexpectedly suspended")


async def gather_immediate(*coroutines):
    return [await coroutine for coroutine in coroutines]


class LifecycleMethods(unittest.TestCase):
    def test_model_initialization_failure_is_propagated(self):
        async def failure():
            raise RuntimeError("model init failed")
        init = method("engine_common.py", "StageEngine", "_init_model",
                      asyncio=NS(gather=gather_immediate))
        instance = NS(_remote_call_all_workers_async=lambda name: [failure()])
        with self.assertRaisesRegex(RuntimeError, "model init failed"):
            run_immediate(init(instance))

    def test_destination_allocation_failure_preserves_generated_tokens(self):
        req = request(17)
        def failure(req):
            raise RuntimeError("no KV capacity")
        migrate = method("engine_decoding.py", "DecodingStageEngine", "_migrate_blocks_context")
        instance = NS(block_manager=NS(allocate_blocks=failure))
        with self.assertRaisesRegex(RuntimeError, "no KV capacity"):
            run_immediate(migrate(instance, NS(req=req)))
        self.assertEqual(req.generated_token_ids, [11])
        self.assertEqual(req.generated_tokens, ["first"])

    def test_fused_context_does_not_allocate_vision_cache(self):
        init = method("engine_context.py", "ContextStageEngine", "_init_vecache")
        instance = NS(model_config=NS(pd_fused=True))
        run_immediate(init(instance))
        self.assertIsNone(instance.vision_block_manager)

    async def migrate(self, fail):
        events, freed, calls = [], [], []
        req = request(17)
        source = NS(data_parallel_rank=1)
        migration = NS(req=req, block_indexes=[9, 11], source_parallel_config=source)
        async def transfer():
            events.append("transfer")
            if fail:
                raise RuntimeError("simulated failed KV transfer")
        def remote(name, *args):
            calls.append((name, args))
            return [transfer()]
        async def clear(record):
            freed.append(record.req.request_id)
        instance = NS(block_manager=NS(allocate_blocks=lambda r: None,
                                     get_block_table=lambda rid: [20, 21]),
                      _remote_call_all_workers_async=remote,
                      clear_migrated_blocks_callback_context=clear,
                      engine_on_new_lifetime_event_callback=lambda rid, ev: events.append((rid, ev)))
        migrate = method("engine_decoding.py", "DecodingStageEngine", "_migrate_blocks_context",
                         asyncio=NS(gather=gather_immediate), LifetimeEvent=lambda x: x,
                         LifetimeEventType=NS(MigrationBegin="begin", MigrationEnd="end"))
        if fail:
            with self.assertRaisesRegex(RuntimeError, "failed KV transfer"):
                await migrate(instance, migration)
            self.assertEqual(freed, [])
            self.assertNotIn((17, "end"), events)
        else:
            await migrate(instance, migration)
            self.assertEqual(freed, [17])
            self.assertEqual(events, [(17, "begin"), "transfer", (17, "end")])
        self.assertIs(calls[0][1][1], source)
        self.assertEqual(calls[0][1][0], [9, 11])
        self.assertEqual(calls[0][1][2], [20, 21])
        self.assertEqual(req.generated_token_ids, [11])

    def test_successful_kv_transfer_frees_correct_source_after_await(self):
        run_immediate(self.migrate(False))

    def test_failed_kv_transfer_preserves_source_and_raises(self):
        run_immediate(self.migrate(True))

    def test_fused_prefill_enqueues_original_rid_and_source_dp(self):
        reqs = [request(7), request(13)]
        class Batch:
            requests = reqs
            def __len__(self): return len(self.requests)
            def get_request_ids(self): return [r.request_id for r in self.requests]
            def start_one_iteration(self, stamp): pass
            def finish_one_iteration(self, tokens, ids, stamp):
                for r, token, tid in zip(self.requests, tokens, ids):
                    r.generated_tokens, r.generated_token_ids = [token], [tid]
        calls, bridge, outputs = [], [], []
        async def result(): return [31, 32]
        def remote(name, *args):
            calls.append((name, args))
            return [result()]
        source = NS(data_parallel_rank=1, pipeline_parallel_size=1, tensor_parallel_size=1)
        instance = NS(model_config=NS(pd_fused=True),
                      scheduler=NS(get_next_batch_and_pop=lambda: Batch(), on_finish_requests=lambda b: None),
                      block_manager=NS(allocate_blocks_batched=lambda b: None,
                                       get_partial_block_table=lambda ids: [[91], [92]],
                                       get_block_table=lambda rid: [rid + 100]),
                      batches_in_pipeline=[], batches_ret_futures=[], parallel_config=source,
                      engine_on_new_lifetime_event_callback=lambda *args: None,
                      engine_on_new_step_output_callback=lambda rid, out: outputs.append(rid),
                      tokenizer=NS(decode=str), _remote_call_all_workers_async=remote,
                      context_decode_bridge_queue=NS(put_nowait=bridge.append))
        step = method("engine_context.py", "ContextStageEngine", "_step",
                      asyncio=asyncio, time=time, LifetimeEvent=lambda x: x,
                      LifetimeEventType=NS(ContextBegin="begin", ContextEnd="end"),
                      StepOutput=lambda req, tok, tid: (req.request_id, tok, tid),
                      MigratingRequest=lambda **kwargs: NS(**kwargs))
        run_immediate(step(instance))
        self.assertEqual(calls[0][0], "step_pd")
        self.assertEqual(calls[0][1][0], [7, 13])
        self.assertEqual(outputs, [7, 13])
        self.assertEqual([r.req.request_id for r in bridge], [7, 13])
        self.assertTrue(all(r.source_parallel_config is source for r in bridge))
        self.assertEqual([r.block_indexes for r in bridge], [[107], [113]])


class Isolation(unittest.TestCase):
    def test_model_stack_was_not_imported(self):
        self.assertFalse(any(name in sys.modules for name in ("torch", "ray", "vllm")))


class PlanSelection(unittest.TestCase):
    source = "a" * 64
    runtime = "b" * 64

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=TEST_TMP)
        self.artifacts = Path(self.temporary.name)
        assert self.artifacts.resolve().is_relative_to(TEST_TMP)
        self.addCleanup(self.temporary.cleanup)
        self.runtime_data = {"uid": 2147, "host": "CPU-fixture-host", "boot_id": "CPU-fixture-boot",
            "gpu_capacity_bytes": {f"GPU-CPU-fixture-{i}": 10000 for i in range(3)},
            "gpu_admission_free_bytes": {f"GPU-CPU-fixture-{i}": 10000 for i in range(3)},
            "gpu_memory_cap_bytes": {f"GPU-CPU-fixture-{i}": 6500 for i in range(3)},
            "memory_limit_fraction": .65, "memory_sample_max_gap_s": 1.0}

    def memory_evidence(self, row):
        cid = row["candidate"]
        rate = row.get("requests_per_s", 1.0)
        outer_end = 1.0 + 16.0 / rate
        stamps = list(range(int(outer_end) + 1))
        if stamps[-1] != outer_end:
            stamps.append(outer_end)
        run_id = "CPU-fixture-" + cid
        registry = {"uid": 2147, "host": "CPU-fixture-host", "boot_id": "CPU-fixture-boot", "run_id": run_id,
            "processes": [{"pid": 100 + i, "uid": 2147, "run_id": run_id,
                           "proc_start_ticks": 1000 + i, "gpu_uuid": uuid}
                          for i, uuid in enumerate(self.runtime_data["gpu_capacity_bytes"])]}
        samples = [{"gpu_uuid": process["gpu_uuid"], "unit": "bytes", "capacity_bytes": 10000,
                    "device_used_bytes": 5000, "monotonic_s": at,
                    "processes": [{key: value for key, value in {**process, "used_bytes": 4500}.items()
                                   if key != "gpu_uuid"}]}
                   for at in stamps for process in registry["processes"]]
        registry_path = self.artifacts / (cid + "-registry.json")
        samples_path = self.artifacts / f'{cid}-{row["repeat"]}-{row["load"]}-samples.jsonl'
        requests_path = self.artifacts / f'{cid}-{row["repeat"]}-{row["load"]}-requests.jsonl'
        requests = [{"candidate": cid, "repeat": row["repeat"], "load": row["load"], "run_id": run_id,
                     "request_id": index, "success": True, "warmup": index < 4,
                     "submit_monotonic": .1 if index < 4 else 1.0 + (outer_end - 1.0) * .1,
                     "end_monotonic": .9 if index < 4 else outer_end - (outer_end - 1.0) * .1} for index in range(20)]
        requests_path.write_text("".join(json.dumps(record) + "\n" for record in requests), encoding="utf-8")
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        samples_path.write_text("".join(json.dumps(sample) + "\n" for sample in samples), encoding="utf-8")
        receipt = {"candidate": cid, "repeat": row["repeat"], "load": row["load"],
            "candidate_config_sha256": self.qualifications()[cid]["candidate_config_sha256"],
            "source_manifest_sha256": self.source, "runtime_binding_sha256": self.runtime,
            "scope": "calibration_memory", "uid": 2147, "host": "CPU-fixture-host",
            "boot_id": "CPU-fixture-boot", "unit": "bytes", "run_id": run_id,
            "start_monotonic": 0.0, "end_monotonic": outer_end,
            "requests_file": requests_path.name,
            "requests_sha256": hashlib.sha256(requests_path.read_bytes()).hexdigest(),
            "process_registry_file": registry_path.name,
            "process_registry_sha256": hashlib.sha256(registry_path.read_bytes()).hexdigest(),
            "samples_file": samples_path.name,
            "samples_sha256": hashlib.sha256(samples_path.read_bytes()).hexdigest()}
        window = {key: value for key, value in receipt.items() if key in
                  ("candidate", "repeat", "load", "run_id", "uid", "host", "boot_id",
                   "candidate_config_sha256", "source_manifest_sha256", "runtime_binding_sha256",
                   "requests_sha256")}
        window.update(scope="calibration_client_window", schema="calibration-client-window-v1",
                      clock="time.perf_counter", warmup_requests=4, measured_requests=16,
                      warmup_start_monotonic=0.0, warmup_end_monotonic=1.0,
                      measurement_start_monotonic=1.0, measurement_end_monotonic=outer_end)
        window_path = self.artifacts / f'{cid}-{row["repeat"]}-{row["load"]}-window.json'
        window_path.write_text(json.dumps(window), encoding="utf-8")
        receipt.update(client_window_file=window_path.name,
                       client_window_sha256=hashlib.sha256(window_path.read_bytes()).hexdigest())
        receipt_path = self.artifacts / f'{cid}-{row["repeat"]}-{row["load"]}-memory.json'
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        return {"memory_receipt_file": receipt_path.name,
                "memory_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                "run_id": run_id, "warmup_start_monotonic": 0.0,
                "measurement_start_monotonic": 1.0, "measure_end_monotonic": outer_end}

    def qualifications(self):
        return {plan.candidate_id(candidate): {
            "passed": True, "receipt_sha256": plan.config_sha256(candidate),
            "candidate_config_sha256": plan.config_sha256(candidate),
            "source_manifest_sha256": self.source,
            "runtime_binding_sha256": self.runtime}
            for candidate in plan.CANDIDATES}

    def select(self, rows, qualifications=None):
        return plan.select_calibration(rows, self.qualifications() if qualifications is None else qualifications,
                                       self.source, self.runtime, runtime=self.runtime_data,
                                       artifact_root=self.artifacts)

    def test_qualification_and_final_G3_fit_original_480_budget(self):
        qualification = plan.qualification_schedule()
        self.assertEqual(sum(row["requests"] for row in qualification), 120)
        self.assertEqual(120 + 3 * 120, 480)
        selected = self.select(self.rows())
        self.assertEqual(selected["formal_admission"], "blocked_pending_selected_config_full_G3")
        self.assertEqual(len(selected["required_full_G3"]), 3)
        self.assertEqual(sum(row["requests"] for row in selected["required_full_G3"].values()), 360)

    def test_profile_or_source_receipt_cannot_be_reused(self):
        for field in ("candidate_config_sha256", "source_manifest_sha256", "runtime_binding_sha256"):
            qualifications = self.qualifications()
            qualifications["pd-p1-d2-b4"][field] = "0" * 64
            with self.assertRaises(ValueError):
                self.select(self.rows(), qualifications)
        with self.assertRaises(ValueError):
            self.select(self.rows(), {})
        qualifications = self.qualifications()
        qualifications["pd-p1-d2-b4"]["passed"] = False
        with self.assertRaisesRegex(ValueError, "before exact-candidate qualification"):
            self.select(self.rows(), qualifications)
        rows = self.rows()
        for row in rows:
            row.pop("qualification_receipt_sha256")
            row["correctness_passed"] = True
        with self.assertRaises(ValueError):
            self.select(rows)

    def qualification_fixture(self):
        candidate = plan.CANDIDATES[0]
        cid = plan.candidate_id(candidate)
        records, fixtures = [], []
        for case in plan.qualification_schedule():
            if case["candidate"] != cid:
                continue
            for index in range(case["requests"]):
                key = f'{case["case"]}-{index}'
                data = {"prompt": "CPU fixture prompt " + key,
                        "images": [{"path": f"image-{key}-{i}.jpg",
                                    "rgb_sha256": hashlib.sha256(f"RGB-{key}-{i}".encode()).hexdigest()}
                                   for i in range(case["images"])]}
                fixtures.append({"fixture_id": key, "case": case["case"], "input": data,
                                 "output_tokens": case["tokens"]})
                records.append({"candidate": cid, "case": case["case"], "fixture_id": key,
                    "request_id": key, "images": case["images"], "input": data,
                    "output_token_ids": [2] * case["tokens"], "processed_prompt_token_ids": [1],
                    "success": True, "submit_monotonic": 0, "end_monotonic": 1})
        path, log = self.artifacts / "qualification.json", self.artifacts / "requests.jsonl"
        inputs, reference = self.artifacts / "inputs.json", self.artifacts / "reference.jsonl"
        inputs.write_text(json.dumps({"fixtures": fixtures}), encoding="utf-8")
        reference.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
        input_sha = hashlib.sha256(inputs.read_bytes()).hexdigest()
        reference_sha = hashlib.sha256(reference.read_bytes()).hexdigest()
        receipt = {"candidate": cid, "candidate_config_sha256": plan.config_sha256(candidate),
            "source_manifest_sha256": self.source, "runtime_binding_sha256": self.runtime,
            "scope": "candidate_eligibility_only", "status": "passed", "requests_file": log.name,
            "inputs_file": inputs.name, "inputs_sha256": input_sha,
            "reference_file": reference.name, "reference_sha256": reference_sha}
        def save():
            log.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
            receipt["requests_sha256"] = hashlib.sha256(log.read_bytes()).hexdigest()
            path.write_text(json.dumps(receipt), encoding="utf-8")
        def load(which=candidate):
            return plan.load_qualification(path, which, self.source, self.runtime, input_sha, reference_sha)
        save()
        return records, receipt, path, log, reference, save, load

    def test_actual_qualification_log_binding_count_and_concurrency(self):
        records, receipt, path, log, reference, save, load = self.qualification_fixture()
        self.assertTrue(load()["passed"])
        with self.assertRaises(ValueError):
            load(plan.CANDIDATES[1])
        records[-1]["success"] = False
        save()
        with self.assertRaises(ValueError):
            load()
        records[-1]["success"] = True
        for index, row in enumerate(records):
            row["submit_monotonic"], row["end_monotonic"] = index * 2, index * 2 + 1
        save()
        with self.assertRaisesRegex(ValueError, "concurrency"):
            load()
        receipt["requests_file"] = "../outside.jsonl"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "artifact directory"):
            load()
        receipt["requests_file"] = log.name
        path.write_text(json.dumps(receipt), encoding="utf-8")
        log.write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA"):
            load()

    def test_wrong_actual_IDs_are_rejected_even_with_true_boolean(self):
        records, receipt, path, log, reference, save, load = self.qualification_fixture()
        for field in ("output_token_ids", "processed_prompt_token_ids"):
            with self.subTest(field=field):
                old = list(records[-1][field])
                records[-1][field][0] += 1
                records[-1]["reference_match"] = True
                save()
                with self.assertRaisesRegex(ValueError, "token IDs differ"):
                    load()
                records[-1][field] = old
        save()
        self.assertTrue(load()["passed"])
        reference.write_text(reference.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA"):
            load()

    def test_prompt_and_ordered_images_are_bound_to_actual_fixture(self):
        records, receipt, path, log, reference, save, load = self.qualification_fixture()
        records[-1]["input"]["images"].reverse()
        records[-1]["reference_match"] = True
        save()
        with self.assertRaisesRegex(ValueError, "ordered image"):
            load()
        records[-1]["input"]["images"].reverse()
        records[-1]["input"]["prompt"] += " changed"
        save()
        with self.assertRaisesRegex(ValueError, "prompt"):
            load()

    def test_candidate_server_arguments_match_three_gpu_profiles(self):
        for candidate in plan.CANDIDATES:
            config = plan.candidate_arguments(candidate)
            system, p, d, cap = candidate
            self.assertEqual(config["instances"], 3 if system == "replicas" else 1)
            arguments = config["arguments"]
            self.assertEqual(arguments[arguments.index("--gpu-memory-utilization") + 1], "0.65")
            if system != "replicas":
                self.assertEqual(arguments[arguments.index("--context-data-parallel-size") + 1], str(p))
                self.assertEqual(arguments[arguments.index("--decoding-data-parallel-size") + 1], str(d))
                self.assertEqual(arguments[arguments.index("--runtime-max-num-seqs") + 1], str(cap))
                self.assertEqual("--pd-fused" in arguments, system == "pd")

    def test_memory_requires_raw_bytes_ownership_interval_and_capacity(self):
        def check(mutation, pattern):
            row = {**plan.calibration_schedule()[0], "requests_per_s": 1.0}
            row.update(self.memory_evidence(row))
            path = self.artifacts / row["memory_receipt_file"]
            receipt = json.loads(path.read_bytes())
            samples_path = self.artifacts / receipt["samples_file"]
            samples = [json.loads(line) for line in samples_path.read_bytes().splitlines()]
            registry_path = self.artifacts / receipt["process_registry_file"]
            registry = json.loads(registry_path.read_bytes())
            mutation(row, receipt, samples, registry)
            samples_path.write_text("".join(json.dumps(sample) + "\n" for sample in samples), encoding="utf-8")
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            receipt["samples_sha256"] = hashlib.sha256(samples_path.read_bytes()).hexdigest()
            receipt["process_registry_sha256"] = hashlib.sha256(registry_path.read_bytes()).hexdigest()
            path.write_text(json.dumps(receipt), encoding="utf-8")
            row["memory_receipt_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex((ValueError, KeyError), pattern):
                admission.validate_memory(row, plan.config_sha256(plan.CANDIDATES[0]),
                                          self.source, self.runtime, self.runtime_data, self.artifacts)
        cases = [
            ("missing", lambda r, h, s, p: r.pop("memory_receipt_file"), "memory_receipt_file"),
            ("over_cap", lambda r, h, s, p: s[0].update(device_used_bytes=6501), "exceeds"),
            ("unit", lambda r, h, s, p: s[0].update(unit="MiB"), "unit"),
            ("negative", lambda r, h, s, p: s[0].update(device_used_bytes=-1), "integer"),
            ("float", lambda r, h, s, p: s[0].update(device_used_bytes=1.0), "integer"),
            ("bool", lambda r, h, s, p: s[0].update(device_used_bytes=True), "integer"),
            ("capacity", lambda r, h, s, p: s[0].update(capacity_bytes=20000), "capacity"),
            ("foreign_pid", lambda r, h, s, p: s[0]["processes"][0].update(pid=999), "PID"),
            ("foreign_uid", lambda r, h, s, p: s[0]["processes"][0].update(uid=999), "UID"),
            ("foreign_run", lambda r, h, s, p: s[0]["processes"][0].update(run_id="foreign"), "RUNID"),
            ("reused_pid", lambda r, h, s, p: s[0]["processes"][0].update(proc_start_ticks=999), "PID"),
            ("bad_interval", lambda r, h, s, p: h.update(end_monotonic=1.0), "interval"),
            ("missing_GPU", lambda r, h, s, p: s.__setitem__(slice(None), [v for v in s if v["gpu_uuid"] != "GPU-CPU-fixture-2"]), "cover"),
            ("gap", lambda r, h, s, p: s.__setitem__(slice(None), [v for v in s if v["monotonic_s"] != 1.0]), "gap"),
            ("foreign_registry", lambda r, h, s, p: p["processes"][0].update(uid=999), "registry"),
        ]
        for name, mutation, pattern in cases:
            with self.subTest(case=name):
                check(mutation, pattern)

    def test_memory_summary_or_bad_raw_hash_cannot_admit_a_candidate(self):
        rows = self.rows()
        self.select(rows)
        for row in rows:
            row.pop("memory_receipt_file")
            row["peak_memory_bytes"], row["memory_cap_bytes"] = 1, 6500
        with self.assertRaises(KeyError):
            self.select(rows)
        rows = self.rows()
        path = self.artifacts / rows[0]["memory_receipt_file"]
        receipt = json.loads(path.read_bytes())
        raw_path = self.artifacts / receipt["samples_file"]
        raw_path.write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA"):
            self.select(rows)

    def test_nonconstant_repeats_freeze_load_mean_then_geomean(self):
        rows = self.rows()
        for row in rows:
            if row["candidate"] == "replicas-p0-d0-b4":
                row["requests_per_s"] = ((100, 1, 1), (1, 100, 1))[row["repeat"]]["CDE".index(row["load"])]
            elif row["candidate"] == "replicas-p0-d0-b8":
                row["requests_per_s"] = 10.0
        for row in rows:
            row.update(self.memory_evidence(row))
        result = self.select(rows)
        expected = (50.5 * 50.5 * 1.0) ** (1 / 3)
        self.assertAlmostEqual(result["all_eligible_scores"]["replicas-p0-d0-b4"], expected)
        self.assertEqual(result["selected"]["replicas"]["candidate"], "replicas-p0-d0-b4")
        # Mean of the two per-repeat geometric means would instead be ~4.64.
        self.assertLess(100 ** (1 / 3), 10)

    def test_three_percent_tie_is_best_over_candidate_score(self):
        rows = self.rows()
        for row in rows:
            if row["candidate"] == "replicas-p0-d0-b4":
                row["requests_per_s"] = 10.0
            elif row["candidate"] == "replicas-p0-d0-b8":
                row["requests_per_s"] = 10.299
        for row in rows:
            row.update(self.memory_evidence(row))
        self.assertEqual(self.select(rows)["selected"]["replicas"]["candidate"], "replicas-p0-d0-b4")
        for row in rows:
            if row["candidate"] == "replicas-p0-d0-b8":
                row["requests_per_s"] = 10.301
        for row in rows:
            row.update(self.memory_evidence(row))
        self.assertEqual(self.select(rows)["selected"]["replicas"]["candidate"], "replicas-p0-d0-b8")

    def test_available_memory_cap_and_raw_request_interval_are_enforced(self):
        row = {**plan.calibration_schedule()[0], "requests_per_s": 1.0}
        row.update(self.memory_evidence(row))
        candidate = plan.CANDIDATES[0]
        def validate():
            return admission.validate_memory(row, plan.config_sha256(candidate), self.source,
                                             self.runtime, self.runtime_data, self.artifacts)
        self.assertEqual(set(validate()["sampled_peaks_bytes"].values()), {5000})
        uuid = next(iter(self.runtime_data["gpu_capacity_bytes"]))
        self.runtime_data["gpu_admission_free_bytes"][uuid] = 4000
        self.runtime_data["gpu_memory_cap_bytes"][uuid] = 4000
        with self.assertRaisesRegex(ValueError, "exceeds"):
            validate()
        self.runtime_data["gpu_admission_free_bytes"][uuid] = 10000
        self.runtime_data["gpu_memory_cap_bytes"][uuid] = 6500
        path = self.artifacts / row["memory_receipt_file"]
        receipt = json.loads(path.read_bytes())
        requests_path = self.artifacts / receipt["requests_file"]
        records = [json.loads(line) for line in requests_path.read_bytes().splitlines()]
        records[-1]["end_monotonic"] = row["measure_end_monotonic"] + 1.0
        requests_path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
        receipt["requests_sha256"] = hashlib.sha256(requests_path.read_bytes()).hexdigest()
        path.write_text(json.dumps(receipt), encoding="utf-8")
        row["memory_receipt_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "raw requests|raw binding"):
            validate()

    def test_only_changing_summary_rate_is_rejected_without_touching_raw(self):
        rows = self.rows()
        self.select(rows)
        tracked = {path: hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in self.artifacts.iterdir() if path.is_file()}
        rows[0]["requests_per_s"] = 1e100
        with self.assertRaisesRegex(ValueError, "Summary requests_per_s"):
            self.select(rows)
        self.assertTrue(all(hashlib.sha256(path.read_bytes()).hexdigest() == digest
                            for path, digest in tracked.items()))

    def test_rate_uses_outer_client_window_instead_of_min_submit_span(self):
        row = {**plan.calibration_schedule()[0], "requests_per_s": 1.0}
        row.update(self.memory_evidence(row))
        config_sha = plan.config_sha256(plan.CANDIDATES[0])
        evidence = admission.validate_memory(row, config_sha, self.source, self.runtime,
                                             self.runtime_data, self.artifacts)
        self.assertEqual(evidence["requests_per_s"], 1.0)
        receipt = json.loads((self.artifacts / row["memory_receipt_file"]).read_bytes())
        records = [json.loads(line) for line in (self.artifacts / receipt["requests_file"]).read_bytes().splitlines()]
        measured = [record for record in records if not record["warmup"]]
        row["requests_per_s"] = 16 / (max(record["end_monotonic"] for record in measured)
                                      - min(record["submit_monotonic"] for record in measured))
        self.assertNotEqual(row["requests_per_s"], evidence["requests_per_s"])
        with self.assertRaisesRegex(ValueError, "outer-window"):
            admission.validate_memory(row, config_sha, self.source, self.runtime,
                                      self.runtime_data, self.artifacts)

    def test_actual_client_window_writer_roundtrips_through_consumer(self):
        row = {**plan.calibration_schedule()[0], "requests_per_s": 1.0}
        row.update(self.memory_evidence(row))
        path = self.artifacts / row["memory_receipt_file"]
        receipt = json.loads(path.read_bytes())
        (self.artifacts / "requests.jsonl").write_bytes((self.artifacts / receipt["requests_file"]).read_bytes())
        metadata = {key: receipt[key] for key in ("candidate", "repeat", "load", "run_id", "uid", "host", "boot_id",
                    "candidate_config_sha256", "source_manifest_sha256", "runtime_binding_sha256")}
        emitted = client_window.write_window(self.artifacts, metadata, 0.0, 1.0, 1.0, 17.0)
        receipt["client_window_file"] = "client-window.json"
        receipt["client_window_sha256"] = hashlib.sha256((self.artifacts / "client-window.json").read_bytes()).hexdigest()
        path.write_text(json.dumps(receipt), encoding="utf-8")
        row["memory_receipt_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        result = admission.validate_memory(row, plan.config_sha256(plan.CANDIDATES[0]),
                                           self.source, self.runtime, self.runtime_data, self.artifacts)
        self.assertEqual(result["requests_per_s"], 16 / 16)
        self.assertEqual(emitted["clock"], "time.perf_counter")
        with self.assertRaises(FileExistsError):
            client_window.write_window(self.artifacts, metadata, 0.0, 1.0, 1.0, 17.0)

    def test_calibration_client_metadata_rejects_wrong_budget_or_identity(self):
        row = {**plan.calibration_schedule()[0], "requests_per_s": 1.0}
        row.update(self.memory_evidence(row))
        receipt = json.loads((self.artifacts / row["memory_receipt_file"]).read_bytes())
        metadata = {key: receipt[key] for key in ("candidate", "repeat", "load", "run_id", "uid", "host", "boot_id",
                    "candidate_config_sha256", "source_manifest_sha256", "runtime_binding_sha256")}
        path = self.artifacts / "client-metadata.json"
        path.write_text(json.dumps(metadata), encoding="utf-8")
        args = NS(calibration_metadata=path, warmup=4, requests=16, repetitions=1,
                  images=1, tokens=128, concurrency=8)
        with patch.object(client_window.os, "getuid", return_value=2147, create=True), \
             patch.object(client_window.socket, "gethostname", return_value=metadata["host"]), \
             patch.object(Path, "read_text", return_value=metadata["boot_id"]):
            self.assertEqual(client_window.load_metadata(args)["candidate"], metadata["candidate"])
            args.requests = 17
            with self.assertRaisesRegex(ValueError, "4 warmup and 16"):
                client_window.load_metadata(args)
            args.requests = 16
            metadata["uid"] = 999
            path.write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "UID/host/boot"):
                client_window.load_metadata(args)

    def test_window_clock_identity_and_measurement_count_cannot_be_changed(self):
        for field, value in (("clock", "different-clock"), ("host", "foreign"),
                             ("measured_requests", 15), ("measurement_start_monotonic", .5)):
            with self.subTest(field=field):
                row = {**plan.calibration_schedule()[0], "requests_per_s": 1.0}
                row.update(self.memory_evidence(row))
                path = self.artifacts / row["memory_receipt_file"]
                receipt = json.loads(path.read_bytes())
                window_path = self.artifacts / receipt["client_window_file"]
                window = json.loads(window_path.read_bytes())
                window[field] = value
                window_path.write_text(json.dumps(window), encoding="utf-8")
                receipt["client_window_sha256"] = hashlib.sha256(window_path.read_bytes()).hexdigest()
                path.write_text(json.dumps(receipt), encoding="utf-8")
                row["memory_receipt_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaises(ValueError):
                    admission.validate_memory(row, plan.config_sha256(plan.CANDIDATES[0]),
                                              self.source, self.runtime, self.runtime_data, self.artifacts)

    def rows(self):
        return [{**row, **self.memory_evidence(row), "status": "ok", "failures": 0,
                 "qualification_receipt_sha256": self.qualifications()[row["candidate"]]["receipt_sha256"],
                 "candidate_config_sha256": self.qualifications()[row["candidate"]]["candidate_config_sha256"],
                 "source_manifest_sha256": self.source, "runtime_binding_sha256": self.runtime,
                 "warmup_completed": 4, "requests_completed": 16,
                 "fixed_output_length": True, "requests_per_s": 1.0}
                for row in plan.calibration_schedule()]

    def test_counts_and_balanced_order(self):
        calibration = plan.calibration_schedule()
        self.assertEqual(len(calibration), 48)
        self.assertEqual(sum(row["warmup"] + row["requests"] for row in calibration), 960)
        for full, count, requests in ((False, 54, 2700), (True, 90, 9000)):
            formal = plan.formal_schedule(full)
            self.assertEqual(len(formal), count)
            self.assertEqual(sum(row["requests"] for row in formal), requests)
            orders = [[next(row["system"] for row in formal if row["block"] == block and row["system"] == system)
                       for system in dict.fromkeys(row["system"] for row in formal if row["block"] == block)]
                      for block in range(6)]
            self.assertEqual(len({tuple(order) for order in orders}), 6)
            for position in range(3):
                self.assertEqual([sum(order[position] == system for order in orders) for system in plan.SYSTEMS], [2, 2, 2])

    def test_ties_prefer_small_profile_and_p1d2(self):
        selected = self.select(self.rows())["selected"]
        self.assertEqual(selected["pd"]["candidate"], "pd-p1-d2-b4")
        self.assertEqual(selected["replicas"]["candidate"], "replicas-p0-d0-b4")

    def test_failures_not_dropped_and_missing_cells_rejected(self):
        rows = self.rows()
        with self.assertRaises(ValueError):
            self.select(rows[:-1])
        with self.assertRaises(ValueError):
            self.select(rows + [rows[0]])
        for row in rows:
            if row["candidate"].startswith("pd-"):
                row["status"] = "failed"
        with self.assertRaisesRegex(ValueError, "No valid pd"):
            self.select(rows)


if __name__ == "__main__":
    unittest.main(verbosity=2)
