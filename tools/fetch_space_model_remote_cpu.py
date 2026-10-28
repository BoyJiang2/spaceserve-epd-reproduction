"""One pinned missing Qwen file per CPU unit. No retries, model imports or GPU APIs."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import time
import urllib.request
from urllib.parse import urlsplit

import migrate_code_cpu as migration

BOOT='65f52a67-afe4-4919-8646-4694255b48ee'
COMMIT='a3f03b9dd5956db92add454f9b3afd5663f84609'
METADATA_SHA='1bb637d5a3ca359e9e1cd4656012ead4fa3257878fa4f95d56b2c1847dec39e5'
PREFIX='models/Qwen2-VL-7B-Instruct/'
OWNER=2147


def public_location(url):
    parsed=urlsplit(url)
    return {'scheme':parsed.scheme,'host':parsed.hostname,
            'path_sha256':hashlib.sha256(parsed.path.encode()).hexdigest()}


class SecureRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self,check,trace):self.check=check;self.trace=trace;self.hops=0
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        req.timeout=min(30,self.check());self.hops+=1;parsed=urlsplit(newurl)
        if self.hops>3 or parsed.scheme!='https' or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError('At most three HTTPS redirects without userinfo allowed')
        self.trace.append(public_location(newurl))
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def identity(path):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=OWNER:raise ValueError('Unknown download file owner/type')
    return (info.st_dev,info.st_ino,info.st_uid,info.st_size,info.st_mtime_ns)


def transfer(row,target,check,state,opener=None):
    partial=target.with_name(target.name+'.partial');migration.real_ancestry(target.parent)
    if os.path.lexists(target) or os.path.lexists(partial):raise ValueError('Existing target/partial: inspect; no repeat')
    check();state.update(phase='connect',received_bytes=0,published=False,partial_removed=False,redirects=[])
    opener=opener or urllib.request.build_opener(SecureRedirect(check,state['redirects']))
    url='https://modelscope.cn/models/Qwen/Qwen2-VL-7B-Instruct/resolve/'+row['source']['Revision']+'/'+row['name']
    state['source_url']=url
    value=hashlib.sha256()
    with partial.open('xb') as stream:
        with opener.open(urllib.request.Request(url,headers={'User-Agent':'spaceserve-epd-reproduction'}),
                         timeout=min(30,check())) as response:
            check();state['http_status']=response.status;state['effective_location']=public_location(response.geturl())
            if response.status!=200:raise ValueError('Full HTTP200 response required; no Range or resume')
            length=response.headers.get('Content-Length')
            if length is not None and int(length)!=row['bytes']:raise ValueError('Response Content-Length differs')
            state['phase']='read'
            while True:
                # CPython 3.10 HTTPResponse uses BufferedReader -> SocketIO -> SSLSocket.
                left=check()
                if response.fp is not None:response.fp.raw._sock.settimeout(min(30,left))
                block=response.read(4*1024**2);check()
                if not block:break
                if state['received_bytes']+len(block)>row['bytes']:raise ValueError('Response exceeds pinned size')
                check();stream.write(block);value.update(block);state['received_bytes']+=len(block)
            stream.flush();os.fsync(stream.fileno())
    state['stream_sha256']=value.hexdigest();state['phase']='verify'
    if state['received_bytes']!=row['bytes'] or value.hexdigest()!=row['sha256']:
        raise ValueError('Actual complete response bytes/SHA differ')
    saved=identity(partial);check();migration.real_ancestry(target.parent)
    state['phase']='publish';os.link(partial,target,follow_symlinks=False);state['published']=True
    if identity(partial)!=saved or identity(target)!=saved:raise ValueError('Download inode replaced')
    digest=hashlib.sha256()
    with target.open('rb') as stream:
        while block:=stream.read(4*1024**2):check();digest.update(block)
    state['target_sha256']=digest.hexdigest()
    if digest.hexdigest()!=row['sha256'] or identity(partial)!=saved or identity(target)!=saved:
        raise ValueError('Published bytes/inode changed')
    check();state['phase']='cleanup_verified_temporary_name';partial.unlink();state['partial_removed']=True
    check();state['phase']='complete'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True)
    parser.add_argument('--booking-json',required=True);parser.add_argument('--tool-commit',required=True)
    args=parser.parse_args();start=time.monotonic();deadline=start+240;proof=json.loads(args.booking_json)
    def check():
        left=deadline-time.monotonic()
        if left<=0:raise TimeoutError('240-second model file budget exhausted')
        migration.booking(proof,int(time.time()*1000));return left
    check();migration.validate_executor()
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT or not re.fullmatch('[0-9a-f]{40}',args.tool_commit):
        raise ValueError('Actual boot/designated tool commit differs')
    root=migration.PARENT/'spaceserve';repo=root/'repo';assets=root/'assets';model=assets/PREFIX
    for path in (repo/'.git',model,root/'staging'):migration.real_ancestry(path)
    if (repo/'.git/HEAD').is_symlink() or (repo/'.git/HEAD').read_text().strip()!=COMMIT:raise ValueError('Frozen HEAD differs')
    log=io.BytesIO()
    if migration.command_output(['git','-c','core.fsmonitor=false','-C',str(repo),'status','--porcelain',
            '--untracked-files=all'],log,5,start+360).strip():raise ValueError('Frozen runtime is dirty')
    metadata=model/'download_manifest.json';pins_file=repo/'spaceserve/runtime/configs/asset-content-pins.json'
    metadata_before=migration.sha(metadata);pins_before=migration.sha(pins_file)
    if metadata.is_symlink() or metadata_before!=METADATA_SHA:raise ValueError('Exact original model metadata required')
    manifest=json.loads(metadata.read_bytes());pins=json.loads(pins_file.read_bytes())
    expected={r['path'][len(PREFIX):]:r for r in pins if r['path'].startswith(PREFIX) and r['path']!=PREFIX+'download_manifest.json'}
    rows=manifest['files']
    if (manifest['repo']!='Qwen/Qwen2-VL-7B-Instruct' or manifest['endpoint']!='https://modelscope.cn'
            or len(rows)!=15 or len({r['name'] for r in rows})!=15 or {r['name'] for r in rows}!=set(expected)):
        raise ValueError('Exact fifteen original model entries required')
    for row in rows:
        if (Path(row['name']).name!=row['name'] or not re.fullmatch('[0-9a-f]{40}',row['source']['Revision'])
                or any(row[key]!=expected[row['name']][key] for key in ('bytes','sha256'))):raise ValueError('Unpinned model source')
    row=next(r for r in rows if r['name']==args.name);target=model/row['name'];partial=target.with_name(target.name+'.partial')
    if os.path.lexists(target) or os.path.lexists(partial):raise ValueError('Existing target/partial; do not repeat')
    if shutil.disk_usage(model).free<sum(r['bytes'] for r in rows)+8*1024**3:raise ValueError('Insufficient model space budget')
    evidence=root/'staging/model-fetch';migration.real_ancestry(evidence);evidence.mkdir(mode=0o700,exist_ok=True)
    def save(suffix,value):migration.real_ancestry(evidence);migration.exclusive_json(evidence/(row['name']+suffix),value)
    claim={'name':row['name'],'expected_bytes':row['bytes'],'expected_sha256':row['sha256'],
           'tool_commit':args.tool_commit,'runtime_commit':COMMIT,'metadata_sha256':metadata_before,'pins_sha256':pins_before,
           'host':socket.gethostname(),'uid':os.getuid(),'boot_id':BOOT,'booking':proof,
           'pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],
           'affinity':sorted(os.sched_getaffinity(0)),'nice':os.getpriority(os.PRIO_PROCESS,0),'started_ms':int(time.time()*1000)}
    save('.claim.json',claim)
    with (evidence/(row['name']+'.git.log')).open('xb') as stream:stream.write(log.getvalue())
    handlers={n:signal.getsignal(n) for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
    def stop(number,frame):raise TimeoutError('Model acquisition interrupted')
    for number in handlers:signal.signal(number,stop)
    signal.alarm(max(1,int(deadline-time.monotonic())));state={};failure=None
    try:
        transfer(row,target,check,state)
        if migration.sha(metadata)!=metadata_before or migration.sha(pins_file)!=pins_before:raise ValueError('Frozen metadata/pins changed')
        check()
    except BaseException as error:
        # External exception text can contain signed URLs; persist class/code/phase only.
        failure={'type':type(error).__name__,'http_status':getattr(error,'code',None)}
    finally:
        signal.alarm(0)
        for number in handlers:signal.signal(number,signal.SIG_IGN)
        try:save('.terminal.json',{**claim,**state,'ended_ms':int(time.time()*1000),'elapsed_seconds':time.monotonic()-start,
            'failure':failure,'state':'MODEL_FILE_VERIFIED_only' if failure is None else 'FAILED_ACTUAL_FILES_PRESERVED',
            'final_exists':os.path.lexists(target),'partial_exists':os.path.lexists(partial),'automatic_retries':0,
            'assets_ready':False,'CPU_STAGED':False,'GPU_requests':0})
        finally:
            for number,handler in handlers.items():signal.signal(number,handler)
    if failure is not None:raise RuntimeError('Pinned acquisition failed in '+state.get('phase','preflight')+' ('+failure['type']+')') from None
    print(json.dumps({'name':row['name'],'state':'MODEL_FILE_VERIFIED_only','bytes':row['bytes'],'sha256':row['sha256'],'GPU_requests':0}))


if __name__=='__main__':main()
