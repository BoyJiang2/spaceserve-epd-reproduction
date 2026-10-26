"""Reuse the matching vLLM 0.7.2 wheel's native extensions in the source fork."""
import importlib.metadata
import difflib
import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1]).resolve()
source = root / "src/SpaceServe"
distribution = importlib.metadata.distribution("vllm")
assert distribution.version == "0.7.2", distribution.version
wheel = pathlib.Path(distribution.locate_file("vllm")).resolve()
patches = root / "results/patches"
patches.mkdir(parents=True, exist_ok=True)
old = "        physical_device_id = device_ids[device_id]\n        return int(physical_device_id)"
new = ("        physical_device_id = device_ids[device_id]\n"
       "        if physical_device_id.startswith(\"GPU-\"):\n"
       "            pynvml.nvmlInit()\n"
       "            try:\n"
       "                return pynvml.nvmlDeviceGetIndex(\n"
       "                    pynvml.nvmlDeviceGetHandleByUUID(physical_device_id))\n"
       "            finally:\n"
       "                pynvml.nvmlShutdown()\n"
       "        return int(physical_device_id)")
for label, path in (("baseline", wheel / "platforms/cuda.py"), ("fork", source / "vllm/platforms/cuda.py")):
    before = path.read_text()
    if new in before:
        continue
    assert before.count(old) == 1, path
    after = before.replace(old, new)
    path.write_text(after)
    (patches / (label + "-cuda-uuid.patch")).write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile="a/vllm/platforms/cuda.py", tofile="b/vllm/platforms/cuda.py")))
links = []
originals = list(wheel.rglob("*.so")) + [wheel / "_version.py"]
originals += [path for path in (wheel / "vllm_flash_attn").rglob("*") if path.is_file()]
for original in originals:
    if not original.exists():
        continue
    target = source / "vllm" / original.relative_to(wheel)
    if target.exists():
        continue
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(original)
    links.append({"target": str(target), "original": str(original)})
(root / "results/space-native-extensions.json").write_text(json.dumps(links, indent=2))
print(json.dumps(links, indent=2))
