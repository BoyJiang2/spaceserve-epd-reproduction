"""Check fixed-package FP16 CUDA execution before loading the 7B model."""
import ctypes
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
from runtime_config import context
CONFIG = context()
CONFIG.require_scope('numeric')
import torch

root = Path(os.environ['EXP_ROOT']).resolve()
if str(root) != str(CONFIG.run_root) or os.uname().nodename != CONFIG.config['host'] or os.environ.get('REPRO_HOST_LOCK_HELD') != '1' or not (root / 'evidence/G2_CODE_APPROVED.json').exists():
    raise RuntimeError('runtime probe requires configured owned host lock and G2')
if os.environ.get('CUDA_MPS_PIPE_DIRECTORY'):
    raise RuntimeError('initial runtime probe requires clean non-MPS environment')
packages = {key: importlib.metadata.version(key) for key in ['torch', 'vllm', 'transformers']}
if packages != {'torch': '2.5.1', 'vllm': '0.7.2', 'transformers': '4.49.0'}:
    raise RuntimeError('fixed runtime differs')
if subprocess.check_output(['nvidia-smi', '--id='+str(CONFIG.gpu_devices[0]), '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip():
    raise RuntimeError('configured GPU is occupied')
selected = subprocess.check_output(['nvidia-smi', '--id='+str(CONFIG.gpu_devices[0]), '--query-gpu=uuid', '--format=csv,noheader'], text=True).strip()
if os.environ.get('CUDA_VISIBLE_DEVICES') != selected:
    raise RuntimeError('probe GPU UUID differs')
torch.cuda.set_device(0)
torch.manual_seed(17)
left = torch.randn(256, 256, dtype=torch.float16, device='cuda')
right = torch.randn(256, 256, dtype=torch.float16, device='cuda')
actual = left @ right
torch.cuda.synchronize()
reference = left.cpu().float() @ right.cpu().float()
if not torch.isfinite(actual).all() or not torch.allclose(actual.cpu().float(), reference, atol=.04, rtol=.01):
    raise RuntimeError('FP16 matmul sanity check failed')
driver = ctypes.CDLL('libcuda.so.1')
version = ctypes.c_int()
if driver.cuDriverGetVersion(ctypes.byref(version)) != 0:
    raise RuntimeError('Driver API query failed')
record = {'host': os.uname().nodename, 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'packages': packages, 'torch_cuda': torch.version.cuda, 'driver_api': version.value,
          'gpu_uuid': selected, 'device': torch.cuda.get_device_name(0), 'pid': os.getpid(),
          'fp16_matmul_passed': True, 'max_abs_error': (actual.cpu().float() - reference).abs().max().item(),
          'scope': 'runtime sanity only; not model or SM mechanism acceptance'}
(root / 'evidence/runtime-probe.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record), flush=True)
