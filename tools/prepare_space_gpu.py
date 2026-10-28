"""Two fixed CPU units preparing the approved qjh003 GPU cohort; no GPU launch."""
import base64,hashlib,importlib.util,json,os,secrets,socket,sys,time,types
from pathlib import Path

ROOT=Path('/local/boyjiang/spaceserve')
RUN_ID='space-003-20261029'
RUN=ROOT/'runs'/RUN_ID
COMMIT='7fc3877e4f67cfcaecc6da1b47dbaf60ebdef61c'
BOOT='65f52a67-afe4-4919-8646-4694255b48ee'

def main():
    data=json.load(sys.stdin)
    phase=data['phase']
    if phase not in ('prepare','cpu'):raise ValueError('CPU units only')
    modules=[]
    for name,digest in [('migrate_code_cpu','9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405'),('validate_space_cpu','c9d895c8567fac7f2248c8af63996e6eb4b60080edf493b51002c1c4da4a641b')]:
        raw=base64.b64decode(data[name],validate=True)
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('CPU helper source differs')
        module=types.ModuleType(name);sys.modules[name]=module
        exec(compile(raw,name,'exec'),module.__dict__);modules.append(module)
    migration,helper=modules
    helper.RUN_ID=RUN_ID;helper.RUN=RUN
    started=time.monotonic()
    def check():
        migration.booking(data['booking'],int(time.time()*1000))
        migration.validate_executor()
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT:raise ValueError('Boot changed')
        if time.monotonic()-started>=239:raise TimeoutError('240 second CPU unit')
    check()
    for path,digest in helper.SITE.items():
        if migration.sha(Path(path))!=digest:raise ValueError('Startup file changed')
    site=ROOT/'assets/envs/space/lib/python3.10/site-packages'
    if {str(p) for p in site.glob('*.pth')}!={p for p in helper.SITE if p.startswith(str(site))}:raise ValueError('Unexpected pth')
    evidence=ROOT/'staging/gpu-preparation'
    config=ROOT/'staging/gpu-project.json'
    for path in (evidence,RUN,config.parent,ROOT/'tmp/cpu'):migration.real_ancestry(path)
    if config.is_symlink():raise ValueError('Linked config')
    raw=base64.b64decode(data['config'],validate=True)
    config_sha='45eddf57463c906144afceff5b1a0c1348bdb2738fa4e4ffcb578161ef3cb563'
    if hashlib.sha256(raw).hexdigest()!=config_sha:raise ValueError('Exact approved configuration required')
    if migration.sha(ROOT/'assets/manifest.json')!=helper.ASSETS_SHA:raise ValueError('Asset manifest changed')
    if phase=='prepare':
        if evidence.exists() or RUN.exists() or config.exists():raise ValueError('Existing cohort; no retry')
        evidence.mkdir(mode=0o700)
    else:
        prior=json.loads((evidence/'prepare.terminal.json').read_bytes())
        if (prior['exit_code']!=0 or prior['run_id']!=RUN_ID or prior['boot']!=BOOT or prior['runtime_commit']!=COMMIT
                or prior['config_sha256']!=config_sha or prior['assets_sha256']!=helper.ASSETS_SHA
                or prior['log_sha256']!=migration.sha(evidence/'prepare.log')):raise ValueError('Matching prepare success required')
        frozen=json.loads((RUN/'configs/project.json').read_bytes());original=json.loads(raw)
        generated={'source_manifest_sha256','asset_manifest_sha256'}
        if ({k:v for k,v in frozen.items() if k not in generated}!={k:v for k,v in original.items() if k not in generated}
                or migration.sha(RUN/'configs/asset-inputs.json')!=helper.ASSETS_SHA
                or migration.sha(RUN/'configs/runtime-extension-source-manifest.json')!=frozen['source_manifest_sha256']):raise ValueError('Frozen config/input/source binding changed')
    for path in (ROOT/'tmp/cpu',ROOT/'tmp/cpu-hf',ROOT/'tmp/cpu-torch'):
        migration.real_ancestry(path);path.mkdir(mode=0o700,parents=True,exist_ok=True)
    if any((ROOT/'tmp/cpu').iterdir()):raise ValueError('Nonempty short TMP; preserve')
    if (ROOT/'repo/.git/HEAD').read_text().strip()!=COMMIT:raise ValueError('Runtime HEAD differs')
    spec=importlib.util.spec_from_file_location('asset_inventory',ROOT/'repo/spaceserve/runtime/scripts/stage_cpu.py')
    inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)
    before=json.loads((ROOT/'assets/manifest.json').read_bytes())
    if inventory.inventory(ROOT/'assets')!=before:raise ValueError('Asset inventory changed before unit')
    check()
    claim=evidence/(phase+'.claim.json')
    migration.exclusive_json(claim,dict(pid=os.getpid(),start_ticks=helper.process_records(0)[os.getpid()]['start_ticks'],phase=phase,run_id=RUN_ID,boot=BOOT,started_ms=int(time.time()*1000)))
    environment=helper.child_environment(secrets.token_hex(24))
    if phase=='prepare':
        c=json.loads(raw)
        if c['run_id']!=RUN_ID or c['source_commit']!=COMMIT or c['gpu_devices']!=[0] or c['gpu_uuids']!=['GPU-dd8ab4ed-e34e-4141-ced9-271897da8282']:raise ValueError('Configuration differs')
        with config.open('xb') as stream:stream.write(raw)
    else:config=RUN/'configs/project.json'
    argv=['/usr/bin/python3','-I','-S','-B',str(ROOT/'repo/spaceserve/runtime/entry.py'),phase,'--config',str(config)]
    if phase=='prepare':argv+=['--commit',COMMIT]
    terminal=dict(phase=phase,exit_code=1,run_id=RUN_ID,boot=BOOT,runtime_commit=COMMIT,config_sha256=config_sha,assets_sha256=helper.ASSETS_SHA)
    try:
        with (evidence/(phase+'.log')).open('xb') as stream:
            helper.execute(argv,environment,stream,check,started+239,started+359)
        check()
        if inventory.inventory(ROOT/'assets')!=before:raise ValueError('Assets changed during unit')
        if any((ROOT/'tmp/cpu').iterdir()):raise ValueError('Short TMP residual; preserve')
        check()
        terminal['exit_code']=0
    except BaseException as error:
        terminal.update(error_type=type(error).__name__,error=str(error));raise
    finally:
        terminal['log_sha256']=migration.sha(evidence/(phase+'.log'))
        terminal['finished_ms']=int(time.time()*1000)
        migration.exclusive_json(evidence/(phase+'.terminal.json'),terminal)
    print(json.dumps(terminal),flush=True)

if __name__=='__main__':main()
