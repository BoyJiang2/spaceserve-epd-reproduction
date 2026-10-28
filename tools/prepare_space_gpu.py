"""Fixed deploy/prepare/CPU units for the approved qjh003 GPU cohort; no GPU launch."""
import base64,hashlib,importlib.util,json,os,secrets,socket,sys,time,types
from pathlib import Path

ROOT=Path('/local/boyjiang/spaceserve')
RUN_ID='space-http-20261029'
RUN=ROOT/'runs'/RUN_ID
COMMIT='beadff9c4cc4693cd2ea8675020f757e313659e8'
BOOT='65f52a67-afe4-4919-8646-4694255b48ee'

def main():
    data=json.load(sys.stdin)
    phase=data['phase']
    if phase not in ('deploy','prepare','cpu'):raise ValueError('CPU units only')
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
    evidence=ROOT/'staging/gpu-preparation-http'
    config=ROOT/'staging/gpu-http-project.json'
    for path in (evidence,RUN,config.parent,ROOT/'tmp/cpu'):migration.real_ancestry(path)
    if config.is_symlink():raise ValueError('Linked config')
    raw=base64.b64decode(data['config'],validate=True)
    config_sha='1bdadc8e98a5de137709f8f23b9dd18465c2c5242db391c0589a59dad303193d'
    if hashlib.sha256(raw).hexdigest()!=config_sha:raise ValueError('Exact approved configuration required')
    if migration.sha(ROOT/'assets/manifest.json')!=helper.ASSETS_SHA:raise ValueError('Asset manifest changed')
    if phase=='deploy':
        if evidence.exists() or RUN.exists() or config.exists():raise ValueError('Existing cohort; no retry')
        evidence.mkdir(mode=0o700)
    else:
        previous='deploy' if phase=='prepare' else 'prepare'
        prior=json.loads((evidence/(previous+'.terminal.json')).read_bytes())
        if (prior['exit_code']!=0 or prior['run_id']!=RUN_ID or prior['boot']!=BOOT or prior['runtime_commit']!=COMMIT
                or prior['config_sha256']!=config_sha or prior['assets_sha256']!=helper.ASSETS_SHA
                or prior['log_sha256']!=migration.sha(evidence/(previous+'.log'))):raise ValueError('Matching prepare success required')
        if phase=='prepare' and (RUN.exists() or config.exists()):raise ValueError('Existing prepare; no retry')
        if phase=='cpu':
            frozen=json.loads((RUN/'configs/project.json').read_bytes());original=json.loads(raw)
            generated={'source_manifest_sha256','asset_manifest_sha256'}
            if ({k:v for k,v in frozen.items() if k not in generated}!={k:v for k,v in original.items() if k not in generated}
                    or migration.sha(RUN/'configs/asset-inputs.json')!=helper.ASSETS_SHA
                    or migration.sha(RUN/'configs/runtime-extension-source-manifest.json')!=frozen['source_manifest_sha256']):raise ValueError('Frozen config/input/source binding changed')
    for path in (ROOT/'tmp/cpu',ROOT/'tmp/cpu-hf',ROOT/'tmp/cpu-torch'):
        migration.real_ancestry(path);path.mkdir(mode=0o700,parents=True,exist_ok=True)
    if any((ROOT/'tmp/cpu').iterdir()):raise ValueError('Nonempty short TMP; preserve')
    expected_head='f5ec7a4fc8f2b97ba2c3a68325bc229f86c6d0cb' if phase=='deploy' else COMMIT
    if (ROOT/'repo/.git/HEAD').read_text().strip()!=expected_head:raise ValueError('Runtime HEAD differs')
    spec=importlib.util.spec_from_file_location('asset_inventory',ROOT/'repo/spaceserve/runtime/scripts/stage_cpu.py')
    inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)
    before=json.loads((ROOT/'assets/manifest.json').read_bytes())
    if phase!='deploy' and inventory.inventory(ROOT/'assets')!=before:raise ValueError('Asset inventory changed before unit')
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
            if phase=='deploy':
                old_roots={str(ROOT/'runs/space-003-20261029'),str(ROOT/'runs/space-mask56-20261029'),str(ROOT/'runs/space-pathfix-20261029')}
                if any(row.get('root') in old_roots for row in helper.process_records(0).values()):raise ValueError('Old project process remains; no deployment')
                bundle=ROOT/'staging/space-correctness-connection.bundle'
                if bundle.is_symlink() or bundle.stat().st_uid!=2147 or bundle.stat().st_size!=16111 or migration.sha(bundle)!='fb9a67a0e63294b90ec5b1f0748c10fbed118d7b99dfa446570615ede499ad8f':raise ValueError('Pinned source bundle differs')
                os.environ.clear();os.environ.update(environment)
                git=['git','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','core.excludesFile=/dev/null','-c','core.attributesFile=/dev/null','-C',str(ROOT/'repo')]
                def command(args):
                    check();return migration.command_output(git+args,stream,min(60,max(.1,started+238-time.monotonic())),started+359)
                if command(['status','--porcelain','--untracked-files=all']).strip():raise ValueError('Source repository dirty')
                command(['bundle','verify',str(bundle)])
                if command(['bundle','list-heads',str(bundle)]).decode().strip()!=COMMIT+' HEAD':raise ValueError('Source bundle head differs')
                command(['fetch',str(bundle),'HEAD'])
                if command(['diff','--name-only',expected_head,COMMIT,'--','spaceserve/runtime','reproduction_paths.py']).decode().splitlines()!=['spaceserve/runtime/scripts/correctness_suite.py','spaceserve/runtime/scripts/test_correctness_suite.py']:raise ValueError('Unexpected production change')
                command(['checkout','--detach',COMMIT])
                if command(['rev-parse','HEAD']).decode().strip()!=COMMIT or command(['status','--porcelain','--untracked-files=all']).strip():raise ValueError('Source deployment differs')
                command(['fsck','--full'])
            else:helper.execute(argv,environment,stream,check,started+239,started+359)
        check()
        if phase!='deploy' and inventory.inventory(ROOT/'assets')!=before:raise ValueError('Assets changed during unit')
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
