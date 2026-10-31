"""One reviewed EPD-only CPU Git deployment; no Ray imports or GPU APIs."""
import base64,hashlib,json,os,re,signal,sys,time
from pathlib import Path
p=json.load(sys.stdin);root=Path('/local/boyjiang/epd');repo=root/'repo'
cancelled=set()
previous={n:signal.getsignal(n) for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
for number in previous:signal.signal(number,lambda n,f:cancelled.add(n))
assert os.uname().nodename=='qjh003' and os.getuid()==2147 and os.sched_getaffinity(0)=={50} and os.getpriority(os.PRIO_PROCESS,0)==10
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='65f52a67-afe4-4919-8646-4694255b48ee'
a=p['approval'];review=base64.b64decode(p['review'],validate=True)
assert a['passed'] is True and a['blocking']==0 and a['scope']=='EPD-CPU-full4-deployment-20261031'
assert hashlib.sha256(review).hexdigest()==a['review_sha256']
commit=a['commit'];assert re.fullmatch('[0-9a-f]{40}',commit) and commit==p['commit']
for path in (root,repo,root/'staging'):
    for item in (path,*path.parents):
        assert not item.is_symlink()
        if item.is_relative_to(root):assert item.is_dir() and item.stat().st_uid==2147
guard=base64.b64decode(p['booking_guard'],validate=True)
assert hashlib.sha256(guard).hexdigest()==a['booking_guard_sha256']
module={'__name__':'pure_owned_CPU_booking_guard'};exec(compile(guard,'git:'+commit+':booking-guard','exec'),module)
started=time.monotonic()
CPU50_LEASE= module['acquire_cpu50']()
def check():
    if cancelled:raise RuntimeError('CPU deployment cancelled: '+repr(sorted(cancelled)))
    if time.monotonic()-started>=180:raise TimeoutError('CPU deployment work bound')
    module['validate'](p['booking'],int(time.time()*1000),210)
check()
for path in Path('/proc').iterdir():
    if not path.name.isdigit() or int(path.name)==os.getpid():continue
    try:
        if path.stat().st_uid!=2147:continue
        command=(path/'cmdline').read_bytes()
        if b'/local/boyjiang/epd/' in command:raise ValueError('Another owned EPD process active')
        if b'/local/boyjiang/spaceserve/' in command:raise ValueError('Space process active; no CPU handoff')
        try:cwd=(path/'cwd').resolve(strict=True)
        except PermissionError:
            if b'python' in command or b'ray' in command:raise ValueError('Owned candidate cwd unknown')
            continue
        if cwd.is_relative_to(root):raise ValueError('Another EPD cwd active')
        if cwd.is_relative_to(Path('/local/boyjiang/spaceserve')):raise ValueError('Space cwd active')
    except (FileNotFoundError,ProcessLookupError):continue
helper=base64.b64decode(p['command_helper'],validate=True)
assert hashlib.sha256(helper).hexdigest()==a['command_helper_sha256']
commands={'__name__':'published_CPU_command_process_supervisor'}
exec(compile(helper,'git:'+commit+':tools/migrate_code_cpu.py','exec'),commands)
import subprocess
git=['git','--no-optional-locks','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',str(repo)]
assert subprocess.check_output(git+['rev-parse','HEAD'],timeout=10).decode().strip()=='459e2a8892e872043632ff2d66ffef597aec3e72'
assert not subprocess.check_output(git+['status','--porcelain','--untracked-files=all'],timeout=10).strip()
handoff_raw=base64.b64decode(p['handoff'],validate=True)
assert hashlib.sha256(handoff_raw).hexdigest()==a['handoff_sha256']
handoff=json.loads(handoff_raw)
assert handoff['host']=='qjh003' and handoff['boot_id']=='65f52a67-afe4-4919-8646-4694255b48ee'
assert type(handoff['observed_ms']) is int and 0<=int(time.time()*1000)-handoff['observed_ms']<=300000
assert handoff['released'] is True and handoff['active_owned_pids']==[] and handoff['unknown']==[]
for field in ('space_terminal_sha256','space_release_sha256','review_sha256'):
    assert isinstance(handoff[field],str) and re.fullmatch('[a-f0-9]{64}',handoff[field])
raw=base64.b64decode(p['bundle'],validate=True)
assert len(raw)==a['bundle_bytes'] and hashlib.sha256(raw).hexdigest()==a['bundle_sha256']
stage=root/'staging/cpu-full4-deployment-20261031';assert not stage.exists() and not stage.is_symlink()
stage.mkdir(mode=0o700)
def save(name,value):
    with (stage/name).open('x',encoding='utf8') as out:json.dump(value,out,indent=2);out.flush();os.fsync(out.fileno())
save('claim.json',dict(commit=commit,booking=p['booking'],review_sha256=a['review_sha256'],started_ms=int(time.time()*1000),scope='EPD-only CPU Git deployment; no Ray/GPU'))
bundle=stage/'source.bundle'
with bundle.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
state=dict(exit_code=1,commit=commit,prior_commit='459e2a8892e872043632ff2d66ffef597aec3e72',GPU_requests=0,Ray_started=False)
signal.alarm(max(1,int(180-(time.monotonic()-started))))
try:
    with (stage/'commands.log').open('xb') as log:
        def run(*args):
            check()
            output=commands['command_output'](git+list(args),log,min(60,180-(time.monotonic()-started)),started+210)
            check();return output
        run('bundle','verify',str(bundle))
        run('fetch','--no-tags',str(bundle),commit)
        run('sparse-checkout','add','tools','epd/migration')
        run('checkout','--detach',commit)
        assert run('rev-parse','HEAD').decode().strip()==commit
        assert not run('status','--porcelain','--untracked-files=all').strip()
        rows=[]
        for record in run('ls-tree','-rz',commit,'epd/runtime','tools','epd/migration/qjh003-cpu-evening-20261030.json').split(b'\0'):
            check()
            if not record:continue
            info,name=record.split(b'\t',1);mode,kind,blob=info.decode().split();name=name.decode();path=repo/name
            assert mode in ('100644','100755') and kind=='blob'
            for item in (path,*path.parents):
                assert not item.is_symlink()
                if item.is_relative_to(repo):assert item.stat().st_uid==2147
            data=path.read_bytes()
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==blob
            rows.append(dict(path=name,blob=blob,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        assert rows and any(row['path']=='epd/runtime/numeric_cpu_lifecycle.py' for row in rows)
        save('deployed-files.json',rows)
        assert not run('status','--porcelain','--untracked-files=all').strip()
        state.update(exit_code=0,tree=run('rev-parse','HEAD^{tree}').decode().strip(),checked_source_files=len(rows),runtime_files=sum(x['path'].startswith('epd/runtime/') for x in rows),tools_files=sum(x['path'].startswith('tools/') for x in rows),CPU_tests_executed=0)
except BaseException as error:
    state['error']=repr(error);raise
finally:
    signal.alarm(0)
    state.update(finished_ms=int(time.time()*1000),elapsed_seconds=time.monotonic()-started)
    save('terminal.json',state);print(json.dumps(state),flush=True)
    for number,handler in previous.items():signal.signal(number,handler)
