"""CPU-only reproduction of a process exiting between stat and environ."""
import importlib.util
from pathlib import Path
from unittest import mock
import sys
sys.dont_write_bytecode = True

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def stat(status, birth='123'):
    return '42 (fixture) ' + ' '.join([status, '1'] + ['0'] * 17 + [birth])

def race(module, status='Z', birth='123'):
    seq = [stat('S'), 'Uid:\t2147\t2147\t2147\t2147\n', stat(status, birth), stat(status, birth)]
    with mock.patch.object(module.Path, 'read_text', side_effect=seq), mock.patch.object(module.Path, 'read_bytes', side_effect=PermissionError('exit race')):
        return module.process(42)

for project, folder in [('epd', '/local/boyjiang/epd/assets/build'), ('space', '/local/boyjiang/spaceserve/assets')]:
    root = Path(folder)
    before = load(root / ('official_' + project + '_processes.py'), 'old_' + project)
    after = load(root / ('official_' + project + '_processes_candidate.py'), 'candidate_' + project)
    try:
        race(before)
    except PermissionError:
        pass
    else:
        raise AssertionError('original race not reproduced')
    assert race(after)['status'] == 'Z'
    for status, birth in [('S', '123'), ('Z', '456')]:
        try:
            race(after, status, birth)
        except PermissionError:
            pass
        else:
            raise AssertionError('unreadable live/reused identity accepted')
    saved = {'pid': 42, 'uid': 2147, 'start_ticks': '123'}
    zombie = dict(saved, status='Z', env={})
    with mock.patch.object(after, 'protected_pids', return_value=set()), mock.patch.object(after.os, 'pidfd_open', return_value=99), mock.patch.object(after.os, 'close'), mock.patch.object(after, 'process', return_value=zombie), mock.patch.object(after.signal, 'pidfd_send_signal') as send:
        after.send(saved, {}, after.signal.SIGTERM)
        send.assert_not_called()
    print(project + ': original race reproduced; candidate zombie/live/reused/no-signal checks passed')
