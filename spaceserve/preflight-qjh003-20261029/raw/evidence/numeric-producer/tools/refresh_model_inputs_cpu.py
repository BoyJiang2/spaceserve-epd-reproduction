"""One approved CPU-only refresh; preserve the previous receipt before rechecking."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from runtime_config import context
CONFIG = context()

root=Path(str(CONFIG.run_root))
if socket.gethostname()!=CONFIG.config['host'] or os.getuid()!=2147:
    raise RuntimeError('wrong host/UID')
source=root/'evidence/MODEL_INPUTS_VERIFIED-attempt1.json'
destination=root/'evidence/MODEL_INPUTS_VERIFIED-first-CPU.json'
if source.is_symlink() or not source.is_file() or destination.exists() or destination.is_symlink():
    raise RuntimeError('refuse receipt overwrite or nonregular source')
before=hashlib.sha256(source.read_bytes()).hexdigest()
source.rename(destination)
if hashlib.sha256(destination.read_bytes()).hexdigest()!=before:
    raise RuntimeError('preserved receipt differs')
print(json.dumps({'preserved':str(destination),'sha256':before}),flush=True)
with (root/'evidence/model-inputs-extension-refresh.log').open('x') as log:
    result=subprocess.run([str(CONFIG.asset('envs/space/bin/python')),'-B',str(root/'scripts/verify_model_inputs.py')],
                          stdout=log,stderr=subprocess.STDOUT)
print(json.dumps({'exit_code':result.returncode,'new_model_requests':0}),flush=True)
raise SystemExit(result.returncode)
