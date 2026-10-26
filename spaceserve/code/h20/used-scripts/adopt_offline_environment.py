"""Use a proven complete offline cache; stop only the identified CPU installer."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import psutil

root = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
if os.uname().nodename != 'qjh000' or not (root / 'evidence/sapphire-cache-READY').exists():
    raise RuntimeError('complete isolated source cache required')
if (root / 'evidence/environment-READY').exists():
    raise RuntimeError('original preparer finished; preserve and validate it instead')
freeze = root / 'configs/space-freeze.txt'
if hashlib.sha256(freeze.read_bytes()).hexdigest() != '12cc7ae16e15cb32a58d197b10c139df7d715a8c3eeb4246b77eebe5d4814b0f':
    raise RuntimeError('dependency pin differs')
environment = dict(os.environ, UV_CACHE_DIR=str(root / 'cache-sapphire/cache/uv'), TMPDIR=str(root / 'tmp'), UV_PYTHON_DOWNLOADS='never')
tool = str(root / 'envs/uv-sapphire')
check_env = root / 'envs/offline-check'
subprocess.run([tool, 'venv', '--allow-existing', '--python', '/usr/bin/python3', str(check_env)], env=environment, check=True)
# Every freeze entry is exact; avoid needing old registry resolution metadata.
# pip check after installation still requires the complete dependency closure.
command = [tool, 'pip', 'install', '--offline', '--no-deps', '--dry-run', '--python', str(check_env / 'bin/python'),
           '--index-url', 'https://pypi.tuna.tsinghua.edu.cn/simple', '-r', str(freeze)]
with (root / 'logs/offline-cache-adoption-check.log').open('x') as output:
    checked = subprocess.run(command, env=environment, stdout=output, stderr=subprocess.STDOUT)
if checked.returncode:
    raise RuntimeError('complete fixed freeze unavailable offline; original installer left running')
state = {'offline_dry_run_exit': 0, 'command': command, 'fixed_freeze_sha256': hashlib.sha256(freeze.read_bytes()).hexdigest(), 'stopped': []}
parent = psutil.Process(3361334)
installer = psutil.Process(3363327)
if parent.uids().real != os.getuid() or parent.cmdline() != ['bash', str(root / 'scripts/prepare_environment.sh')] or installer.uids().real != os.getuid() or installer.ppid() != parent.pid or installer.cmdline()[0] != str(root / 'envs/uv') or str(freeze) not in installer.cmdline():
    raise RuntimeError('recorded CPU installer identity changed; refuse stop')
children = parent.children(recursive=True)
if {item.pid for item in children} != {installer.pid}:
    raise RuntimeError('unexpected installer descendants; preserve for inspection')
if (root / 'evidence/environment-READY').exists():
    raise RuntimeError('environment became ready; no stop needed')
for process in [parent, installer]:
    state['stopped'].append({'pid': process.pid, 'create_time': process.create_time(), 'command': process.cmdline()})
(root / 'evidence/offline-adoption.json').write_text(json.dumps(state, indent=2))
parent.terminate()
installer.terminate()
_, alive = psutil.wait_procs([parent, installer], timeout=30)
if any(item.is_running() and item.status() != psutil.STATUS_ZOMBIE for item in alive):
    raise RuntimeError('owned installer has not stopped; do not start replacement')
state['owned_cpu_installer_stopped'] = True
(root / 'evidence/offline-adoption.json').write_text(json.dumps(state, indent=2))
for name in ['prepare-launch.log', 'install-environment.log']:
    before = root / 'logs' / name
    saved = root / 'logs' / (name + '.before-offline')
    if saved.exists():
        raise RuntimeError('preserved original installer log already exists')
    saved.write_bytes(before.read_bytes())
print(json.dumps(state), flush=True)
