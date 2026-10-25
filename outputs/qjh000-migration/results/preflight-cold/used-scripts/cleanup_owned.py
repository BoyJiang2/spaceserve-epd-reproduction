"""Remove orphan processes carrying this run's exact private identity."""
import os
from pathlib import Path
import sys
import psutil

root = str(Path(sys.argv[1]).resolve())
identity = os.environ['REPRO_RUN_ID']
if root != '/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023' or not identity.startswith(root + ':'):
    raise RuntimeError('unexpected experiment identity')
me = psutil.Process()
excluded = {me.pid, *(parent.pid for parent in me.parents())}


def owned():
    result = []
    for process in psutil.process_iter():
        try:
            if process.pid in excluded or process.uids().real != os.getuid():
                continue
            environment = process.environ()
            if environment.get('REPRO_RUN_ID') == identity and environment.get('EXP_ROOT') == root:
                result.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return result


targets = owned()
print('orphan cleanup PIDs', [process.pid for process in targets], flush=True)
for process in targets:
    try:
        process.terminate()
    except psutil.NoSuchProcess:
        pass
_, alive = psutil.wait_procs(targets, timeout=8)
for process in alive:
    try:
        process.kill()
    except psutil.NoSuchProcess:
        pass
psutil.wait_procs(alive, timeout=5)
remaining = []
for process in owned():
    try:
        if process.status() != psutil.STATUS_ZOMBIE:
            remaining.append(process.pid)
    except psutil.NoSuchProcess:
        pass
if remaining:
    raise RuntimeError(f'owned processes remain: {remaining}')
