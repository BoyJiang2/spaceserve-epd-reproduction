"""CPU-only: remove a detached orphan, retain foreign processes, tolerate exit races."""
import contextlib
import io
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import types
from unittest.mock import patch
import psutil

root = Path('/local/boyjiang/epd-profile-a-20261023')
script = root / 'scripts/cleanup_owned.py'
identity = str(root) + ':cpu-test:' + str(os.getpid())
environment = {**os.environ, 'EXP_ROOT': str(root), 'REPRO_RUN_ID': identity}
foreign = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)'], env={**environment, 'REPRO_RUN_ID': identity + '-foreign'}, start_new_session=True)
orphan = None
try:
    parent_code = 'import subprocess,sys; p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(600)"],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid,flush=True)'
    parent = subprocess.Popen([sys.executable, '-c', parent_code], env=environment, start_new_session=True, stdout=subprocess.PIPE, text=True)
    orphan = psutil.Process(int(parent.stdout.readline()))
    assert parent.wait(timeout=10) == 0
    subprocess.run([sys.executable, str(script), str(root)], env=environment, check=True, timeout=30)
    assert not orphan.is_running() or orphan.status() == psutil.STATUS_ZOMBIE
    assert foreign.poll() is None, 'foreign run identity must survive'
finally:
    foreign.terminate()
    foreign.wait(timeout=10)
    if orphan is not None:
        try:
            if orphan.is_running() and orphan.status() != psutil.STATUS_ZOMBIE:
                orphan.kill()
        except psutil.NoSuchProcess:
            pass


class Target:
    def __init__(self, pid, vanished):
        self.pid, self.vanished, self.stopped = pid, vanished, False
    def uids(self):
        return types.SimpleNamespace(real=os.getuid())
    def environ(self):
        return {'REPRO_RUN_ID': identity, 'EXP_ROOT': str(root)}
    def terminate(self):
        if self.vanished:
            raise psutil.NoSuchProcess(self.pid)
        self.stopped = True
    def status(self):
        if self.vanished:
            raise psutil.NoSuchProcess(self.pid)
        return psutil.STATUS_ZOMBIE if self.stopped else psutil.STATUS_RUNNING


targets = [Target(10000001, True), Target(10000002, False)]
me = types.SimpleNamespace(pid=os.getpid(), parents=lambda: [])
with patch.dict(os.environ, environment), patch.object(sys, 'argv', [str(script), str(root)]), patch.object(psutil, 'Process', return_value=me), patch.object(psutil, 'process_iter', return_value=targets), patch.object(psutil, 'wait_procs', return_value=(targets, [])), contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(script), run_name='__main__')
assert targets[1].stopped, 'one vanished target must not prevent cleanup of another'
print('PASS: detached orphan removed, foreign identity retained, vanished-target race tolerated; no GPU used')
