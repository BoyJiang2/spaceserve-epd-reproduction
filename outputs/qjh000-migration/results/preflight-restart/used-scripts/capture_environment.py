import datetime
import importlib.metadata
import json
import pathlib
import platform
import subprocess
import sys


root = pathlib.Path(sys.argv[1]).resolve()
commands = {
    "gpus": ["nvidia-smi", "--query-gpu=index,uuid,name,memory.total,driver_version,pci.bus_id", "--format=csv"],
    "topology": ["nvidia-smi", "topo", "-m"],
    "p2p_read": ["nvidia-smi", "topo", "-p2p", "r"],
    "cpu": ["lscpu"], "storage": ["df", "-h", str(root)],
    "cuda_toolkit": ["/usr/local/cuda/bin/nvcc", "--version"],
}
result = {"captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "hostname": platform.node(), "kernel": platform.release(), "python": platform.python_version(),
          "packages": {name: importlib.metadata.version(name) for name in ["vllm", "torch", "transformers"]}}
for label, command in commands.items():
    completed = subprocess.run(command, capture_output=True, text=True, timeout=20)
    result[label] = {"command": command, "exit_code": completed.returncode,
                     "stdout": completed.stdout, "stderr": completed.stderr}
for repository in ("SpaceServe", "epdserve", "mysmctrl"):
    path = root / "src" / repository
    if (path / ".git").exists():
        result[repository + "_commit"] = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
(root / "results/environment.json").write_text(json.dumps(result, indent=2))
print(json.dumps({key: value for key, value in result.items() if key.endswith("_commit") or key in ("hostname", "packages")}, indent=2))
