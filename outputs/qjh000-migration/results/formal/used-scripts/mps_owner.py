"""Control only a daemon with a recorded PID, start time and private identity."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import psutil

root = Path(os.environ['EXP_ROOT']).resolve()
if str(root) != '/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023':
    raise RuntimeError('unexpected MPS workspace')
pipe = root / 'tmp/mps'
logs = root / 'logs/mps'
for folder in [pipe, logs]:
    folder.mkdir(parents=True, exist_ok=True)
    folder.chmod(0o700)
state_file = root / 'evidence/mps-owner.json'
environment = {**os.environ, 'CUDA_MPS_PIPE_DIRECTORY': str(pipe), 'CUDA_MPS_LOG_DIRECTORY': str(logs),
               'CUDA_MPS_ACTIVE_THREAD_PERCENTAGE': '100'}


def control(command):
    return subprocess.check_output(['nvidia-cuda-mps-control'], input=command + '\n', text=True, env=environment, timeout=30)


def validate(state):
    process = psutil.Process(state['pid'])
    current = process.environ()
    if process.uids().real != os.getuid() or process.create_time() != state['created'] or current.get('REPRO_MPS_OWNER') != state['token'] or current.get('CUDA_MPS_PIPE_DIRECTORY') != str(pipe) or (pipe / 'control').stat().st_ino != state['control_inode']:
        raise RuntimeError('MPS daemon identity mismatch; refuse control command')
    return process


with (root / 'tmp/mps-owner.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    action = sys.argv[1]
    if action == 'start':
        if int(sys.argv[2]) != 0:
            raise RuntimeError('preflight selected GPU0 only')
        if (pipe / 'control').exists():
            raise RuntimeError('private MPS endpoint already exists')
        if state_file.exists() and json.loads(state_file.read_text()).get('state') == 'running':
            raise RuntimeError('previous MPS ownership remains unresolved')
        existing = [p.info['pid'] for p in psutil.process_iter(['pid', 'name']) if (p.info['name'] or '').startswith('nvidia-cuda-mps')]
        if existing:
            raise RuntimeError(f'existing MPS processes; do not touch: {existing}')
        selected = subprocess.check_output(['nvidia-smi', '--id=0', '--query-gpu=uuid', '--format=csv,noheader'], text=True).strip()
        if subprocess.check_output(['nvidia-smi', '--id=0', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip():
            raise RuntimeError('GPU0 is no longer idle')
        token = str(root) + ':' + uuid.uuid4().hex
        environment.update(CUDA_VISIBLE_DEVICES=selected, REPRO_MPS_OWNER=token)
        subprocess.run(['nvidia-cuda-mps-control', '-d'], check=True, env=environment, timeout=30)
        daemon = None
        for attempt in range(100):
            matches = []
            for process in psutil.process_iter(['pid', 'name']):
                try:
                    if (process.info['name'] or '').startswith('nvidia-cuda-mps-control') and process.uids().real == os.getuid() and process.environ().get('REPRO_MPS_OWNER') == token:
                        matches.append(process)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if len(matches) == 1 and (pipe / 'control').exists():
                daemon = matches[0]
                break
            time.sleep(.05)
        if daemon is None:
            raise RuntimeError('MPS identity not confirmed; refuse quit to an unknown daemon')
        state = {'state': 'running', 'pid': daemon.pid, 'created': daemon.create_time(), 'token': token,
                 'pipe': str(pipe), 'uuid': selected, 'active_thread_percentage': 100,
                 'control_inode': (pipe / 'control').stat().st_ino}
        validate(state)
        state_file.write_text(json.dumps(state, indent=2))
        (root / 'results/mps-gpu-uuids.txt').write_text(selected + '\n')
        print(json.dumps(state))
    elif action in {'status', 'stop'}:
        state = json.loads(state_file.read_text())
        if state['state'] != 'running':
            raise RuntimeError('this batch does not own a running daemon')
        daemon = validate(state)
        if action == 'status':
            print(control('get_server_list'), end='')
            print(control('ps'), end='')
        else:
            print(control('quit'), end='')
            try:
                daemon.wait(timeout=30)
            except psutil.NoSuchProcess:
                pass
            state['state'] = 'stopped'
            state_file.write_text(json.dumps(state, indent=2))
    else:
        raise RuntimeError('expected start/status/stop')
