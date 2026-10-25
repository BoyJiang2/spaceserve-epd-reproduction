"""Remove only the recorded socket of an already stopped private MPS daemon."""
import json
import os
from pathlib import Path
import stat
import time
import psutil

root = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
if os.uname().nodename != 'qjh000' or os.environ.get('EXP_ROOT') != str(root) or os.environ.get('REPRO_HOST_LOCK_HELD') != '1':
    raise RuntimeError('private socket cleanup requires the owned qjh000 host lock')
folder = root / 'tmp/mps'
socket = folder / 'control'
if not socket.exists() and not socket.is_symlink():
    print('No stopped MPS socket to remove')
else:
    directory = folder.lstat()
    if not stat.S_ISDIR(directory.st_mode) or stat.S_IMODE(directory.st_mode) != 0o700 or directory.st_uid != os.getuid() or folder.resolve() != folder:
        raise RuntimeError('MPS directory identity/permissions differ')
    state = json.loads((root / 'evidence/mps-owner.json').read_text())
    if state.get('state') != 'stopped' or state.get('pipe') != str(folder) or not state.get('token', '').startswith(str(root) + ':'):
        raise RuntimeError('no stopped private daemon ownership record')
    if psutil.pid_exists(state['pid']):
        raise RuntimeError('recorded daemon PID still exists; preserve endpoint')
    for process in psutil.process_iter(['pid', 'name']):
        if (process.info['name'] or '').startswith('nvidia-cuda-mps'):
            raise RuntimeError('MPS process exists; preserve all endpoints')
    entry = socket.lstat()
    if not stat.S_ISSOCK(entry.st_mode) or entry.st_uid != os.getuid() or entry.st_ino != state['control_inode']:
        raise RuntimeError('socket inode/type/owner differs from stopped daemon')
    recorded_ns = time.time_ns()
    evidence = root / 'evidence' / f'mps-pruned-socket-{entry.st_ino}-{recorded_ns}.json'
    record = {'host': 'qjh000', 'stopped_owner': state, 'removed_socket': str(socket),
              'inode': entry.st_ino, 'uid': entry.st_uid, 'operation': 'unlink exact stopped socket only',
              'daemon_pid_absent': True, 'all_mps_processes_absent': True,
              'recorded_unix_ns': recorded_ns, 'unlink_succeeded': False,
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    with evidence.open('x') as output:
        json.dump(record, output, indent=2)
    if socket.lstat().st_ino != entry.st_ino:
        raise RuntimeError('socket changed before cleanup')
    socket.unlink()
    record['unlink_succeeded'] = True
    evidence.write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)
