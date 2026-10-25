"""Keep the qjh000 GPU lock through owned-job cleanup and MPS shutdown."""
import fcntl
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
import uuid
import psutil

SPACE = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
LOCK = SPACE / 'tmp/host-gpu.lock'


def remaining_owned(root):
    result = []
    for process in psutil.process_iter():
        candidate = False
        try:
            if process.pid == os.getpid() or process.uids().real != os.getuid() or process.status() == psutil.STATUS_ZOMBIE:
                continue
            candidate = str(root) in ' '.join(process.cmdline()) or process.name().startswith('nvidia-cuda-mps')
            environment = process.environ()
            run_owned = environment.get('EXP_ROOT') == str(root) and environment.get('REPRO_RUN_ID', '').startswith(str(root) + ':')
            mps_owned = environment.get('EXP_ROOT') == str(root) and environment.get('CUDA_MPS_PIPE_DIRECTORY') == str(root / 'tmp/mps') and environment.get('REPRO_MPS_OWNER', '').startswith(str(root) + ':')
            if run_owned or mps_owned:
                result.append(process.pid)
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            if candidate:
                result.append(f'{process.pid}: identity inspection denied')
    return result


def main():
    mode, *command = sys.argv[1:]
    if mode != 'space' or not command or os.uname().nodename != 'qjh000':
        raise RuntimeError('expected qjh000 space command')
    root = SPACE
    if Path(os.environ['EXP_ROOT']).resolve() != root:
        raise RuntimeError('unexpected experiment root')
    descriptor = os.open(LOCK, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    info = os.fstat(descriptor)
    if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode):
        raise RuntimeError('host lock is not an owned regular file')
    with os.fdopen(descriptor, 'r+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps({'pid': os.getpid(), 'mode': mode, 'started_ns': time.time_ns()}))
        handle.flush()
        stop = []
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, lambda value, frame: stop.append(value))
        environment = dict(os.environ, REPRO_HOST_LOCK_HELD='1',
                           REPRO_RUN_ID=str(root) + ':supervisor:' + uuid.uuid4().hex)
        child = subprocess.Popen(command, env=environment, start_new_session=True)
        terminated = False
        try:
            while child.poll() is None:
                if stop and not terminated:
                    print(json.dumps({'state': 'yielding', 'child': child.pid, 'reason': 'supervisor signal'}), flush=True)
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    terminated = True
                time.sleep(1)
            code = child.wait()
        finally:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                child.wait()  # Keep the lock until owned cleanup and Nsight finalization finish.
        warned = False
        while True:
            remaining = remaining_owned(root)
            if not remaining:
                break
            if not warned:
                print(json.dumps({'state': 'blocked-retaining-lock', 'remaining': remaining}), flush=True)
                warned = True
            time.sleep(1)
        print(json.dumps({'state': 'yielded' if terminated else 'finished', 'child_exit': code}), flush=True)
        return 75 if terminated else code


if __name__ == '__main__':
    sys.exit(main())
