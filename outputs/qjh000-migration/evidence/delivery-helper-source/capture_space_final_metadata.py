"""CPU/read-only system checks after the formal supervisor exits successfully."""
if not __debug__:
    raise RuntimeError('verification requires Python without -O')

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

import psutil

root = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
assert socket.gethostname() == 'qjh000' and os.getuid() == 2147
assert (root / 'results/formal/COMPLETED').is_file()
terminal = json.loads((root / 'logs/formal-launch.log').read_text().splitlines()[-1])
assert terminal == {'state': 'finished', 'child_exit': 0}
try:
    process = psutil.Process(124199)
    if str(root / 'scripts/gpu_exclusive.py') in process.cmdline():
        raise RuntimeError('formal supervisor still live; do not collect final evidence yet')
except psutil.NoSuchProcess:
    pass
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == (root / 'evidence/boot-id.txt').read_text().strip()
environment = dict(os.environ, EXP_ROOT=str(root))
with (root / 'evidence/formal-final-background-check.txt').open('x') as output:
    subprocess.run([str(root / 'envs/manage/bin/python'), str(root / 'scripts/check_background.py')], env=environment, check=True, text=True, stdout=output)
with (root / 'evidence/formal-final-target-gpu-processes.csv').open('x') as output:
    subprocess.run(['nvidia-smi', '--id=0', '--query-compute-apps=pid,process_name,gpu_uuid,used_gpu_memory', '--format=csv'], check=True, text=True, stdout=output)
sources = {}
for repository, expected in [('SpaceServe', '66de079af4234b27f7f82ff91d238ef1351324ba'), ('mysmctrl', '6ff57356968a3f04158b9273aa881ee6bdf04229')]:
    actual = subprocess.check_output(['git', '-C', str(root / 'src' / repository), 'rev-parse', 'HEAD'], text=True).strip()
    assert actual == expected
    sources[repository] = actual
diff = subprocess.check_output(['git', '-C', str(root / 'src/SpaceServe'), '-c', 'color.ui=never', 'diff', '--no-ext-diff', '--binary', 'HEAD'])
with (root / 'evidence/formal-final-SpaceServe.diff').open('xb') as output:
    output.write(diff)
record = {'passed': True, 'host': socket.gethostname(), 'boot_id': boot, 'sources': sources, 'supervisor_terminal': terminal, 'spaceserve_diff_sha256': hashlib.sha256(diff).hexdigest(), 'scope': 'after all formal measurements;no GPU experiment;no process stopped'}
with (root / 'evidence/formal-final-source-revisions.json').open('x') as output:
    json.dump(record, output, indent=2)
print(json.dumps(record))
