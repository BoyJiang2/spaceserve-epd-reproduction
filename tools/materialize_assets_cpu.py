"""Copy only frozen qjh003 project assets; never load a model or modify a source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import stat
import time
import re
import shutil
import io

import migrate_code_cpu as migration

LEGACY=migration.PARENT/'spaceserve-epd-qjh003-20261023'
BOOT='65f52a67-afe4-4919-8646-4694255b48ee'
RUNTIME_COMMIT='a3f03b9dd5956db92add454f9b3afd5663f84609'
COMPONENTS={
    'data': [('dataset','spaceserve','dataset'),('dataset','epd','dataset'),
             ('build/epd-cuda/libcuda_ipc_utils.so','epd','build/epd-cuda/libcuda_ipc_utils.so')],
    'env': [('envs/epd','epd','envs/epd')],
    'model': [('models/MiniCPM-V-2_6','epd','models/MiniCPM-V-2_6')],
}
LINKS={'lib64':'lib','bin/python':'/usr/bin/python3','bin/python3':'python','bin/python3.10':'python'}
LIMIT=30*1024**3
OWNER=2147
PAM_SNAPSHOT={'boot_id':BOOT,'processes':[
    {'pid':2565253,'uid':2147,'comm':'systemd','ppid':1,'start_ticks':12603390,
     'cmdline_sha256':'8e5650cd3e49f78d40815491e0e012c21acac998215dd4338c62ac0eaed3bec0',
     'cgroup':'0::/user.slice/user-2147.slice/user@2147.service/init.scope\n','exe':'/usr/lib/systemd/systemd'},
    {'pid':2565254,'uid':2147,'comm':'(sd-pam)','ppid':2565253,'start_ticks':12603391,
     'cmdline_sha256':'971490059d839d27af3ded30a476216b92689d837b0236a700723fb13640e370',
     'cgroup':'0::/user.slice/user-2147.slice/user@2147.service/init.scope\n'}]}


def fingerprint(info):
    return (info.st_dev,info.st_ino,info.st_uid,info.st_mode,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def inventory(root,check,allow_links=False):
    """Include every member, including caches and hidden files; follow no links."""
    rows=[];total=0
    def visit(path,relative):
        nonlocal total
        check();before=path.lstat();mode=stat.S_IMODE(before.st_mode)
        if before.st_uid!=OWNER or mode & 0o6000:raise ValueError('Foreign owner or privileged mode')
        row={'path':relative,'mode':mode}
        if stat.S_ISLNK(before.st_mode):
            target=os.readlink(path)
            if not allow_links or LINKS.get(relative)!=target:raise ValueError('Unapproved asset symlink')
            row.update(type='link',target=target)
        elif stat.S_ISDIR(before.st_mode):
            row['type']='directory';rows.append(row)
            for child in sorted(path.iterdir()):visit(child,child.name if relative=='.' else relative+'/'+child.name)
            return
        elif stat.S_ISREG(before.st_mode):
            total+=before.st_size
            if total>LIMIT:raise ValueError('Asset byte budget exceeded')
            value=hashlib.sha256()
            descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(descriptor,'rb') as stream:
                if fingerprint(os.fstat(stream.fileno()))!=fingerprint(before):raise ValueError('Source changed before read')
                while block:=stream.read(4*1024**2):check();value.update(block)
            if fingerprint(path.lstat())!=fingerprint(before):raise ValueError('Asset changed during hash')
            row.update(type='file',bytes=before.st_size,sha256=value.hexdigest())
        else:raise ValueError('Special asset file refused')
        rows.append(row)
    visit(root,'.')
    return rows


def copy_members(source,target,rows,check):
    """Exclusive creation only. Failure leaves the original partial for inspection."""
    for row in rows:
        check();src=source if row['path']=='.' else source/row['path']
        dst=target if row['path']=='.' else target/row['path']
        if row['type']=='directory':
            dst.mkdir(mode=row['mode']);os.chmod(dst,row['mode'])
        elif row['type']=='link':os.symlink(row['target'],dst)
        else:
            descriptor=os.open(src,os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(descriptor,'rb') as reader,dst.open('xb') as writer:
                copied=0;value=hashlib.sha256()
                while block:=reader.read(4*1024**2):
                    check();copied+=len(block)
                    if copied>row['bytes']:raise ValueError('Source grew during copy')
                    writer.write(block);value.update(block)
                writer.flush();os.fsync(writer.fileno())
            os.chmod(dst,row['mode'])
            if copied!=row['bytes'] or value.hexdigest()!=row['sha256']:raise ValueError('Copied source changed')


def pam_snapshot(proc):
    rows=[]
    for pid in (2565253,2565254):
        folder=proc/str(pid);fields=(folder/'stat').read_text().rsplit(')',1)[1].split()
        row={'pid':pid,'uid':folder.stat().st_uid,'comm':(folder/'comm').read_text().strip(),
             'ppid':int(fields[1]),'start_ticks':int(fields[19]),
             'cmdline_sha256':hashlib.sha256((folder/'cmdline').read_bytes()).hexdigest(),
             'cgroup':(folder/'cgroup').read_text()}
        if pid==2565253:row['exe']=os.readlink(folder/'exe')
        rows.append(row)
    return {'boot_id':(proc/'sys/kernel/random/boot_id').read_text().strip(),'processes':rows}


def pam_exception(proc,pid):
    if pid!=2565254:return None
    before=pam_snapshot(proc)
    if before!=PAM_SNAPSHOT or pam_snapshot(proc)!=before:raise ValueError('PAM service identity changed')
    return {'snapshot':before,'sha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest()}


def ssh_snapshot(proc,pid):
    def read(number):
        folder=proc/str(number);fields=(folder/'stat').read_text().rsplit(')',1)[1].split()
        return {'pid':number,'uid':folder.stat().st_uid,'comm':(folder/'comm').read_text().strip(),
                'ppid':int(fields[1]),'start_ticks':int(fields[19]),'cgroup':(folder/'cgroup').read_text(),
                'cmdline_sha256':hashlib.sha256((folder/'cmdline').read_bytes()).hexdigest()}
    child=read(pid)
    return {'boot_id':(proc/'sys/kernel/random/boot_id').read_text().strip(),
            'child':child,'parent':read(child['ppid']),'daemon':read(7347)}


def ssh_exception(proc,pid):
    snapshot=ssh_snapshot(proc,pid);child=snapshot['child'];parent=snapshot['parent'];daemon=snapshot['daemon']
    anchor={'pid':7347,'uid':0,'comm':'sshd','ppid':1,'start_ticks':19660,
            'cgroup':'0::/system.slice/ssh.service\n'}
    if (snapshot['boot_id']!=BOOT or child['uid']!=2147 or child['comm']!='sshd'
            or child['cmdline_sha256']!='3b019070d13e4d05f268dd5f7ac3f625caa6b4fa35efddc49c30935466bde1bb'
            or not re.fullmatch(r'0::/user\.slice/user-2147\.slice/session-[0-9]+\.scope\n',child['cgroup'])
            or child['ppid']!=parent['pid'] or parent['uid']!=0 or parent['comm']!='sshd' or parent['ppid']!=7347
            or any(daemon[key]!=value for key,value in anchor.items())):return None
    if ssh_snapshot(proc,pid)!=snapshot:raise ValueError('SSH service identity changed')
    return {'snapshot':snapshot,'sha256':hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()}


def guard_processes(proc=Path('/proc')):
    """A cwd guard only, not an audit of every process FD or source reference."""
    roots=(LEGACY,migration.PARENT/'spaceserve',migration.PARENT/'epd')
    exceptions=[]
    for folder in proc.iterdir():
        if not folder.name.isdigit():continue
        try:
            if folder.stat().st_uid!=2147 or int(folder.name)==os.getpid():continue
        except (FileNotFoundError,ProcessLookupError):continue
        try:
            cwd=(folder/'cwd').resolve(strict=True)
            if any(cwd.is_relative_to(root) for root in roots):raise ValueError('Project cwd active')
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError:
            match=pam_exception(proc,int(folder.name))
            if match is None:match=ssh_exception(proc,int(folder.name))
            if match is None:raise ValueError('Own process cwd cannot be verified')
            exceptions.append(match)
    return exceptions


def create_evidence(path,git_log):
    migration.real_ancestry(path)
    path.mkdir(mode=0o700)
    migration.real_ancestry(path)
    with (path/'git-validation.log').open('xb') as stream:stream.write(git_log)


def run(args):
    proof=json.loads(args.booking_json);start=time.monotonic();deadline=start+900
    def check():
        if time.monotonic()>=deadline:raise TimeoutError('900-second asset unit exhausted')
        migration.booking(proof,int(time.time()*1000))
    check();migration.validate_executor()
    if not re.fullmatch('[0-9a-f]{40}',args.tool_commit):raise ValueError('Full pushed tool commit required')
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT:raise ValueError('Actual boot changed')
    if args.runtime_commit!=RUNTIME_COMMIT:raise ValueError('Unexpected frozen runtime commit')
    for root in (LEGACY,*(migration.PARENT/p for p in ('spaceserve','epd'))):migration.real_ancestry(root)
    # Only recorded, already audited code checkouts are accepted. No Git subprocesses or code mutations.
    git_log=io.BytesIO()
    for project in ('spaceserve','epd'):
        repo=migration.PARENT/project/'repo'
        migration.real_ancestry(repo/'.git')
        if (repo/'.git/HEAD').is_symlink():raise ValueError('Linked Git HEAD refused')
        if (repo/'.git/HEAD').read_text().strip()!=RUNTIME_COMMIT:raise ValueError('Runtime HEAD changed')
        if migration.command_output(['git','-c','core.fsmonitor=false','-C',str(repo),'status',
                '--porcelain','--untracked-files=all'],git_log,15,start+1020).strip():
            raise ValueError('Runtime checkout is dirty')
        receipt=json.loads((repo.parent/'staging/CPU_CODE_DEPLOYED.json').read_bytes())
        if receipt['commit']!=RUNTIME_COMMIT:raise ValueError('Audited deployment differs')
        for row in receipt['files']:
            path=repo/row['path']
            if path.is_symlink() or migration.sha(path)!=row['sha256']:raise ValueError('Frozen source changed')
    mappings=COMPONENTS[args.unit]
    for member,project,relative in mappings:
        source=LEGACY/member;target=migration.PARENT/project/'assets'/relative
        migration.real_ancestry(source.parent);migration.real_ancestry(target.parent)
        if not source.exists() or source.is_symlink() or os.path.lexists(target):raise ValueError('Missing source or existing target')
    process_exceptions=guard_processes()
    evidence=migration.PARENT/'epd/staging'/('asset-'+args.unit)
    create_evidence(evidence,git_log.getvalue())
    def save(name,value):
        migration.real_ancestry(evidence)
        migration.exclusive_json(evidence/name,value)
    identity={'unit':args.unit,'runtime_commit':RUNTIME_COMMIT,'tool_commit':args.tool_commit,
              'pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],
              'host':socket.gethostname(),'uid':os.getuid(),'boot_id':BOOT,'booking':proof,
              'started_ms':int(time.time()*1000),'GPU_queries':0,'package_imports':0,
              'process_guard_exceptions':process_exceptions}
    save('claim.json',identity)
    previous=signal.getsignal(signal.SIGALRM)
    def interrupted(number,frame):raise TimeoutError('Asset unit interrupted: '+str(number))
    handlers={number:signal.getsignal(number) for number in (signal.SIGTERM,signal.SIGINT)}
    signal.signal(signal.SIGALRM,interrupted)
    for number in handlers:signal.signal(number,interrupted)
    signal.alarm(max(1,int(deadline-time.monotonic())))
    completed=[];failure=None
    try:
        for index,(member,project,relative) in enumerate(mappings):
            source=LEGACY/member;target=migration.PARENT/project/'assets'/relative
            before=inventory(source,check,args.unit=='env')
            if args.unit=='env' and {row['path']:row['target'] for row in before if row['type']=='link'}!=LINKS:
                raise ValueError('Exact four environment links required')
            save(str(index)+'-source-before.json',before)
            total=sum(row.get('bytes',0) for row in before)
            if shutil.disk_usage(migration.PARENT/project/'assets').free<total+2*1024**3:
                raise ValueError('Insufficient real free space')
            if member=='dataset' and project=='spaceserve':
                pins=json.loads((migration.PARENT/'spaceserve/repo/spaceserve/runtime/configs/asset-content-pins.json').read_bytes())
                actual={row['path']:row for row in before}
                for pin in (row for row in pins if row['path'].startswith('dataset/')):
                    row=actual.get(pin['path'][8:])
                    if row is None or any(row[key]!=pin[key] for key in ('bytes','sha256')):raise ValueError('Space dataset pin differs')
            target.parent.mkdir(parents=True,exist_ok=True)
            migration.real_ancestry(target.parent)
            copy_members(source,target,before,check)
            after=inventory(source,check,args.unit=='env');copied=inventory(target,check,args.unit=='env')
            save(str(index)+'-source-after.json',after)
            save(str(index)+'-target.json',copied)
            if before!=after or before!=copied:raise ValueError('Complete asset manifests differ')
            completed.append({'source':str(source),'target':str(target),'bytes':total,'members':len(before)})
        check()
    except BaseException as error:
        failure=repr(error)
        raise
    finally:
        signal.alarm(0)
        for number in (*handlers,signal.SIGALRM):signal.signal(number,signal.SIG_IGN)
        try:
            save('terminal.json',{
                **identity,'ended_ms':int(time.time()*1000),'elapsed_seconds':time.monotonic()-start,
                'state':'ASSET_BYTES_COPIED_RELOCATION_PENDING' if failure is None else 'FAILED_PARTIAL_PRESERVED',
                'failure':failure,'completed':completed,'CPU_suite_passed':False,'GPU_G3_passed':False,
                'old_sources_modified':False,'shebang_and_RUNPATH_unchanged':True})
        finally:
            for number,handler in handlers.items():signal.signal(number,handler)
            signal.signal(signal.SIGALRM,previous)
    return {'unit':args.unit,'state':'ASSET_BYTES_COPIED_RELOCATION_PENDING','completed':completed}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('unit',choices=COMPONENTS)
    parser.add_argument('--booking-json',required=True)
    parser.add_argument('--runtime-commit',required=True)
    parser.add_argument('--tool-commit',required=True)
    print(json.dumps(run(parser.parse_args())))
