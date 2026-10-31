"""Reviewed CPU invocation wrapper; real deployment G3 must precede execution."""
import base64,hashlib,json,os,runpy,socket,subprocess,sys,time
from pathlib import Path
p=json.load(sys.stdin);root=Path('/local/boyjiang/epd');repo=root/'repo'
prepared_started=time.monotonic()
def preparation_check():
    if time.monotonic()-prepared_started>=30:raise TimeoutError('CPU invocation preparation bound')
assert os.uname().nodename=='qjh003' and os.getuid()==2147 and os.sched_getaffinity(0)=={50} and os.getpriority(os.PRIO_PROCESS,0)==10
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='65f52a67-afe4-4919-8646-4694255b48ee'
a=p['approval'];review=base64.b64decode(p['review'],validate=True)
assert a['passed'] is True and a['blocking']==0 and a['scope']=='EPD-single-scenario-CPU-smoke-20261031'
assert hashlib.sha256(review).hexdigest()==a['review_sha256']
assert a['commit']==p['commit'] and len(a['commit'])==40
deployment_gate=p['deployment_G3'];deployment_review=base64.b64decode(p['deployment_review'],validate=True)
assert deployment_gate['passed'] is True and deployment_gate['blocking']==0 and deployment_gate['commit']==a['commit']
assert hashlib.sha256(deployment_review).hexdigest()==deployment_gate['review_sha256']==a['deployment_G3_review_sha256']
guard=base64.b64decode(p['booking_guard'],validate=True)
assert hashlib.sha256(guard).hexdigest()==a['booking_guard_sha256']
assert p['control_commit']==a['control_commit'] and len(a['control_commit'])==40
pure={'__name__':'pure_CPU_booking_guard'};exec(compile(guard,'git:'+a['control_commit']+':tools/epd_cpu_evening_20261030.py','exec'),pure)
pure['validate'](p['booking'],int(time.time()*1000),300)
CPU50_LEASE= pure['acquire_cpu50']()
git=['git','--no-optional-locks','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',str(repo)]
assert subprocess.check_output(git+['rev-parse','HEAD'],timeout=10).decode().strip()==a['commit']
assert not subprocess.check_output(git+['status','--porcelain','--untracked-files=all'],timeout=10).strip()
stage=root/'staging/cpu-smoke-deployment-20261031'
manifest=stage/'deployed-files.json';terminal=stage/'terminal.json'
for path,expected in ((manifest,a['deployed_manifest_sha256']),(terminal,a['deployment_terminal_sha256'])):
    assert not path.is_symlink() and path.stat().st_uid==2147 and path.stat().st_size<262144
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
assert json.loads(terminal.read_bytes())['exit_code']==0
for row in json.loads(manifest.read_bytes()):
    preparation_check()
    path=repo/row['path'];assert not path.is_symlink() and path.stat().st_uid==2147
    raw=path.read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
cfg_raw=base64.b64decode(p['config'],validate=True)
assert hashlib.sha256(cfg_raw).hexdigest()==a['config_sha256']
cfg=json.loads(cfg_raw);assert set(cfg)=={'run_id','folder','ray_base','port','ray_package'}
assert cfg['folder']=='/local/boyjiang/epd/runs/cpu-smoke-20261031-once-27180'
assert cfg['ray_base']=='/local/boyjiang/epd/ray/cpu-1031a'
assert cfg['ray_package']=='/local/boyjiang/epd/assets/envs/epd/lib/python3.10/site-packages/ray'
assert cfg['run_id']==a['run_id'] and cfg['port']==a['port']
for path in (root,repo,root/'runs',root/'staging'):
    for item in (path,*path.parents):
        assert not item.is_symlink()
        if item.is_relative_to(root):assert item.is_dir() and item.stat().st_uid==2147
for directory in Path('/proc').iterdir():
    preparation_check()
    if not directory.name.isdigit() or int(directory.name)==os.getpid():continue
    try:
        if directory.stat().st_uid!=2147:continue
        cmd=(directory/'cmdline').read_bytes()
        if b'/local/boyjiang/spaceserve/' in cmd:raise ValueError('Space process active; no CPU handoff')
        if b'/local/boyjiang/epd/' in cmd:raise ValueError('Owned EPD process active before CPU diagnostic')
        try:cwd=(directory/'cwd').resolve(strict=True)
        except PermissionError:
            if b'python' in cmd or b'ray' in cmd:raise ValueError('Candidate cwd unknown')
            continue
        if cwd.is_relative_to(Path('/local/boyjiang/spaceserve')):raise ValueError('Space cwd active')
        if cwd.is_relative_to(root):raise ValueError('Owned EPD cwd active')
    except (FileNotFoundError,ProcessLookupError):continue
# Actual current handoff, not absence of historical Space claim files.
for key in ('handoff','user_instruction','G1','G5'):
    raw=base64.b64decode(p[key],validate=True)
    field={'handoff':'handoff_sha256','user_instruction':'user_instruction_sha256','G1':'G1_sha256','G5':'G5_sha256'}[key]
    assert raw.strip() and hashlib.sha256(raw).hexdigest()==a[field]
handoff=json.loads(base64.b64decode(p['handoff'],validate=True))
assert handoff['host']=='qjh003' and handoff['boot_id']=='65f52a67-afe4-4919-8646-4694255b48ee'
assert type(handoff['observed_ms']) is int and 0<=int(time.time()*1000)-handoff['observed_ms']<=300000
assert handoff['released'] is True and handoff['active_owned_pids']==[] and handoff['unknown']==[]
for field in ('space_terminal_sha256','space_release_sha256','review_sha256'):
    assert isinstance(handoff[field],str) and len(handoff[field])==64 and all(ch in '0123456789abcdef' for ch in handoff[field])
intent=root/'staging/cpu-smoke-20261031-once-27180.intent.json'
assert not intent.is_symlink()
with intent.open('x',encoding='utf8') as saved:
    json.dump(dict(run_id=cfg['run_id'],approval=a,config_sha256=a['config_sha256'],argv_sha256=a['argv_sha256'],booking=p['booking'],handoff=handoff,consumed=True),saved)
    saved.flush();os.fsync(saved.fileno())
with socket.socket() as probe:probe.bind(('127.0.0.2',cfg['port']))
for name in (cfg['folder'],cfg['ray_base']):assert not os.path.lexists(name)
ray_parent=root/'ray'
if ray_parent.exists():assert ray_parent.is_dir() and not ray_parent.is_symlink() and ray_parent.stat().st_uid==2147
else:ray_parent.mkdir(mode=0o700)
folder=Path(cfg['folder']);folder.mkdir(mode=0o700);Path(cfg['ray_base']).mkdir(mode=0o700)
runtime=repo/'epd/runtime';sys.path.insert(0,str(runtime))
from numeric_cpu_receipts import publish
publish(folder/'execution-claim.json',dict(commit=a['commit'],review_sha256=a['review_sha256'],deployment_G3=deployment_gate,
    booking=p['booking'],scope='single-scenario CPU Ray smoke only; no full4 or GPU authorization'))
config=folder/'config.json'
with config.open('xb') as out:out.write(cfg_raw);out.flush();os.fsync(out.fileno())
os.chdir(root)
os.environ.update(EXP_ROOT=str(root),REPRO_RUN_ID=cfg['run_id'],CUDA_VISIBLE_DEVICES='',NVIDIA_VISIBLE_DEVICES='void',
    PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
sys.argv=[str(runtime/'numeric_cpu_lifecycle.py'),'--config',str(config),'--smoke']
preparation_check()
pure['validate'](p['booking'],int(time.time()*1000),180)
runpy.run_path(sys.argv[0],run_name='__main__')
