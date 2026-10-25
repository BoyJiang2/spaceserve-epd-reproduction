"""CPU-only: current run can stop; another run or foreign child must survive."""
import json
import os
from pathlib import Path
import subprocess
import sys
import psutil

root = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
identity = str(root) + ':cpu-stop-fixture'
base = dict(os.environ, EXP_ROOT=str(root), REPRO_RUN_ID=identity)
script = 'import os,subprocess,sys,time; e=dict(os.environ,REPRO_RUN_ID=sys.argv[1]); p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"],env=e); print(p.pid,flush=True); time.sleep(60)'
results = []
for case in ['owned', 'different-run', 'foreign-child']:
    environment = dict(base, REPRO_RUN_ID=identity + ':other') if case == 'different-run' else base
    child_identity = identity + ':other' if case != 'owned' else identity
    parent = subprocess.Popen([sys.executable, '-c', script, child_identity], env=environment, stdout=subprocess.PIPE, text=True)
    child = psutil.Process(int(parent.stdout.readline()))
    try:
        checked = subprocess.run([sys.executable, str(root / 'scripts/stop_server.py'), str(root), str(parent.pid)], env=base, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(json.dumps({'case': case, 'stop_returncode': checked.returncode, 'output': checked.stdout}), flush=True)
        if case == 'owned':
            assert checked.returncode == 0
            assert parent.poll() is not None and (not child.is_running() or child.status() == psutil.STATUS_ZOMBIE)
        else:
            assert checked.returncode != 0 and parent.poll() is None and child.is_running() and child.status() != psutil.STATUS_ZOMBIE
        results.append({'case': case, 'passed': True, 'stop_returncode': checked.returncode, 'output': checked.stdout})
    finally:
        for item in [child, psutil.Process(parent.pid) if parent.poll() is None else None]:
            if item is not None:
                try:
                    item.terminate()
                except psutil.NoSuchProcess:
                    pass
        parent.wait(timeout=10)
print(json.dumps({'passed': True, 'gpu_calls': 0, 'cases': results}), flush=True)
