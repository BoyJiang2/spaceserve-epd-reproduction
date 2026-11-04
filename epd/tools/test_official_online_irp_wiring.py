"""CPU regression for real online flag propagation; GPU dependencies are replaced."""
import ast
import asyncio
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import time

ROOT = Path("/local/boyjiang/epdserve-official")
BUILD = Path("/local/boyjiang/epd/assets/build")

def compile_nodes(nodes, namespace):
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    tree = ast.fix_missing_locations(ast.Module(body=[future] + nodes, type_ignores=[]))
    exec(compile(tree, "<exact-source-CPU-unit>", "exec"), namespace)

factory_tree = ast.parse((ROOT / "epdserve/request.py").read_text())
factory = next(n for n in factory_tree.body if isinstance(n, ast.FunctionDef) and n.name == "create_request")

def run_case(source, cli=None, override=None, direct=False, direct_flag=None):
    captured = []
    class FakeEngineArgs:
        def __init__(self, **kwargs):
            pass
        def create_engine_config(self):
            return SimpleNamespace()
    namespace = {"Request": SimpleNamespace}
    compile_nodes([copy.deepcopy(factory)], namespace)
    class FakeOrchestrator:
        def __init__(self, *args, **kwargs):
            pass
        async def initialize(self):
            pass
        async def generate(self, input, sampling_params, request_id, arrival_time, **kwargs):
            request = namespace["create_request"](input, sampling_params, request_id, arrival_time, **kwargs)
            captured.append(request.enable_irp)
            yield SimpleNamespace()
    namespace.update(asyncio=asyncio, time=time, EngineArgs=FakeEngineArgs,
                     Counter=lambda: iter(range(10)), SamplingParams=lambda: None,
                     EPDOrchestrator=FakeOrchestrator)
    for name in ["ModelConfig", "ClusterParallelConfig", "DisaggParallelConfig", "CacheConfig",
                 "EncodingStageSchedConfig", "ContextStageSchedConfig", "DecodingStageSchedConfig"]:
        namespace[name] = SimpleNamespace
    original = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == "AsyncLLM")
    methods = [copy.deepcopy(n) for n in original.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name in ["__init__", "generate", "from_engine_args"]]
    node = ast.ClassDef(name="AsyncLLM", bases=[], keywords=[], body=methods, decorator_list=[])
    compile_nodes([node], namespace)
    cls = namespace["AsyncLLM"]
    if direct:
        options = {} if direct_flag is None else {"enable_irp": direct_flag}
        engine = cls(None, None, None, None, None, None, **options)
    else:
        method = next(n for n in methods if n.name == "from_engine_args")
        keys = {n.attr for n in ast.walk(method)
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "args"}
        args = SimpleNamespace(**{name: 1 for name in keys})
        args.model = "MiniCPM-V-2_6"
        args.intra_request_dp = cli
        engine = cls.from_engine_args(args)
    async def consume():
        options = {} if override is None else {"enable_irp": override}
        async for _ in engine.generate(
            request_id=7, input_dict={"prompt": "CPU fixture", "prompt_token_ids": [1],
                                     "multi_modal_data": {"image": ["A", "B", "C", "D"]}},
            arrival_time=1.0, **options):
            pass
    asyncio.run(consume())
    assert len(captured) == 1
    return captured[0]

old = subprocess.check_output(["git", "show", "9b111f710dfb4724072b603d626a1e4dad93ef1f:epdserve/llm_async.py"],
                              cwd=ROOT, text=True)
new = (ROOT / "epdserve/llm_async.py").read_text()
old_disabled = run_case(old, cli=0)
assert old_disabled is True  # Reproduces the violation: CLI zero did not disable Request IRP.
cases = []
for cli, override, expected in [(0, None, False), (1, None, True), (0, True, True), (1, False, False)]:
    actual = run_case(new, cli=cli, override=override)
    assert actual is expected
    cases.append({"cli": cli, "explicit_override": override, "effective_request_enable_irp": actual})
assert run_case(new, direct=True) is True
assert run_case(new, direct=True, direct_flag=False) is False

encoding = (ROOT / "epdserve/engine_encoding.py").read_text()
cluster = next(n for n in ast.parse(encoding).body if isinstance(n, ast.ClassDef) and n.name == "EncodingStageCluster")
shard = next(n for n in cluster.body if isinstance(n, ast.FunctionDef) and n.name == "shard_requests")
space = {"copy": copy}
compile_nodes([copy.deepcopy(shard)], space)
shared_images = {"image": ["A", "B", "C", "D"]}
request = SimpleNamespace(request_id=7, is_sharded=False, multi_modal_data=shared_images,
                          vllm_seq_metadata=SimpleNamespace(multi_modal_data={"image": shared_images}))
shards = space["shard_requests"](None, request)
observed = [part.multi_modal_data["image"] for part in shards]
assert observed == [["D"], ["D"], ["D"], ["D"]]
assert request.multi_modal_data["image"] == ["D"]

record = {"CPU_only": True, "target_packages_imported": False, "GPU_executed": False,
          "old_cli_zero_effective_request_enable_irp": old_disabled,
          "new_flag_cases": cases, "direct_constructor_old_default_preserved": True,
          "existing_enabled_shard_alias_bug": observed, "enabled_shard_path_fixed": False,
          "limitations": "Exact real methods/factory; model/configuration/Orchestrator work replaced. Not inference or full-config validation.",
          "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                            for p in ["epdserve/llm_async.py", "epdserve/orchestrator.py", "epdserve/request.py",
                                      "epdserve/engine_encoding.py", "epdserve/worker.py"]}}
result_path = BUILD / ("official-online-irp-cpu-result-" + str(time.time_ns()) + ".json")
with result_path.open("x") as stream:
    stream.write(json.dumps(record, indent=2))
print(json.dumps(record), flush=True)
