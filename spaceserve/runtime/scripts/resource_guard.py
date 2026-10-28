"""Bind a run to reviewed code, fresh resources and both new/old project GPU locks."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import socket
import signal
import stat
import subprocess
import time

from runtime_config import context
CONFIG = context()
ROOT = CONFIG.run_root
DEVICES = CONFIG.gpu_devices
UUIDS = list(CONFIG.gpu_uuids)


class RunInterrupted(RuntimeError):
    pass


@contextlib.contextmanager
def run_signals():
    numbers = [signal.SIGTERM, signal.SIGINT]
    if hasattr(signal, 'SIGALRM'):
        numbers.append(signal.SIGALRM)
    previous = {number: signal.getsignal(number) for number in numbers}
    def interrupt(number, _frame):
        # One controlled unwind; repeated signals must not interrupt owned cleanup.
        for item in previous:
            signal.signal(item, signal.SIG_IGN)
        raise RunInterrupted('run interrupted by signal ' + str(number))
    try:
        for number in previous:
            signal.signal(number, interrupt)
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_identity(action=None):
    manifest = ROOT / 'configs/code-manifest.json'
    approval = json.loads((ROOT / 'evidence/G2_CODE_APPROVED.json').read_text())
    if approval.get('passed') is not True or approval['code_manifest_sha256'] != sha(manifest):
        raise RuntimeError('G2 does not approve this code manifest')
    if approval.get('boot_id') != Path('/proc/sys/kernel/random/boot_id').read_text().strip() or approval.get('gpu_uuids') != UUIDS:
        raise RuntimeError('G2 runtime deployment boot/GPU binding differs')
    if action is not None and action not in approval.get('allowed_actions', []):
        raise RuntimeError('G2 does not approve this action')
    # The completed numeric producer remains immutable. Model/formal consumers
    # verify its archived source; their own current source has a separate G2.
    archive = ROOT / 'evidence/numeric-producer' if action is None else ROOT
    for row in json.loads(manifest.read_text()):
        path = archive / row['path']
        if not path.resolve().is_relative_to(ROOT) or sha(path) != row['sha256']:
            raise RuntimeError('reviewed code changed')
    return approval['code_manifest_sha256']


def idle():
    rows = subprocess.check_output(['nvidia-smi', '--id=' + ','.join(map(str, DEVICES)), '--query-gpu=uuid,memory.used,utilization.gpu', '--format=csv,noheader,nounits'], text=True).splitlines()
    if [line.split(',')[0].strip() for line in rows] != UUIDS:
        raise RuntimeError('physical GPU identity changed')
    processes = subprocess.check_output(['nvidia-smi', '--id=' + ','.join(map(str, DEVICES)), '--query-compute-apps=pid', '--format=csv,noheader'], text=True)
    if processes.strip() or any(int(line.split(',')[1]) > 100 for line in rows):
        raise RuntimeError('selected GPUs not idle')


def gate(name, code):
    state = json.loads((ROOT / 'evidence' / name).read_text())
    if not state['passed'] or state['code_manifest_sha256'] != code or state['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip() or state['gpu_uuids'] != UUIDS:
        raise RuntimeError('stale or unbound runtime gate')
    if not state.get('bound_files'):
        raise RuntimeError('runtime gate has no bound evidence')
    for row in state['bound_files']:
        path = ROOT / row['path']
        if not path.resolve().is_relative_to(ROOT) or sha(path) != row['sha256']:
            raise RuntimeError('runtime gate evidence changed')
    return state


def remaining_owned():
    import psutil
    result = []
    for process in psutil.process_iter():
        candidate = False
        try:
            if process.pid == os.getpid():
                continue
            candidate = process.name().startswith(('ray', 'python','nvidia-cuda-mps')) or process.name() in ('gcs_server', 'plasma_store')
            candidate = candidate or str(ROOT) in ' '.join(process.cmdline())
            if process.uids().real != os.getuid() or process.status() == psutil.STATUS_ZOMBIE:
                continue
            env = process.environ()
            if env.get('EXP_ROOT') == str(ROOT) and env.get('REPRO_RUN_ID', '').startswith(str(ROOT) + ':'):
                result.append(process.pid)
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            if candidate:
                result.append(f'{process.pid}:identity-unconfirmed')
    return result


@contextlib.contextmanager
def _exclusive(action, phase=None):
    import fcntl
    CONFIG.require_scope(phase or action)
    if socket.gethostname() != CONFIG.config['host'] or Path(os.environ['EXP_ROOT']).resolve() != ROOT:
        raise RuntimeError('wrong experiment host/root')
    if not json.loads((ROOT / 'evidence/CPU_STAGED.json').read_text())['destination_verified']:
        raise RuntimeError('CPU staging incomplete')
    handles = []
    acquired = False
    try:
        # Both projects use the same owned host lock; it does not confer a reservation.
        for path, flags in [(CONFIG.host_lock, os.O_RDWR | os.O_CREAT),
                            (ROOT / 'tmp/host-gpu.lock', os.O_RDWR | os.O_CREAT)]:
            descriptor = os.open(path, flags | os.O_NOFOLLOW, 0o600)
            handle = os.fdopen(descriptor, 'r' if flags == os.O_RDONLY else 'r+')
            handles.append(handle)
            info = os.fstat(descriptor)
            if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode):
                raise RuntimeError('lock is not an owned regular file')
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquired = True
        idle()
        yield code_identity(action)
        idle()
    finally:
        if acquired:
            for number in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
                signal.signal(number, signal.SIG_IGN)
        while acquired and remaining_owned():
            print(json.dumps({'state': 'retaining-lock-owned-processes-remain', 'pids': remaining_owned()}), flush=True)
            time.sleep(1)
        for handle in reversed(handles):
            handle.close()


@contextlib.contextmanager
def exclusive(action):
    from booking_window import require
    with run_signals():
        remaining = require(fresh=True)
        signal.setitimer(signal.ITIMER_REAL, remaining)
        try:
            with _exclusive(action) as code:
                yield code
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
