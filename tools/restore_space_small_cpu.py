"""One exclusive copy of eight exact Space asset pins; no download or model execution."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import sys
import time

import migrate_code_cpu as migration

BOOT='65f52a67-afe4-4919-8646-4694255b48ee'
COMMIT='a3f03b9dd5956db92add454f9b3afd5663f84609'
PREFIX='models/Qwen2-VL-7B-Instruct/'
MEMBERS={'build/libsmctrl.so','build/service_sm_probe.so',*(PREFIX+name for name in (
    'chat_template.json','config.json','configuration.json','generation_config.json','merges.txt','download_manifest.json'))}


def decode_files(rows,pins):
    if len(rows)!=8 or {row['path'] for row in rows}!=MEMBERS:raise ValueError('Exact eight asset names required')
    expected={row['path']:row for row in pins};result=[]
    for row in rows:
        if set(row)!={'path','bytes','sha256','base64'}:raise ValueError('Unexpected asset fields')
        raw=base64.b64decode(row['base64'],validate=True);pin=expected[row['path']]
        if (len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']
                or any(row[key]!=pin[key] for key in ('bytes','sha256'))):raise ValueError('Exact original asset pin differs')
        result.append((row['path'],raw,row['sha256']))
    return result


def write_one(path,raw):
    migration.real_ancestry(path.parent)
    if os.path.lexists(path):raise ValueError('Existing target refused')
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    migration.real_ancestry(path.parent)
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    if hashlib.sha256(path.read_bytes()).digest()!=hashlib.sha256(raw).digest():raise ValueError('Actual target SHA differs')


def main():
    start=time.monotonic();deadline=start+60;payload=sys.stdin.buffer.read(8*1024**2+1)
    if len(payload)>8*1024**2:raise ValueError('8MiB payload budget exceeded')
    data=json.loads(payload)
    if set(data)!={'tool_commit','runtime_commit','booking','files'}:raise ValueError('Unexpected payload fields')
    def check():
        if time.monotonic()>=deadline:raise TimeoutError('60-second small asset unit exhausted')
        migration.booking(data['booking'],int(time.time()*1000))
    check();migration.validate_executor()
    if (Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT
            or data['runtime_commit']!=COMMIT or not re.fullmatch('[0-9a-f]{40}',data['tool_commit'])):
        raise ValueError('Actual boot/designated commits differ')
    root=migration.PARENT/'spaceserve';repo=root/'repo';assets=root/'assets'
    for path in (assets,repo/'.git',root/'staging'):migration.real_ancestry(path)
    if shutil.disk_usage(assets).free<4*1024**3:raise ValueError('At least 4GiB real free space required')
    if (repo/'.git/HEAD').is_symlink() or (repo/'.git/HEAD').read_text().strip()!=COMMIT:raise ValueError('Frozen runtime HEAD differs')
    log=io.BytesIO()
    if migration.command_output(['git','-c','core.fsmonitor=false','-C',str(repo),'status','--porcelain',
            '--untracked-files=all'],log,5,start+180).strip():raise ValueError('Frozen runtime is dirty')
    files=decode_files(data['files'],json.loads((repo/'spaceserve/runtime/configs/asset-content-pins.json').read_bytes()))
    for relative,raw,digest in files:
        migration.real_ancestry((assets/relative).parent)
        if os.path.lexists(assets/relative):raise ValueError('All eight targets must be absent before any write')
    evidence=root/'staging/asset-small-restore';migration.real_ancestry(evidence);evidence.mkdir(mode=0o700)
    def save(name,value):migration.real_ancestry(evidence);migration.exclusive_json(evidence/name,value)
    claim={'tool_commit':data['tool_commit'],'runtime_commit':COMMIT,'booking':data['booking'],
           'host':socket.gethostname(),'uid':os.getuid(),'boot_id':BOOT,'pid':os.getpid(),
           'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],
           'affinity':sorted(os.sched_getaffinity(0)),'nice':os.getpriority(os.PRIO_PROCESS,0),
           'started_ms':int(time.time()*1000),'payload_sha256':hashlib.sha256(payload).hexdigest()}
    save('claim.json',claim)
    with (evidence/'git-validation.log').open('xb') as stream:stream.write(log.getvalue())
    handlers={number:signal.getsignal(number) for number in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
    def stop(number,frame):raise TimeoutError('Small asset unit interrupted '+str(number))
    for number in handlers:signal.signal(number,stop)
    signal.alarm(max(1,int(deadline-time.monotonic())));completed=[];failure=None
    try:
        for relative,raw,digest in files:
            check();write_one(assets/relative,raw)
            completed.append({'path':relative,'bytes':len(raw),'sha256':digest})
        check()
    except BaseException as error:failure=repr(error);raise
    finally:
        signal.alarm(0)
        for number in handlers:signal.signal(number,signal.SIG_IGN)
        try:save('terminal.json',{**claim,'ended_ms':int(time.time()*1000),'elapsed_seconds':time.monotonic()-start,
            'state':'EIGHT_SMALL_ASSETS_COPIED_only' if failure is None else 'FAILED_PARTIAL_PRESERVED',
            'failure':failure,'files':completed,'assets_ready':False,'CPU_STAGED':False,'GPU_requests':0})
        finally:
            for number,handler in handlers.items():signal.signal(number,handler)
    print(json.dumps({'state':'EIGHT_SMALL_ASSETS_COPIED_only','files':completed,'assets_ready':False,'GPU_requests':0}))


if __name__=='__main__':main()
