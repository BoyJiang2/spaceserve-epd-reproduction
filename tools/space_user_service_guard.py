"""Narrow PAM cwd exception; no process signalling or filesystem mutation."""
import hashlib
import json
from pathlib import Path

BOOT='65f52a67-afe4-4919-8646-4694255b48ee'
CGROUP='0::/user.slice/user-2147.slice/user@2147.service/init.scope\n'
PAM_SHA='971490059d839d27af3ded30a476216b92689d837b0236a700723fb13640e370'
USER_SHA='8e5650cd3e49f78d40815491e0e012c21acac998215dd4338c62ac0eaed3bec0'
INIT_SHA='6628c1ade33319fc12730a87856ccdb1e4eaed9a0aa2b0bce0535a97a232f272'


def read_identity(proc,pid,uid,exe=False):
    if type(pid) is not int or pid<=0:raise ValueError('Invalid service PID')
    folder=proc/str(pid)
    if folder.stat().st_uid!=uid:raise ValueError('Service UID differs')
    fields=(folder/'stat').read_text().rsplit(')',1)[1].split()
    value=dict(pid=pid,uid=uid,comm=(folder/'comm').read_text().strip(),ppid=int(fields[1]),
        start_ticks=int(fields[19]),cgroup=(folder/'cgroup').read_text(),
        cmdline_sha256=hashlib.sha256((folder/'cmdline').read_bytes()).hexdigest())
    if exe:value['exe']=str((folder/'exe').resolve(strict=True))
    return value


def snapshot(proc,pid):
    child=read_identity(proc,pid,2147)
    if child['comm']!='(sd-pam)':return None
    parent=read_identity(proc,child['ppid'],2147,exe=True)
    init=read_identity(proc,1,0)
    return dict(boot_id=(proc/'sys/kernel/random/boot_id').read_text().strip(),child=child,parent=parent,init=init)


def validate(value):
    c,p,i=value['child'],value['parent'],value['init']
    if (value['boot_id']!=BOOT or c['uid']!=2147 or c['comm']!='(sd-pam)' or c['cmdline_sha256']!=PAM_SHA
            or c['cgroup']!=CGROUP or c['ppid']!=p['pid'] or p['uid']!=2147 or p['comm']!='systemd'
            or p['ppid']!=1 or p['exe']!='/usr/lib/systemd/systemd' or p['cmdline_sha256']!=USER_SHA or p['cgroup']!=CGROUP
            or i['pid']!=1 or i['uid']!=0 or i['ppid']!=0 or i['comm']!='systemd' or i['start_ticks']!=856
            or i['cgroup']!='0::/init.scope\n' or i['cmdline_sha256']!=INIT_SHA
            or type(c['pid']) is not int or type(p['pid']) is not int or not c['pid']>1 or not p['pid']>1
            or c['pid']==p['pid'] or type(c['start_ticks']) is not int or type(p['start_ticks']) is not int
            or not c['start_ticks']>=p['start_ticks']>=i['start_ticks']):
        raise ValueError('Exact user-service three-process chain differs')


def exception(proc,pid):
    before=snapshot(proc,pid)
    if before is None:return None
    validate(before)
    after=snapshot(proc,pid)
    if after!=before:raise ValueError('Service identity changed during observation')
    return dict(snapshot=before,sha256=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),
        scope='cwd PermissionError only; not project-process or runtime approval')


def guard_processes(assets,proc=Path('/proc')):
    # The original scan decides when cwd was unreadable; readable project cwd still fails there.
    original=assets.pam_exception
    def approved_exception(path,pid):
        result=original(path,pid)
        return result if result is not None else exception(path,pid)
    assets.pam_exception=approved_exception
    try:return assets.guard_processes(proc)
    finally:assets.pam_exception=original
