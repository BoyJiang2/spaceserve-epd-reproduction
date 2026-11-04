"""Register and stop processes carrying one exact official EPDServe run identity.

This CPU helper does not authorize GPU use or load any model packages.
"""
if not __debug__:
    raise RuntimeError('Refusing optimized Python: identity assertions must remain enabled')

import fcntl
import json
import os
from pathlib import Path
import re
import signal
import sys
import time


def protected_pids():
    protected = set()
    pid = os.getpid()
    while pid and pid not in protected:
        protected.add(pid)
        try:
            pid = int((Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()[1])
        except (FileNotFoundError, ProcessLookupError):
            break
    return protected


def process(pid):
    path = Path('/proc') / str(pid)
    try:
        stat = (path / 'stat').read_text().rsplit(')', 1)[1].split()
        uid = int(next(line for line in (path / 'status').read_text().splitlines()
                       if line.startswith('Uid:')).split()[1])
        # Exited zombies have no executable workload and may deny environ reads.
        deadline = time.monotonic() + .25
        while True:
            try:
                env = {} if stat[0] == 'Z' else dict(
                    part.split(b'=', 1) for part in
                    (path / 'environ').read_bytes().split(b'\0') if b'=' in part)
                break
            except PermissionError:
                exited = (path / 'stat').read_text().rsplit(')', 1)[1].split()
                if exited[19] != stat[19]:
                    raise RuntimeError('PID changed during observation')
                if exited[0] == 'Z':
                    env = {}
                    break
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.01)
        again = (path / 'stat').read_text().rsplit(')', 1)[1].split()
        if stat[19] != again[19]:
            raise RuntimeError('PID changed during observation')
        return {'pid': pid, 'uid': uid, 'start_ticks': stat[19],
                'parent': int(stat[1]), 'status': again[0], 'env': env}
    except (FileNotFoundError, ProcessLookupError):
        return None


def matches(item, state):
    return (item['uid'] == state['uid'] and
            int(item['start_ticks']) >= state['min_start_ticks'] and
            item['env'].get(b'EXP_ROOT') == state['root'].encode() and
            item['env'].get(b'REPRO_RUN_ID') == state['runid'].encode())


def observe(state):
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == state['boot']
    protected = protected_pids()
    unreadable = []
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        pid = int(path.name)
        if pid in protected:
            continue
        try:
            if path.stat().st_uid != state['uid']:
                continue
            item = process(pid)
        except PermissionError:
            unreadable.append(pid)
            if str(pid) in state['known']:
                raise RuntimeError('Known process identity unreadable: ' + str(pid))
            continue
        except (FileNotFoundError, ProcessLookupError):
            continue
        if item and matches(item, state):
            identity = {key: item[key] for key in ('pid', 'uid', 'start_ticks', 'parent')}
            previous = state['known'].get(str(pid))
            assert previous is None or all(previous[key] == identity[key]
                                           for key in ('pid', 'uid', 'start_ticks')), 'PID identity changed'
            if previous is None:
                state['known'][str(pid)] = identity
    state['unreadable_same_uid'] = unreadable
    alive = []
    for saved in state['known'].values():
        if saved['pid'] in protected:
            continue
        item = process(saved['pid'])
        if item and item['start_ticks'] == saved['start_ticks'] and item['status'] != 'Z':
            assert matches(item, state), 'Known live process lost its run identity'
            alive.append(saved)
    return alive


def send(saved, state, sig):
    assert saved['pid'] not in protected_pids(), 'Refusing to signal supervisor or ancestors'
    try:
        descriptor = os.pidfd_open(saved['pid'])
    except ProcessLookupError:
        return
    try:
        item = process(saved['pid'])
        if item is None:
            return
        assert item['start_ticks'] == saved['start_ticks'], 'PID was reused; refusing signal'
        if item['status'] == 'Z':
            return
        assert matches(item, state), 'Run identity differs; refusing signal'
        signal.pidfd_send_signal(descriptor, sig)
    except ProcessLookupError:
        pass
    finally:
        os.close(descriptor)


def stop(state):
    for sig, seconds in ((signal.SIGTERM, 8), (signal.SIGKILL, 5)):
        for saved in observe(state):
            send(saved, state, sig)
        until = time.monotonic() + seconds
        while observe(state) and time.monotonic() < until:
            time.sleep(.1)
    remaining = observe(state)
    if remaining:
        raise RuntimeError('Known run processes remain: ' + repr(remaining))
    return remaining


if __name__ == '__main__':
    mode, filename = sys.argv[1:]
    assert mode in ('observe', 'stop')
    path = Path(filename).resolve()
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(path.read_text())
        assert state['uid'] == os.getuid() == 2147
        assert state['root'] == '/local/boyjiang/epdserve-official'
        assert re.fullmatch(re.escape(str(path.parent)) + r':[0-9a-f]{32}', state['runid'])
        assert str(path.parent).startswith('/local/boyjiang/epd/runs/')
        assert hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal')
        state.pop('known_run_processes_absent', None)
        try:
            alive = stop(state) if mode == 'stop' else observe(state)
            state['last_observed_epoch'] = time.time()
            state['known_live'] = alive
            if mode == 'stop':
                state['known_run_processes_absent'] = True
                state['scope_note'] = 'Known workloads exclude supervisor/ancestors. Unknown identities are never signalled; GPU release requires separate evidence.'
            print(json.dumps({'known': len(state['known']), 'known_live': alive,
                              'unreadable_same_uid': state.get('unreadable_same_uid', [])}))
        finally:
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(state, indent=2))
            temporary.replace(path)
