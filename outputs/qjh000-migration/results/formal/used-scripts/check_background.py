"""Refuse measurement while another process from this SpaceServe batch remains."""
import os
from pathlib import Path


def check(root):
    import psutil
    root = str(root.resolve())
    current = psutil.Process()
    excluded = {current.pid, *(process.pid for process in current.parents())}
    remaining = []
    for process in psutil.process_iter():
        candidate = False
        try:
            if process.pid in excluded or process.uids().real != os.getuid() or process.status() == psutil.STATUS_ZOMBIE:
                continue
            candidate = root in ' '.join(process.cmdline())
            environment = process.environ()
            if candidate or environment.get('EXP_ROOT') == root:
                remaining.append({'pid': process.pid, 'name': process.name()})
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            if candidate:
                raise RuntimeError('batch process identity inaccessible; refuse measurement')
    if remaining:
        raise RuntimeError('batch background processes remain; do not terminate unknown tasks: ' + str(remaining))
    return {'passed': True, 'scope': 'all same-UID processes with exact EXP_ROOT or dedicated-root command path, excluding current process and ancestors'}


if __name__ == '__main__':
    import json
    root = Path(os.environ['EXP_ROOT'])
    if str(root.resolve()) != '/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023':
        raise RuntimeError('unexpected SpaceServe root')
    print(json.dumps(check(root)))
