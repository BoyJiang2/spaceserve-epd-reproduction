"""Apply only documented setup fixes and the verified multi-image routing fix."""
import ast
import difflib
import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1]).resolve()
patches = root / "results/patches"
patches.mkdir(parents=True, exist_ok=True)
server = root / "src/epdserve/epdserve/api_server.py"
before = server.read_text()
old = 'mm_data["image"] = [load_image_cache(ps[0])] * len(ps)'
new = 'mm_data["image"] = [load_image_cache(path) for path in ps]'


def exercise_assignment(text):
    tree = ast.parse(text)
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and ast.unparse(node.targets[0]) == "mm_data['image']"]
    assert len(assignments) == 1
    module = ast.fix_missing_locations(ast.Module(body=assignments, type_ignores=[]))
    state = {"mm_data": {}, "ps": ["red", "blue"], "load_image_cache": lambda path: path}
    exec(compile(module, "image-routing", "exec"), state)
    return state["mm_data"]["image"]


if old in before:
    result = exercise_assignment(before)
    assert result == ["red", "red"], result
    (patches / "multi-image-before.json").write_text(json.dumps({"expected": ["red", "blue"], "actual": result, "passed": False}))
    after = before.replace(old, new, 1)
    assert exercise_assignment(after) == ["red", "blue"]
    server.write_text(after)
    (patches / "epd-multi-image.patch").write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile="a/epdserve/api_server.py", tofile="b/epdserve/api_server.py")))
else:
    assert new in before
    assert exercise_assignment(before) == ["red", "blue"]
(patches / "multi-image-after.json").write_text(json.dumps({"expected": ["red", "blue"], "actual": ["red", "blue"], "passed": True}))

processor = root / "envs/epd/lib/python3.10/site-packages/vllm/transformers_utils/image_processor.py"
before = processor.read_text()
definition = "def get_image_processor("
position = before.index(definition)
prefix, suffix = before[:position], before[position:]
after = prefix + suffix.replace("trust_remote_code: bool = False,", "trust_remote_code: bool = True,", 1)
if after != before:
    processor.write_text(after)
    (patches / "vllm-image-processor-trust.patch").write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile="a/vllm/transformers_utils/image_processor.py", tofile="b/vllm/transformers_utils/image_processor.py")))
print("multi-image regression reproduced and fixed; documented image-processor setup applied")

for relative, old_text, new_text in [
    ("epdserve/api_server.py", "arrival_time=arrival_time)",
     "arrival_time=arrival_time,\n                                        enable_irp=bool(args.intra_request_dp))"),
    ("epdserve/llm_async.py", "arrival_time=arrival_time if arrival_time is not None else time.perf_counter(),\n        )",
     "arrival_time=arrival_time if arrival_time is not None else time.perf_counter(),\n                            **kwargs,\n        )"),
    ("epdserve/api_server.py", "        'prompt_token_len': len(input_dict['prompt_token_ids']),",
     "        'output_token_ids': [step_output[0].new_token_id for step_output in final_outputs],\n"
     "        'processed_prompt_token_ids': input_dict['processed_prompt_token_ids'],\n"
     "        'prompt_token_len': len(input_dict['prompt_token_ids']),"),
]:
    path = root / "src/epdserve" / relative
    before = path.read_text()
    if new_text in before:
        continue
    assert before.count(old_text) == 1, relative
    after = before.replace(old_text, new_text, 1)
    ast.parse(after)
    path.write_text(after)
    (patches / (path.stem + "-" + str(len(old_text)) + "-compat.patch")).write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile="a/" + relative, tofile="b/" + relative)))
print("IRP command-line setting is forwarded to request creation")

before = server.read_text()
rgb_fix = '''from rgb_cache import cache_snapshot, dataset_paths

rgb_manifest = os.environ.get('REPRO_RGB_MANIFEST')
if rgb_manifest:
    for rgb_path in dataset_paths(rgb_manifest):
        load_image_cache(str(rgb_path))

@app.get('/repro/rgb-cache')
async def rgb_cache():
    assert rgb_manifest, 'RGB preload is not enabled'
    return cache_snapshot(rgb_manifest, image_cache)

'''
if rgb_fix not in before:
    anchor = '@app.post("/generate")'
    assert before.count(anchor) == 1
    after = before.replace(anchor, rgb_fix + anchor, 1)
    ast.parse(after)
    server.write_text(after)
    (patches / 'epd-rgb-cache.patch').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile='a/epdserve/api_server.py', tofile='b/epdserve/api_server.py')))
print('RGB-only preload and cache evidence route installed; no inference is performed')
