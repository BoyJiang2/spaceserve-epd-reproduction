"""Read-only static EPD asset inventory after the owned Space GPU phase released."""
import hashlib,json,os,shutil,socket,subprocess,sys,time
from pathlib import Path
ROOT=Path('/local/boyjiang/epd')
SPACE=Path('/local/boyjiang/spaceserve/runs/space-http-20261029')
BOOT='65f52a67-afe4-4919-8646-4694255b48ee'

def main():
    data=json.load(sys.stdin);started=time.monotonic();deadline=started+60;now=int(time.time()*1000)
    if socket.gethostname()!='qjh003' or os.getuid()!=2147 or os.sched_getaffinity(0)!={50} or os.getpriority(os.PRIO_PROCESS,0)!=10:raise ValueError('Executor differs')
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT:raise ValueError('Boot differs')
    proof=data['booking'];expected=dict(id='bk-20261028T0925-0332cf80',node='qjh003',resource_id='h20/qjh003',kind='cpu',user='boyjiang',start_ms=1793192400000,end_ms=1793235600000)
    bookings=[b for b in proof['bookings'] if b.get('id')==expected['id']];resources=[r for r in proof['resources'] if r.get('id')=='h20/qjh003']
    if (proof.get('origin')!='gputime_read_only_api' or proof.get('read_only') is not True or type(proof.get('observed_ms')) is not int or not 0<=now-proof['observed_ms']<=300000
        or len(bookings)!=1 or any(bookings[0].get(k)!=v for k,v in expected.items()) or len(resources)!=1 or resources[0].get('active') is not True
        or now<expected['start_ms'] or now+210000>expected['end_ms']):raise ValueError('Fresh owned CPU booking/full60+30 before08:58 required')
    def check():
        if time.monotonic()>=deadline or int(time.time()*1000)+120000>=expected['end_ms']:raise TimeoutError('Static inventory deadline')
    def real(path):
        for item in (path,*path.parents):
            if item.is_symlink():raise ValueError('Linked managed ancestry')
            if item.exists() and item.is_relative_to('/local/boyjiang') and item.stat().st_uid!=2147:raise ValueError('Foreign project owner')
    real(SPACE)
    capture=SPACE/'evidence/model-attempt1-terminal.json';real(capture)
    if not capture.is_file():raise ValueError('Capture must be an owned regular file')
    raw=capture.read_bytes();state=json.loads(raw)
    if (hashlib.sha256(raw).hexdigest()!=data['space_capture_sha256'] or state.get('phase')!='model' or state.get('released') is not True or state.get('boot_id')!=BOOT
        or state.get('owned_processes')!=[] or state.get('model_code_manifest_sha256')!='0590bc625d2d3dff2d412bd240aeba29e6193016bcccb340fb38a24e654fb8f6'):raise ValueError('Actual current Space model release receipt required')
    owner_path=SPACE/'evidence/mps-owner.json';real(owner_path)
    if not owner_path.is_file():raise ValueError('MPS receipt must be an owned regular file')
    owner=json.loads(owner_path.read_bytes())
    if owner.get('state')!='stopped' or owner.get('pipe')!=str(SPACE/'tmp/mps'):raise ValueError('Space private MPS is not stopped')
    real(ROOT)
    environment=dict(PATH='/usr/bin:/bin',HOME='/nonexistent',LC_ALL='C.UTF-8',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_TERMINAL_PROMPT='0')
    def command(argv):
        check();left=deadline-time.monotonic()
        result=subprocess.run(argv,env=environment,capture_output=True,timeout=min(10,left))
        check();return dict(argv=argv,exit_code=result.returncode,stdout=result.stdout.decode(errors='replace'),stderr=result.stderr.decode(errors='replace'))
    result=dict(scope='static read-only CPU; no Torch/dlopen/GPU or runtime-ready claim',observed_ms=now,host=socket.gethostname(),uid=os.getuid(),boot=BOOT,space_capture_sha256=data['space_capture_sha256'])
    repo=ROOT/'repo';real(repo)
    result['git_head']=command(['/usr/bin/git','-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null','-C',str(repo),'rev-parse','HEAD'])
    envroot=ROOT/'assets/envs/epd';real(envroot)
    cfg=envroot/'pyvenv.cfg';real(cfg)
    if not cfg.is_file():raise ValueError('pyvenv must be an owned regular file')
    result['pyvenv']={}
    for line in cfg.read_text().splitlines():
        key,sep,value=line.partition('=')
        if sep and key.strip() in ('home','version','include-system-site-packages'):result['pyvenv'][key.strip()]=value.strip()
    interpreter=envroot/'bin/python';real(interpreter.parent)
    result['interpreter']=dict(path=str(interpreter),link=os.readlink(interpreter) if interpreter.is_symlink() else None,resolved=str(interpreter.resolve(strict=True)))
    shebangs=[]
    for path in sorted((envroot/'bin').iterdir()):
        check()
        if not path.is_symlink() and path.is_file():
            real(path)
            with path.open('rb') as stream:first=stream.readline(1024)
            if first.startswith(b'#!'):shebangs.append(dict(path=path.relative_to(ROOT).as_posix(),first_line=first.decode(errors='replace').strip()))
    result['shebangs']=shebangs;result['libraries']=[]
    for name in ('assets/build/epd-cuda/libcuda_ipc_utils.so','assets/build/libcuda_ipc_utils.so'):
        path=ROOT/name;real(path);entry=dict(path=name,exists=path.exists())
        if path.exists():
            if not path.is_file():raise ValueError('Library is not a regular file')
            check();entry.update(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            entry['dynamic']=command(['/usr/bin/readelf','-W','-d',str(path)])
            entry['sections']=command(['/usr/bin/readelf','-W','-S',str(path)])
        result['libraries'].append(entry)
    result['dependency_files']={}
    for name in ('torch/lib','nvidia/cuda_runtime/lib'):
        folder=envroot/'lib/python3.10/site-packages'/name;real(folder)
        entries=[]
        for path in sorted(folder.iterdir()) if folder.exists() else []:
            if path.is_symlink():entries.append(dict(name=path.name,link=os.readlink(path)))
            else:
                real(path)
                if path.is_file():entries.append(dict(name=path.name,bytes=path.stat().st_size))
        result['dependency_files'][name]=entries
    result['patchelf_available']=shutil.which('patchelf',path='/usr/bin:/bin')
    check();result['elapsed_seconds']=time.monotonic()-started;print(json.dumps(result),flush=True)

if __name__=='__main__':main()
