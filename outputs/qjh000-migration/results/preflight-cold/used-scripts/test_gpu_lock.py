"""CPU-only guard: a runner exiting early must not release its orphan's lock."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
assert os.uname().nodename == 'qjh000'
evidence = root / 'evidence/cpu-lock-test'
evidence.mkdir(exist_ok=False)
environment = dict(os.environ, EXP_ROOT=str(root))
wrapper = root / 'scripts/gpu_exclusive.py'
outside = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], env={key: value for key, value in environment.items() if key not in {'EXP_ROOT', 'REPRO_RUN_ID'}})
runner = ('import subprocess,sys; p=subprocess.Popen([sys.executable,"-c",'
          '"import time; time.sleep(4)"]); print(p.pid, flush=True)')
first = subprocess.Popen([sys.executable, str(wrapper), 'space', sys.executable, '-c', runner], env=environment, stdout=subprocess.PIPE, text=True)
try:
    orphan = int(first.stdout.readline())
    time.sleep(.5)
    assert first.poll() is None, 'supervisor released while owned orphan remains'
    follower = subprocess.Popen([sys.executable, str(wrapper), 'space', sys.executable, '-c', 'print("FOLLOWER", flush=True)'], env=environment, stdout=subprocess.PIPE, text=True)
    time.sleep(.5)
    assert follower.poll() is None, 'second job acquired lock before orphan exit'
    first_output = first.communicate(timeout=12)[0]
    follower_output = follower.communicate(timeout=12)[0]
    assert first.returncode == follower.returncode == 0
    assert 'blocked-retaining-lock' in first_output and 'FOLLOWER' in follower_output
    assert outside.poll() is None, 'foreign process touched'
    result = {'passed': True, 'orphan_pid': orphan, 'first': first_output, 'follower': follower_output,
              'foreign_identity_untouched': True, 'gpu_calls': 0}
    (evidence / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
finally:
    outside.terminate()
    outside.wait(timeout=10)
    if first.poll() is None:
        first.terminate()
        first.wait(timeout=15)
