import json
import os
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
environment = dict(os.environ, EXP_ROOT=str(root))
result = subprocess.run(["bash", str(root / "scripts/start_server.sh"), "epd", "0,1,2", "18400"],
                        env=environment, capture_output=True, text=True, timeout=30)
apps = subprocess.check_output(["nvidia-smi", "--id=0,1,2", "--query-compute-apps=pid", "--format=csv,noheader"], text=True).strip()
assert result.returncode == 1 and "does not support bare-metal" in result.stderr and not apps
(root / "results/iommu-start-guard-test.json").write_text(json.dumps({"passed": True, "exit_code": result.returncode,
    "stdout": result.stdout, "stderr": result.stderr, "gpu_processes_after": apps}, indent=2))
print("Unsupported DMA IOMMU rejected before model/Ray startup; no GPU processes created")
