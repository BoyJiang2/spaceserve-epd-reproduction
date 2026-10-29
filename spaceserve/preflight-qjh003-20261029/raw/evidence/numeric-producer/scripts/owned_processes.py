"""Stop only this exact run identity, never an unbound PID or another user's job."""
import os
from pathlib import Path
import time
import psutil

from runtime_config import context
CONFIG = context()
ROOT = CONFIG.run_root


class IdentityUnconfirmed(RuntimeError):
    pass


def _owned_once(identity, excluded=()):
    if not identity.startswith(str(ROOT) + ':'):
        raise RuntimeError('unbound run identity')
    result = []
    for process in psutil.process_iter():
        candidate = False
        try:
            if process.pid in excluded:
                continue
            candidate = process.name().startswith(('ray', 'python')) or process.name() in ('gcs_server', 'plasma_store')
            candidate = candidate or str(ROOT) in ' '.join(process.cmdline())
            if process.uids().real != os.getuid() or process.status() == psutil.STATUS_ZOMBIE:
                continue
            env = process.environ()
            if env.get('EXP_ROOT') == str(ROOT) and env.get('REPRO_RUN_ID') == identity:
                result.append((process.pid, process.create_time()))
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            if candidate:
                raise IdentityUnconfirmed(f'cannot confirm candidate process identity: {process.pid}')
    return result


def owned(identity, excluded=()):
    # An exiting raylet can briefly deny /proc/environ before disappearing.
    # Retry reads only; persistent uncertainty must still fail without signalling it.
    deadline = time.monotonic() + 1.0
    while True:
        try:
            return _owned_once(identity, excluded)
        except IdentityUnconfirmed:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.05)


def stop(identity):
    me = psutil.Process()
    excluded = {me.pid, *(item.pid for item in me.parents())}
    def signal(candidates, force):
        for pid, creation in candidates:
            try:
                process = psutil.Process(pid)
                if process.create_time() != creation or (pid, creation) not in owned(identity, excluded):
                    continue
                process.kill() if force else process.terminate()
            except psutil.NoSuchProcess:
                pass
    signal(owned(identity, excluded), False)
    deadline = time.monotonic() + 8
    while owned(identity, excluded) and time.monotonic() < deadline:
        time.sleep(.2)
    signal(owned(identity, excluded), True)
    deadline = time.monotonic() + 5
    while owned(identity, excluded) and time.monotonic() < deadline:
        time.sleep(.2)
    if owned(identity, excluded):
        raise RuntimeError('owned processes remain; keep lock and do not start next run')
