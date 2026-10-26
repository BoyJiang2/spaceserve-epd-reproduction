"""Read-only process/resource inventory; preserve all partial C files, no cleanup."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import psutil

root = Path('/var/tmp/boyjiang-epd-revision-20261026')
owned = []
for process in psutil.process_iter():
    try:
        if process.pid == os.getpid() or process.uids().real != os.getuid():
            continue
        command = process.cmdline()
        if str(root) in ' '.join(command):
            owned.append({'pid': process.pid, 'created': process.create_time(), 'command': command})
    except psutil.NoSuchProcess:
        continue
    except psutil.AccessDenied:
        owned.append({'pid': process.pid, 'identity_unconfirmed': True})
files = []
for path in sorted((root / 'results/performance').rglob('*')):
    if path.is_file():
        files.append({'path': path.relative_to(root).as_posix(),
                      'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
state = {'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
         'owned_root_processes': owned, 'files': files,
         'gpus': subprocess.check_output(['nvidia-smi', '--id=4,5,6', '--query-gpu=index,uuid,memory.used,utilization.gpu', '--format=csv,noheader,nounits'], text=True, timeout=15),
         'compute': subprocess.check_output(['nvidia-smi', '--id=4,5,6', '--query-compute-apps=pid,gpu_uuid,used_memory', '--format=csv,noheader,nounits'], text=True, timeout=15),
         'controller_exit_code': None,
         'observation': 'Remote controller absent; local session observation has not returned an exit. No automatic restart.',
         'completed': [p.parent.name for p in sorted((root / 'results/performance').glob('*/COMPLETED'))]}
destination = root / 'evidence/C-interruption-20261027-0018.json'
with destination.open('x') as output:
    json.dump(state, output, indent=2)
print(json.dumps({'completed_cells': len(state['completed']), 'frozen_files': len(files),
                  'owned_root_processes': owned, 'selected_gpu_compute': state['compute']}))
