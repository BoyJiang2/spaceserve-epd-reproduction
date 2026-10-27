"""Unlink only the recorded endpoint of this root's stopped, absent MPS daemon."""
import json
import os
from pathlib import Path
import stat
import time
import psutil

ROOT=Path('/var/tmp/boyjiang-spaceserve-window-20261027-1300')


def prune(root):
    folder=root/'tmp/mps'
    socket=folder/'control'
    if not socket.exists() and not socket.is_symlink():
        return {'removed':False,'reason':'no endpoint'}
    directory=folder.lstat()
    if not stat.S_ISDIR(directory.st_mode) or stat.S_IMODE(directory.st_mode)!=0o700 or directory.st_uid!=os.getuid() or folder.resolve(strict=True)!=folder:
        raise RuntimeError('private MPS directory identity differs')
    state=json.loads((root/'evidence/mps-owner.json').read_text())
    if state.get('state')!='stopped' or state.get('pipe')!=str(folder) or not state.get('token','').startswith(str(root)+':'):
        raise RuntimeError('no stopped private MPS owner proof')
    if psutil.pid_exists(state['pid']):
        raise RuntimeError('recorded daemon PID still exists')
    if any((p.info['name'] or '').startswith('nvidia-cuda-mps') for p in psutil.process_iter(['name'])):
        raise RuntimeError('MPS process still exists; preserve endpoint')
    entry=socket.lstat()
    if not stat.S_ISSOCK(entry.st_mode) or entry.st_uid!=os.getuid() or entry.st_ino!=state['control_inode']:
        raise RuntimeError('stopped endpoint inode/type/owner differs')
    record={'stopped_owner':state,'socket':str(socket),'inode':entry.st_ino,'uid':entry.st_uid,
            'operation':'unlink exact stopped socket only','daemon_absent':True,'all_MPS_absent':True,
            'recorded_unix_ns':time.time_ns(),'unlink_succeeded':False}
    evidence=root/'evidence'/f'mps-prune-{entry.st_ino}-{record["recorded_unix_ns"]}.json'
    with evidence.open('x') as output:
        json.dump(record,output,indent=2)
    current=socket.lstat()
    if (current.st_ino,current.st_uid,current.st_mode)!=(entry.st_ino,entry.st_uid,entry.st_mode):
        raise RuntimeError('endpoint changed before unlink')
    socket.unlink()
    record['unlink_succeeded']=True
    evidence.write_text(json.dumps(record,indent=2))
    return record


if __name__=='__main__':
    if not __debug__ or os.uname().nodename!='qjh000' or os.environ.get('EXP_ROOT')!=str(ROOT) or os.environ.get('REPRO_HOST_LOCK_HELD')!='1':
        raise RuntimeError('requires current root owned host lock')
    print(json.dumps(prune(ROOT)))
