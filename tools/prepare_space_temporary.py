"""Bounded CPU-only deploy/prepare/suite for the direct idle-GPU2 grant."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
import types


ROOT=Path('/local/boyjiang/spaceserve')
RUN_ID='space-idle2-20261029'
RUN=ROOT/'runs'/RUN_ID
BOOT='65f52a67-afe4-4919-8646-4694255b48ee'
UUID='GPU-c005197e-747d-2dc8-b77b-b123b41efd75'
QUOTE='如果gpu暂时没人用 你可以先暂时用一下'
FAILED_DEPLOY_SHA='b4dda733def170f1d7a840e4ee9160648b7f02c5dedaccac96c3972b78097584'
ORIGINAL_CONFIG_SHA='ebe8ae33a2bebd80da88328ef268900c459853bbb913857a311a88059acd1c8f'


def validate_config(raw,commit,user):
    config=json.loads(raw)
    grant=config.get('temporary_gpu_use',{})
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Exact published commit required')
    expected=dict(schema='reproduction-project-v1',project='spaceserve',project_root=ROOT.as_posix(),state='approved_scope',
        host='qjh003',uid=2147,run_id=RUN_ID,gpu_devices=[2],gpu_uuids=[UUID],allowed_actions=['numeric','model'],
        booking=None,source_commit=commit,source_manifest_sha256=None,cuda_home='/usr/local/cuda-12.8',mask_off=56,
        mask_compatibility_proof_sha256='f8cff8a12b7a613d2ccb1241f8126945fef5935425c13f1851ca961957b89aa4',
        correctness_http_connection='new_connection_no_retry',workload_cpu_affinity=list(range(90)),workload_numa_node=0,
        temporary_gpu_use=grant)
    if (config!=expected or any(type(cpu) is not int for cpu in config['workload_cpu_affinity'])
            or set(grant)!={'schema','start_ms','end_ms','boot_id','user_sha256'}
            or grant['schema']!='temporary-idle-single-gpu-v1' or grant['boot_id']!=BOOT
            or any(type(grant[k]) is not int for k in ('start_ms','end_ms'))
            or not 0<grant['end_ms']-grant['start_ms']<=3600000
            or grant['user_sha256']!=hashlib.sha256(user).hexdigest()
            or user.decode('utf8').strip()!=QUOTE):
        raise ValueError('Exact direct-user GPU2/CPU90 preflight configuration required')
    return config


def recovery_bundle(evidence,config,data):
    prior=evidence/'deploy.terminal.json';log=evidence/'deploy.log'
    for path in (prior,log):
        if path.is_symlink() or not path.is_file() or path.stat().st_uid!=os.getuid():raise ValueError('Original owned failure required')
    raw=prior.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=FAILED_DEPLOY_SHA:raise ValueError('Exact original failed deployment required')
    failed=json.loads(raw)
    if (failed['exit_code']!=1 or failed.get('error_type')!='TimeoutExpired'
            or hashlib.sha256(log.read_bytes()).hexdigest()!=failed['log_sha256']):raise ValueError('Original network failure/log differs')
    original=base64.b64decode(data['prior_config'],validate=True)
    if hashlib.sha256(original).hexdigest()!=ORIGINAL_CONFIG_SHA:raise ValueError('Original configuration bytes required')
    previous=json.loads(original)
    if {k:v for k,v in config.items() if k!='source_commit'}!={k:v for k,v in previous.items() if k!='source_commit'}:
        raise ValueError('Recovery may only update source version; never extend the window')
    bundle=ROOT/'staging/temporary-gpu2-recovery.bundle';metadata=data['bundle']
    if (bundle.is_symlink() or not bundle.is_file() or bundle.stat().st_uid!=os.getuid()
            or type(metadata['bytes']) is not int or not 0<metadata['bytes']<=16*1024**2
            or bundle.stat().st_size!=metadata['bytes'] or hashlib.sha256(bundle.read_bytes()).hexdigest()!=metadata['sha256']):
        raise ValueError('Exact owned bounded source bundle required')
    return bundle


def main():
    import subprocess
    data=json.load(sys.stdin);phase=data['phase'];started=time.monotonic()
    if not __debug__ or phase not in ('deploy','deploy-recovery','prepare','cpu'):raise ValueError('Only bounded CPU auxiliary phases')
    deploying=phase in ('deploy','deploy-recovery')
    modules=[]
    for name,expected in [('migrate_code_cpu','9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405'),
                          ('validate_space_cpu','c9d895c8567fac7f2248c8af63996e6eb4b60080edf493b51002c1c4da4a641b')]:
        raw=base64.b64decode(data[name],validate=True)
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Auxiliary process/asset helper differs')
        module=types.ModuleType(name);sys.modules[name]=module
        exec(compile(raw,name,'exec'),module.__dict__);modules.append(module)
    migration,helper=modules;helper.RUN_ID=RUN_ID;helper.RUN=RUN
    commit=data['runtime_commit'];raw_config=base64.b64decode(data['config'],validate=True)
    user=base64.b64decode(data['user'],validate=True);config=validate_config(raw_config,commit,user)
    end=config['temporary_gpu_use']['end_ms'];config_sha=hashlib.sha256(raw_config).hexdigest()
    def check():
        migration.validate_executor()
        now=int(time.time()*1000);snapshot=data['resource_snapshot']
        resources=[r for r in snapshot['resources'] if r.get('id')=='h20/qjh003']
        if (snapshot.get('origin')!='gputime_read_only_api' or snapshot.get('read_only') is not True
                or type(snapshot.get('observed_ms')) is not int or not 0<=now-snapshot['observed_ms']<=300000
                or len(resources)!=1 or resources[0].get('active') is not True
                or Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT
                or now<config['temporary_gpu_use']['start_ms'] or now+120000>=end
                or time.monotonic()-started>=239):raise ValueError('Direct CPU auxiliary scope/time/resource differs')
    check()
    if int(time.time()*1000)+360000>=end:raise TimeoutError('Full240+120 CPU unit does not fit temporary batch')
    gpu=subprocess.check_output(['nvidia-smi','--id=2','--query-gpu=uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=5)
    processes=subprocess.check_output(['nvidia-smi','--id=2','--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True,timeout=5)
    fields=[v.strip() for v in gpu.strip().split(',')]
    if len(fields)!=3 or fields[0]!=UUID or int(fields[1])>100 or int(fields[2])!=0 or processes.strip():raise ValueError('Direct idle condition absent; no CPU preparation writes')
    for path,digest in helper.SITE.items():
        if migration.sha(Path(path))!=digest:raise ValueError('Environment startup file changed')
    site=ROOT/'assets/envs/space/lib/python3.10/site-packages'
    if {str(p) for p in site.glob('*.pth')}!={p for p in helper.SITE if p.startswith(str(site))}:raise ValueError('Unknown startup code')
    if migration.sha(ROOT/'assets/manifest.json')!=helper.ASSETS_SHA:raise ValueError('Shared asset manifest changed')
    git=['git','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','core.excludesFile=/dev/null','-c','core.attributesFile=/dev/null','-C',str(ROOT/'repo')]
    if not deploying:
        environment=helper.child_environment(secrets.token_hex(24))
        head=subprocess.check_output(git+['rev-parse','HEAD'],env=environment,text=True,timeout=15).strip()
        status=subprocess.check_output(git+['status','--porcelain','--untracked-files=all'],env=environment,text=True,timeout=15).strip()
        if head!=commit or status:raise ValueError('Live repository source differs before importing code')
        check()
    evidence=ROOT/'staging/temporary-gpu2-preparation';candidate=ROOT/'staging/temporary-gpu2-project.json'
    for path in (evidence,RUN,candidate.parent,ROOT/'tmp/cpu'):migration.real_ancestry(path)
    if candidate.is_symlink():raise ValueError('Linked candidate')
    if phase=='deploy':
        if evidence.exists() or RUN.exists() or candidate.exists():raise ValueError('Preserve existing attempt; no retry')
        evidence.mkdir(mode=0o700)
    elif phase=='deploy-recovery':
        if RUN.exists() or candidate.exists():raise ValueError('Recovery cannot replace an existing run')
        if any((evidence/(phase+suffix)).exists() for suffix in ('.claim.json','.log','.terminal.json')):raise ValueError('No repeated deployment recovery')
        bundle=recovery_bundle(evidence,config,data)
    else:
        previous=('deploy-recovery' if (evidence/'deploy-recovery.terminal.json').exists() else 'deploy') if phase=='prepare' else 'prepare'
        prior=json.loads((evidence/(previous+'.terminal.json')).read_bytes())
        if (prior['exit_code']!=0 or prior['runtime_commit']!=commit or prior['config_sha256']!=config_sha
                or prior['log_sha256']!=migration.sha(evidence/(previous+'.log'))):raise ValueError('Matching successful previous unit required')
        if phase=='prepare' and (RUN.exists() or candidate.exists()):raise ValueError('Existing prepare; no retry')
    for folder in ('cpu','cpu-hf','cpu-torch'):
        path=ROOT/'tmp'/folder;migration.real_ancestry(path)
        path.mkdir(parents=True,mode=0o700,exist_ok=True)
    if any((ROOT/'tmp/cpu').iterdir()):raise ValueError('CPU fixture residue; preserve')
    migration.exclusive_json(evidence/(phase+'.claim.json'),dict(pid=os.getpid(),phase=phase,started_ms=int(time.time()*1000),
        run_id=RUN_ID,config_sha256=config_sha,origin='direct_user_conditional_idle_use',booking_claimed=False,
        gpu_metadata=gpu,compute_processes=processes,resource_snapshot=data['resource_snapshot']))
    environment=helper.child_environment(secrets.token_hex(24))
    terminal=dict(phase=phase,exit_code=1,runtime_commit=commit,config_sha256=config_sha,run_id=RUN_ID,boot=BOOT,GPU_requests=0)
    log=evidence/(phase+'.log')
    try:
        with log.open('xb') as stream:
            if deploying:
                if any((row.get('root') or '').startswith(str(ROOT)+'/runs/') for row in helper.process_records(0).values()):raise ValueError('Another own project process active')
                def command(arguments):
                    check();return migration.command_output(git+arguments,stream,min(60,max(.1,started+239-time.monotonic())),started+359)
                if command(['status','--porcelain','--untracked-files=all']).strip():raise ValueError('Target repository dirty')
                if command(['rev-parse','HEAD']).decode().strip()!='beadff9c4cc4693cd2ea8675020f757e313659e8':raise ValueError('Target prior HEAD changed')
                os.environ.clear();os.environ.update(environment)
                if phase=='deploy-recovery':
                    command(['bundle','verify',str(bundle)])
                    if command(['bundle','list-heads',str(bundle)]).decode().strip()!=commit+' HEAD':raise ValueError('Bundle HEAD differs')
                    command(['fetch',str(bundle),'HEAD'])
                else:command(['fetch','--no-tags','https://github.com/BoyJiang2/spaceserve-epd-reproduction.git',commit])
                if command(['rev-parse','FETCH_HEAD']).decode().strip()!=commit:raise ValueError('Fetched different source')
                command(['checkout','--detach',commit]);command(['fsck','--full'])
                if command(['rev-parse','HEAD']).decode().strip()!=commit or command(['status','--porcelain','--untracked-files=all']).strip():raise ValueError('Deployment differs')
            else:
                spec=importlib.util.spec_from_file_location('temporary_asset_inventory',ROOT/'repo/spaceserve/runtime/scripts/stage_cpu.py')
                inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)
                before=json.loads((ROOT/'assets/manifest.json').read_bytes())
                if inventory.inventory(ROOT/'assets')!=before:raise ValueError('Actual assets differ before unit')
                if phase=='prepare':
                    with candidate.open('xb') as output:output.write(raw_config)
                else:
                    frozen=json.loads((RUN/'configs/project.json').read_bytes());generated={'source_manifest_sha256','asset_manifest_sha256'}
                    if {k:v for k,v in frozen.items() if k not in generated}!={k:v for k,v in config.items() if k not in generated}:raise ValueError('Frozen configuration changed')
                argv=['/usr/bin/python3','-I','-S','-B',str(ROOT/'repo/spaceserve/runtime/entry.py'),phase,'--config',str(candidate if phase=='prepare' else RUN/'configs/project.json')]
                if phase=='prepare':argv+=['--commit',commit]
                helper.execute(argv,environment,stream,check,started+239,started+359)
                if inventory.inventory(ROOT/'assets')!=before:raise ValueError('Assets changed during unit')
        check()
        if any((ROOT/'tmp/cpu').iterdir()):raise ValueError('CPU fixture residue remains')
        terminal['exit_code']=0
    except BaseException as error:
        terminal.update(error_type=type(error).__name__,error=str(error));raise
    finally:
        terminal.update(finished_ms=int(time.time()*1000),log_sha256=migration.sha(log) if log.exists() else None)
        migration.exclusive_json(evidence/(phase+'.terminal.json'),terminal)
    print(json.dumps(terminal),flush=True)


if __name__=='__main__':main()
