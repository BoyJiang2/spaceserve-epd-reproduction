"""Inspect fixed EPD startup assets before any separately approved relocation."""
import hashlib,json,os,socket,sys,time
from pathlib import Path
ROOT=Path('/local/boyjiang/epd')
BOOT='65f52a67-afe4-4919-8646-4694255b48ee'

def main():
    data=json.load(sys.stdin)
    if data.get('phase') in ('apply','verify'):return relocate(data)
    now=int(time.time()*1000);started=time.monotonic()
    if data.get('phase')!='inspect':raise ValueError('Only read-only inspection implemented')
    if socket.gethostname()!='qjh003' or os.getuid()!=2147 or os.sched_getaffinity(0)!={50} or os.getpriority(os.PRIO_PROCESS,0)!=10:raise ValueError('Executor differs')
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT:raise ValueError('Boot differs')
    proof=data['booking'];expected=dict(id='bk-20261029T0057-e2efd603',node='qjh003',resource_id='h20/qjh003',kind='cpu',user='boyjiang',start_ms=1793235600000,end_ms=1793239200000)
    tickets=[b for b in proof['bookings'] if b.get('id')==expected['id']];resources=[r for r in proof['resources'] if r.get('id')=='h20/qjh003']
    if (proof.get('origin')!='gputime_read_only_api' or proof.get('read_only') is not True or type(proof.get('observed_ms')) is not int or not 0<=now-proof['observed_ms']<=300000 or len(tickets)!=1 or tickets[0]!=expected or len(resources)!=1 or resources[0].get('active') is not True or now<expected['start_ms'] or now+210000>expected['end_ms']):raise ValueError('Fresh exact owned CPU slot/full60+30 before09:58 required')
    def check():
        if time.monotonic()-started>=60 or int(time.time()*1000)+120000>=expected['end_ms']:raise TimeoutError('Inspection deadline')
    def real(path):
        for item in (path,*path.parents):
            if item.is_symlink():raise ValueError('Managed symlink refused')
            if item.exists() and item.is_relative_to('/local/boyjiang') and item.stat().st_uid!=2147:raise ValueError('Foreign managed owner')
    def read(path,text=False):
        check();real(path)
        if not path.is_file() or path.stat().st_size>65536:raise ValueError('Expected small owned regular startup file')
        raw=path.read_bytes();row=dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        if text:row['text']=raw.decode('utf8')
        return row
    real(ROOT);env=ROOT/'assets/envs/epd';site=env/'lib/python3.10/site-packages';real(site);binpath=env/'bin';real(binpath)
    files=[read(env/'pyvenv.cfg',True)]
    for path in sorted(site.glob('*.pth')):files.append(read(path,True))
    for name in ('sitecustomize.py','usercustomize.py'):
        path=site/name;real(path)
        if path.exists():files.append(read(path,True))
    for path in sorted(binpath.iterdir()):
        check()
        if path.is_symlink():continue
        real(path)
        if path.is_file():
            with path.open('rb') as stream:first=stream.readline(1024)
            if path.name.startswith('activate'):files.append(read(path,True))
            elif first.startswith(b'#!'):files.append(read(path,False)|dict(first_line=first.decode('utf8').strip()))
    links=[]
    for name in ('python','python3','python3.10'):
        path=binpath/name;real(path.parent)
        if path.is_symlink():links.append(dict(path=path.relative_to(ROOT).as_posix(),link=os.readlink(path),resolved=str(path.resolve(strict=True))))
        elif path.exists():links.append(read(path,False))
    check();print(json.dumps(dict(phase='inspect',scope='CPU static only; no imports from relocated environment, no GPU or writes',host=socket.gethostname(),uid=os.getuid(),boot=BOOT,observed_ms=now,files=files,python_links=links,elapsed_seconds=time.monotonic()-started)),flush=True)


OLD_ENV=b'/local/boyjiang/spaceserve-epd-qjh003-20261023/envs/epd'
NEW_ENV=b'/local/boyjiang/epd/assets/envs/epd'
CONFIG_SHA='afab6795c25600d7fdfa3de215e30ab97ae367d81deb3897cc2a7f29f3e09a66'

def rewrite(raw,kind):
    if kind=='console':
        prefix=b'#!'+OLD_ENV+b'/bin/python'
        if not (raw.startswith(prefix+b'\n') or raw.startswith(prefix+b'\r\n')):raise ValueError('Unexpected console interpreter')
        return b'#!'+NEW_ENV+b'/bin/python'+raw[len(prefix):]
    if kind=='activation':
        if raw.count(OLD_ENV)!=1:raise ValueError('Activation must contain exactly one old environment prefix')
        return raw.replace(OLD_ENV,NEW_ENV)
    raise ValueError('Unapproved rewrite kind')

def known_startup(site):
    if {p.name for p in site.glob('*.pth')}!={'distutils-precedence.pth'}:raise ValueError('Unexpected startup code')
    for name in ('sitecustomize.py','usercustomize.py'):
        path=site/name
        if path.exists() or path.is_symlink():raise ValueError('Unexpected startup customization')

def cpu_permission(proof,now,seconds,end):
    if (proof.get('origin')!='gputime_read_only_api' or proof.get('read_only') is not True or type(proof.get('observed_ms')) is not int or not 0<=now-proof['observed_ms']<=300000 or now+int(seconds*1000)+120000>end):raise ValueError('Fresh actual CPU availability/full cleanup reserve required')
    resources=[r for r in proof['resources'] if r.get('id')=='h20/qjh003']
    if len(resources)!=1 or resources[0].get('node')!='qjh003' or resources[0].get('active') is not True:raise ValueError('Resource differs')
    for row in proof['bookings']:
        if row.get('resource_id')!='h20/qjh003' or row.get('kind')=='gpu':continue
        if row.get('kind') not in (None,'cpu'):raise ValueError('Unknown resource lane')
        if type(row.get('start_ms')) is not int or type(row.get('end_ms')) is not int:raise ValueError('Unknown CPU interval')
        if row['start_ms']<now+int(seconds*1000) and row['end_ms']>now and row.get('user')!='boyjiang':raise ValueError('Conflicting other CPU/whole-node booking')

def terminal_report(stage,phase,state,owned_stage):
    failure=None
    try:
        if owned_stage:
            with (stage/(phase+'-terminal.json')).open('x',encoding='utf8') as f:json.dump(state,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    except BaseException as error:
        state.update(exit_code=1,terminal_write_error=type(error).__name__+': '+str(error));failure=error
    print(json.dumps(state),flush=True)
    return failure

def relocate(data):
    import base64,resource,signal,subprocess
    phase=data['phase'];started=time.monotonic();now=int(time.time()*1000)
    if socket.gethostname()!='qjh003' or os.getuid()!=2147 or os.sched_getaffinity(0)!={50} or os.getpriority(os.PRIO_PROCESS,0)!=10 or Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT:raise ValueError('Executor or boot differs')
    raw_config=base64.b64decode(data['config'],validate=True)
    if hashlib.sha256(raw_config).hexdigest()!=CONFIG_SHA:raise ValueError('Exact reviewed relocation allowlist required')
    cfg=json.loads(raw_config);permission=cfg['cpu_permission'];end=permission['valid_until_ms']
    if permission!={'origin':'direct_user_instruction','quote':'虽然后面的cpu没有预约 但是你可以随便用','valid_until_ms':1793246400000}:raise ValueError('Direct user CPU scope differs')
    cpu_permission(data['booking'],now,240 if phase=='apply' else 90,end)
    if cfg['root']!=str(ROOT) or cfg['boot']!=BOOT or len(cfg['files'])!=61 or len({r['path'] for r in cfg['files']})!=61:raise ValueError('Pinned root/allowlist differs')
    limit=120 if phase=='apply' else 60;stage=ROOT/cfg['stage'];journal=[]
    def check():
        if time.monotonic()-started>=limit or int(time.time()*1000)+120000>=end:raise TimeoutError('Bounded CPU unit exhausted')
    def real(path):
        for item in (path,*path.parents):
            if item.is_symlink():raise ValueError('Managed symlink refused')
            if item.exists() and item.is_relative_to('/local/boyjiang') and item.stat().st_uid!=2147:raise ValueError('Foreign managed owner')
    def digest(path):
        check();real(path)
        if not path.is_file():raise ValueError('Owned regular asset required')
        return hashlib.sha256(path.read_bytes()).hexdigest()
    def save(path,value):
        check();real(path.parent)
        with path.open('x',encoding='utf8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    def command(argv):
        check();r=subprocess.run(argv,cwd=str(stage),env=dict(PATH='/usr/bin:/bin',HOME='/nonexistent',LC_ALL='C.UTF-8',CUDA_VISIBLE_DEVICES='',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=min(10,limit-(time.monotonic()-started)))
        row=dict(argv=argv,exit_code=r.returncode,stdout=r.stdout.decode(errors='replace'),stderr=r.stderr.decode(errors='replace'));journal.append(row)
        if r.returncode:raise RuntimeError('Static ELF tool failed')
        return row['stdout']
    real(ROOT);real(stage)
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit() or int(folder.name)==os.getpid():continue
        try:
            if folder.stat().st_uid!=2147:continue
            commandline=(folder/'cmdline').read_bytes().replace(b'\0',b' ')
            if b'/local/boyjiang/epd/' in commandline or b'/local/boyjiang/spaceserve/runs/' in commandline:raise ValueError('Owned project process active; refuse asset mutation')
            try:cwd=os.readlink(folder/'cwd')
            except PermissionError:
                if b'python' in commandline or b'ray' in commandline:raise ValueError('Candidate process cwd unknown')
                continue
            if cwd.startswith(str(ROOT)+'/'):raise ValueError('Project cwd active')
        except (FileNotFoundError,ProcessLookupError):continue
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    original=ROOT/cfg['original_library']['path'];flat=ROOT/cfg['flat_library']
    real(original)
    if original.stat().st_size!=cfg['original_library']['bytes'] or digest(original)!=cfg['original_library']['sha256']:raise ValueError('Original nested IPC changed')
    for row in cfg['files']:
        real(ROOT/row['path'])
    for row in cfg['python_links']:
        path=ROOT/row['path'];real(path.parent)
        if not path.is_symlink() or os.readlink(path)!=row['link'] or str(path.resolve(strict=True))!=row['resolved']:raise ValueError('Interpreter link differs')
    pth=ROOT/'assets/envs/epd/lib/python3.10/site-packages';real(pth)
    known_startup(pth)
    if phase=='apply':
        if stage.exists() or flat.exists() or flat.is_symlink():raise ValueError('Existing relocation or flat library; preserve, no retry')
        for row in cfg['files']:
            path=ROOT/row['path']
            if path.stat().st_size!=row['bytes'] or digest(path)!=row['sha256']:raise ValueError('Original startup pin differs')

    else:
        prior_path=stage/'apply-terminal.json';real(prior_path)
        if not prior_path.is_file():raise ValueError('Owned regular apply receipt required')
        marker=stage/'verify-terminal.json';real(marker)
        prior=json.loads(prior_path.read_bytes())
        if prior['exit_code']!=0 or prior['config_sha256']!=CONFIG_SHA or marker.exists() or marker.is_symlink():raise ValueError('Matching one successful apply required; no verify retry')
    state=dict(phase=phase,config_sha256=CONFIG_SHA,boot=BOOT,exit_code=1,started_ms=now,changes=[],scope='static CPU relocation only; no dlopen/Torch/GPU or runtime-ready claim')
    owned_stage=phase=='verify'
    previous={n:signal.getsignal(n) for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
    def interrupted(n,frame):raise TimeoutError('Controlled CPU interruption')
    for n in previous:signal.signal(n,interrupted)
    signal.setitimer(signal.ITIMER_REAL,limit)
    try:
        if phase=='apply':
            old_mask=signal.pthread_sigmask(signal.SIG_BLOCK,set(previous))
            try:
                stage.mkdir(mode=0o700);owned_stage=True
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,old_mask)
            save(stage/'claim.json',dict(pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],boot=BOOT,phase=phase,config_sha256=CONFIG_SHA,started_ms=now,cpu_permission=permission,availability=data['booking'],reservation_claimed=False))
            (stage/'before').mkdir(mode=0o700)
            for row in cfg['files']:
                if row['kind']=='unchanged':continue
                path=ROOT/row['path'];backup=stage/'before'/row['path'];backup.parent.mkdir(parents=True,exist_ok=True);real(backup.parent)
                with backup.open('xb') as f:f.write(path.read_bytes());f.flush();os.fsync(f.fileno())
                if digest(backup)!=row['sha256']:raise ValueError('Backup pin differs')
            for folder in cfg['rpath']:real(Path(folder))
            for folder,name in ((cfg['rpath'][0],'libc10.so'),(cfg['rpath'][0],'libtorch_cpu.so'),(cfg['rpath'][0],'libc10_cuda.so'),(cfg['rpath'][1],'libnccl.so.2'),(cfg['rpath'][2],'libcudart.so.12')):
                path=Path(folder)/name;real(path)
                if not path.is_file():raise ValueError('Required relocated dependency missing')
            temporary=flat.with_name('.libcuda_ipc_utils.relocation-tmp.so');real(temporary)
            with temporary.open('xb') as f:f.write(original.read_bytes());f.flush();os.fsync(f.fileno())
            os.chmod(temporary,original.stat().st_mode&0o777)
            old_dynamic=command(['/usr/bin/readelf','-W','-d',str(original)])
            command(['/usr/bin/patchelf','--set-rpath',':'.join(cfg['rpath']),str(temporary)])
            if command(['/usr/bin/patchelf','--print-rpath',str(temporary)]).strip()!=':'.join(cfg['rpath']):raise ValueError('New RUNPATH differs')
            os.link(temporary,flat);temporary.unlink()
            state['flat_sha256']=digest(flat);state['original_dynamic']=old_dynamic
            for row in cfg['files']:
                path=ROOT/row['path']
                if row['kind']=='unchanged':continue
                backup=stage/'before'/row['path'];before=backup.read_bytes();after=rewrite(before,row['kind'])
                if digest(path)!=row['sha256']:raise ValueError('Startup changed before atomic edit')
                temporary=path.with_name('.'+path.name+'.relocation-tmp');real(temporary)
                with temporary.open('xb') as f:f.write(after);f.flush();os.fsync(f.fileno())
                os.chmod(temporary,path.stat().st_mode&0o777);os.replace(temporary,path)
                actual=digest(path)
                if actual!=hashlib.sha256(after).hexdigest():raise ValueError('Atomic rewrite differs')
                state['changes'].append(dict(path=row['path'],before_sha256=row['sha256'],after_sha256=actual,bytes=len(after),kind=row['kind']))
        else:
            changes={row['path']:row for row in prior['changes']}
            if len(changes)!=56 or digest(flat)!=prior['flat_sha256']:raise ValueError('Incomplete prior apply or flat changed')
            for row in cfg['files']:
                path=ROOT/row['path'];expected=row['sha256']
                if row['kind']!='unchanged':
                    backup=stage/'before'/row['path']
                    if digest(backup)!=row['sha256']:raise ValueError('Original backup changed')
                    expected=hashlib.sha256(rewrite(backup.read_bytes(),row['kind'])).hexdigest()
                    if expected!=changes[row['path']]['after_sha256']:raise ValueError('Recorded transformation differs')
                if digest(path)!=expected:raise ValueError('Final startup pin differs')
            if command(['/usr/bin/patchelf','--print-rpath',str(flat)]).strip()!=':'.join(cfg['rpath']):raise ValueError('Final RUNPATH differs')
            state['flat_sha256']=digest(flat);state['startup_files_verified']=61;state['rewrites_verified']=56
        state['flat_dynamic']=command(['/usr/bin/readelf','-W','-d',str(flat)])
        import re
        before_dynamic=state.get('original_dynamic') if phase=='apply' else prior['original_dynamic']
        if re.findall(r'\(NEEDED\).*?\[([^]]+)\]',before_dynamic)!=re.findall(r'\(NEEDED\).*?\[([^]]+)\]',state['flat_dynamic']):raise ValueError('ELF dependencies changed')
        if digest(original)!=cfg['original_library']['sha256']:raise ValueError('Original nested library changed')
        state['original_nested_unchanged']=True;state['exit_code']=0
    except BaseException as error:state.update(error_type=type(error).__name__,error=str(error));raise
    finally:
        original_failure=sys.exc_info()[0] is not None
        signal.setitimer(signal.ITIMER_REAL,0)
        for n in previous:signal.signal(n,signal.SIG_IGN)
        state.update(finished_ms=int(time.time()*1000),elapsed_seconds=time.monotonic()-started,commands=journal)
        try:terminal_failure=terminal_report(stage,phase,state,owned_stage)
        finally:
            for n,h in previous.items():signal.signal(n,h)
        if terminal_failure is not None and not original_failure:raise RuntimeError('CPU terminal persistence failed') from terminal_failure

if __name__=='__main__':main()
