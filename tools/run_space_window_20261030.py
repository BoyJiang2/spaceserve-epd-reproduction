"""One explicitly reviewed phase; no automatic Gates, retries or phase chaining."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import types

ROOT = Path('/local/boyjiang/spaceserve')
REPO = ROOT/'repo'
RUN = ROOT/'runs/space-formal-20261030-0400'
BOOT = '65f52a67-afe4-4919-8646-4694255b48ee'
CONFIG_PATH = 'spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json'


def command(phase, config, commit):
    if phase not in ('prepare','cpu','numeric','model','formal') or not re.fullmatch('[a-f0-9]{40}',commit):
        raise ValueError('Exact phase and commit required')
    result=['/usr/bin/python3','-I','-S','-B',str(REPO/'spaceserve/runtime/entry.py'),phase,'--config',str(config)]
    if phase=='prepare':result += ['--commit',commit]
    return result



def supervise_phase(policy, proof, cfg, phase, helper, supervision, argv, environment, log, check):
    # Refresh/identity verification time is part of this phase's admission budget.
    admitted_ms = int(time.time()*1000)
    limits = policy.validate(proof, admitted_ms, phase, cfg)
    supervision.supervise(helper, argv, environment, log, check, limits['work_seconds'])
    return dict(admitted_ms=admitted_ms, limits=limits)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('prepare','cpu','numeric','model','formal'))
    parser.add_argument('--commit',required=True)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--approval',type=Path,required=True)
    args=parser.parse_args()
    if not __debug__ or not re.fullmatch('[a-f0-9]{40}',args.commit):raise ValueError('Exact nonoptimized source required')
    git=['git','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',str(REPO)]
    if subprocess.check_output(git+['rev-parse','HEAD'],text=True,timeout=10).strip()!=args.commit:
        raise ValueError('Designated checkout commit differs')
    if subprocess.check_output(git+['status','--porcelain','--untracked-files=all'],text=True,timeout=10).strip():
        raise ValueError('Deployment is not frozen clean')
    if (os.uname().nodename!='qjh003' or os.getuid()!=2147 or os.sched_getaffinity(0)!={50}
            or os.getpriority(os.PRIO_PROCESS,0)!=10 or Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT):
        raise ValueError('Actual executor identity differs')
    def source(path):return subprocess.check_output(git+['show',args.commit+':'+path],timeout=10)
    def load(name):
        if name in sys.modules:raise ValueError('Unexpected preloaded launch dependency')
        module=types.ModuleType(name);module.__file__='git:'+args.commit+':tools/'+name+'.py'
        sys.modules[name]=module;exec(compile(source('tools/'+name+'.py'),module.__file__,'exec'),module.__dict__)
        return module
    policy=load('space_window_20261030')
    proposed=source(CONFIG_PATH);cfg=json.loads(proposed)
    proof=json.loads(args.snapshot.read_bytes());now=int(time.time()*1000)
    limits=policy.validate(proof,now,args.phase,cfg)
    approval=json.loads(args.approval.read_bytes())
    expected=dict(passed=True,phase=args.phase,source_commit=args.commit,run_id=RUN.name,boot_id=BOOT,
        proposed_config_sha256=hashlib.sha256(proposed).hexdigest(),booking_id=policy.GPU)
    if any(approval.get(k)!=v for k,v in expected.items()):raise ValueError('Exact independent phase execution approval required')
    for path in (args.approval,args.snapshot):
        if path.is_symlink() or path.stat().st_uid!=2147:raise ValueError('Unowned/linked phase evidence')
    gpu=subprocess.check_output(['nvidia-smi','--id=2','--query-gpu=uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=5)
    apps=subprocess.check_output(['nvidia-smi','--id=2','--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True,timeout=5)
    if [x.strip() for x in gpu.strip().split(',')]!=[cfg['gpu_uuids'][0],'0','0'] or apps.strip():
        raise ValueError('Actual GPU2 strict idle required')
    config=RUN/'configs/project.json'
    if args.phase=='prepare':
        if RUN.exists():raise ValueError('Existing run is not a prepare retry')
        config=REPO/CONFIG_PATH
        if config.is_symlink() or config.read_bytes()!=proposed:raise ValueError('Proposed checkout bytes differ')
    else:
        frozen=json.loads(config.read_bytes())
        if {k:v for k,v in frozen.items() if k not in ('source_commit','source_manifest_sha256','asset_manifest_sha256')}!=cfg or frozen.get('source_commit')!=args.commit:
            raise ValueError('Frozen configuration differs')
    load('migrate_code_cpu');helper=load('validate_space_cpu');supervision=load('run_space_numeric')
    helper.RUN_ID=RUN.name;helper.RUN=RUN
    for name,digest in helper.SITE.items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:raise ValueError('Pinned site startup changed')
    if hashlib.sha256((ROOT/'assets/manifest.json').read_bytes()).hexdigest()!=helper.ASSETS_SHA:
        raise ValueError('Protected asset inventory differs')
    stage=ROOT/'staging'/RUN.name
    for path in (stage,*stage.parents):
        if path.is_symlink():raise ValueError('Linked phase record ancestry')
        if path.exists() and path.is_relative_to(ROOT) and path.stat().st_uid!=2147:raise ValueError('Foreign phase record ancestry')
    stage.mkdir(exist_ok=True,mode=0o700)
    with (stage/(args.phase+'.claim.json')).open('x') as out:
        json.dump(dict(phase=args.phase,commit=args.commit,run_id=RUN.name,boot_id=BOOT,pid=os.getpid(),
            started_ms=now,approval=approval,snapshot=proof,limits=limits),out,indent=2)
    environment=helper.child_environment(secrets.token_hex(24))
    environment.update(SPACESERVE_CONFIG=str(config),EXP_ROOT=str(RUN),REPRO_PHASE=args.phase,MASK_OFF='56',
        PATH='/usr/local/cuda-12.8/bin:/usr/bin:/bin',OMP_NUM_THREADS='4',TOKENIZERS_PARALLELISM='false')
    if args.phase in ('numeric','model','formal'):environment['CUDA_VISIBLE_DEVICES']=cfg['gpu_uuids'][0]
    def check():
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT or int(time.time()*1000)+120000>=policy.END:
            raise RuntimeError('Actual boot or cleanup boundary reached')
    terminal=dict(phase=args.phase,commit=args.commit,run_id=RUN.name,exit_code=1)
    try:
        if args.phase in ('numeric','model','formal'):
            refresh=REPO/'spaceserve/runtime/tools/refresh_booking.py'
            if refresh.read_bytes()!=source('spaceserve/runtime/tools/refresh_booking.py'):
                raise ValueError('Booking refresh source changed')
            subprocess.run(['/usr/bin/python3','-I','-S','-B',str(refresh),'--snapshot',str(args.snapshot.resolve())],
                env=dict(environment,CUDA_VISIBLE_DEVICES=''),check=True,timeout=20)
        with (stage/(args.phase+'.log')).open('xb') as out:
            terminal['actual_admission']=supervise_phase(policy,proof,cfg,args.phase,helper,supervision,command(args.phase,config,args.commit),environment,out,check)
        terminal['exit_code']=0
    except BaseException as error:
        terminal['error']=repr(error);raise
    finally:
        terminal['finished_ms']=int(time.time()*1000)
        with (stage/(args.phase+'.exit.json')).open('x') as out:json.dump(terminal,out,indent=2)
    print(json.dumps(terminal))


if __name__=='__main__':main()
