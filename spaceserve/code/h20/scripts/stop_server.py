"""Stop only the process tree of a recorded experiment server PID."""
import os
import json
import pathlib
import sys
import time
import psutil


root = pathlib.Path(sys.argv[1]).resolve()
identity = os.environ['REPRO_RUN_ID']
if str(root) != '/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023' or os.environ.get('EXP_ROOT') != str(root) or not identity.startswith(str(root) + ':'):
    raise RuntimeError('unexpected server cleanup identity')
try:
    process = psutil.Process(int(sys.argv[2]))
except psutil.NoSuchProcess:
    print('recorded API already exited', flush=True)
    raise SystemExit(0)
children = process.children(recursive=True)
targets = children + [process]


def validate(item):
    if item.status() == psutil.STATUS_ZOMBIE:
        return False
    if item.uids().real != os.getuid():
        raise RuntimeError('target UID differs')
    environment = item.environ()
    if environment.get('EXP_ROOT') != str(root) or environment.get('REPRO_RUN_ID') != identity:
        raise RuntimeError('target exact root/runID differs')
    return True


def wait_without_pidfd(items, timeout):
    # This host rejects pidfd_open with EINVAL; poll these exact Process objects.
    deadline = time.monotonic() + timeout
    while True:
        alive = []
        for item in items:
            try:
                if item.is_running() and item.status() != psutil.STATUS_ZOMBIE:
                    alive.append(item)
            except psutil.NoSuchProcess:
                pass
        if not alive or time.monotonic() >= deadline:
            return alive
        time.sleep(.05)


try:
    for item in targets:
        try:
            validate(item)
        except psutil.NoSuchProcess:
            continue
except (RuntimeError, psutil.AccessDenied) as error:
    record = {'refused': True, 'reason': str(error), 'recorded_api_pid': process.pid,
              'expected_root': str(root), 'expected_run_id': identity, 'target_pids': [item.pid for item in targets]}
    (root / 'evidence' / f'stop-refused-{time.time_ns()}.json').write_text(json.dumps(record, indent=2))
    raise
print('stopping PIDs', [item.pid for item in targets], flush=True)
for item in targets:
    try:
        if not validate(item):
            continue
        item.terminate()
    except psutil.NoSuchProcess:
        pass
alive = wait_without_pidfd(targets, timeout=8)
kill_targets = []
for item in alive:
    try:
        if not validate(item):
            continue
        item.kill()
        kill_targets.append(item)
    except psutil.NoSuchProcess:
        pass
if wait_without_pidfd(kill_targets, timeout=5):
    raise RuntimeError('owned server processes remain after bounded cleanup')
