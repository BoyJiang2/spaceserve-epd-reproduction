"""Repair the observed multi-image cache overwrite and encoder state leaks."""
import ast
import difflib
import json
import pathlib
import sys
import typing
from types import SimpleNamespace


root = pathlib.Path(sys.argv[1]).resolve()
source = root / "src/SpaceServe"
patches = root / "results/patches"
patches.mkdir(parents=True, exist_ok=True)

runner = source / "vllm/v1/worker/gpu_model_runner.py"
text = runner.read_text()
old = "for (req_id, input_id), output in zip(req_input_ids, encoder_outputs):\n            if req_id not in self.encoder_cache:"
new = "for (req_id, input_id), output in zip(req_input_ids, encoder_outputs):\n            if req_id not in encoder_cache:"


def cache_regression(text):
    tree = ast.parse(text)
    loop = next(node for node in ast.walk(tree) if isinstance(node, ast.For)
                and ast.unparse(node.iter) == "zip(req_input_ids, encoder_outputs)")
    module = ast.fix_missing_locations(ast.Module(body=[loop], type_ignores=[]))
    state = {"self": SimpleNamespace(encoder_cache={}),
             "encoder_cache": {}, "req_input_ids": [("a", i) for i in range(4)],
             "encoder_outputs": ["red", "green", "blue", "yellow"]}
    exec(compile(module, "actual-cache-loop", "exec"), state)
    return state["encoder_cache"]


broken_text = text.replace(new, old, 1)
fixed_text = broken_text.replace(old, new, 1)
assert cache_regression(broken_text) == {"a": {3: "yellow"}}
assert cache_regression(fixed_text) == {"a": dict(enumerate(["red", "green", "blue", "yellow"]))}
(patches / "space-cache-regression.json").write_text(json.dumps({"before": cache_regression(broken_text),
                                                                "after": cache_regression(fixed_text)}))


def release_regression(text):
    definition = next(node for node in ast.parse(text).body if isinstance(node, ast.ClassDef) and node.name == "EncoderCacheManager")
    state = {**vars(typing), "Request": object}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[definition], type_ignores=[])), "actual-cache-manager", "exec"), state)
    manager = state["EncoderCacheManager"](4096)
    for number in range(50):
        request = SimpleNamespace(request_id=str(number), get_num_encoder_tokens=lambda _: 256)
        for image in range(4):
            manager.allocate(request, image)
        manager.free(request)
        assert manager.num_free_slots == 4096 and not manager.cached
    return {"requests_released": 50, "free_slots": manager.num_free_slots}
changes = [
    (runner, old, new),
    (source / "vllm/v1/worker/gpu_worker.py", "                with_stack=True,", "                with_stack=False,"),
    (source / "vllm/v1/core/encoder_cache_manager.py",
     "        for input_id in input_ids:\n            self.free_encoder_input(request, input_id)",
     "        for input_id in list(input_ids):\n            self.free_encoder_input(request, input_id)"),
    (source / "vllm/v1/engine/core_client.py",
     "                        make_zmq_socket)",
     "                        make_zmq_socket, get_mp_context)"),
    (source / "vllm/v1/engine/core_client.py",
     "        encoder_result_queue = mp.Queue(maxsize=5)",
     "        self.encoder_result_queue = get_mp_context().Queue(maxsize=5)\n"
     "        encoder_result_queue = self.encoder_result_queue"),
    (source / "vllm/v1/engine/core_client.py",
     "    async def profile_async(self, is_start: bool = True) -> None:\n        await self._send_input(EngineCoreRequestType.PROFILE,",
     "    async def profile_async(self, is_start: bool = True) -> None:\n"
     "        await self._send_input_toencoder(EngineCoreRequestType.PROFILE,\n"
     "                                         EngineCoreProfile(is_start))\n"
     "        await self._send_input(EngineCoreRequestType.PROFILE,"),
    (source / "vllm/v1/engine/core.py",
     "                self.encoder_result_queue.put(output)",
     "                self.encoder_result_queue.put(output)\n"
     "                self.scheduler.finish_requests(\n"
     "                    [req.req_id for req in scheduler_output.scheduled_new_reqs],\n"
     "                    RequestStatus.FINISHED_STOPPED)\n"
     "                self.scheduler.finished_req_ids.clear()\n"
     "                self.scheduler.encoder_cache_manager.get_freed_ids()"),
    (source / "vllm/v1/worker/gpu_worker.py",
     "        encoder_cache = self.model_runner._execute_encoder(scheduler_output)",
     "        encoder_cache = self.model_runner._execute_encoder(scheduler_output)\n"
     "        for req_id in scheduler_output.scheduled_encoder_inputs:\n"
     "            self.model_runner.requests.pop(req_id, None)"),
]
for path, old_text, new_text in changes:
    before = path.read_text()
    if new_text in before:
        continue
    assert old_text in before, str(path)
    after = before.replace(old_text, new_text, 1)
    ast.parse(after)
    path.write_text(after)
    relative = path.relative_to(source).as_posix()
    (patches / (path.stem + "-space.patch")).write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile="a/" + relative, tofile="b/" + relative)))
print("multi-image cache regression passed; completed encoder requests are released")
release = release_regression((source / "vllm/v1/core/encoder_cache_manager.py").read_text())
(patches / "space-cache-release-regression.json").write_text(json.dumps(release))
print(json.dumps(release))
