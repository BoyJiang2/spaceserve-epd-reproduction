"""Two fixed trusted CPU validation units; no numeric/model/formal entry."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import subprocess
import sys
import time

import migrate_code_cpu as migration

ROOT=Path('/local/boyjiang/spaceserve')
RUN_ID='migration-cpu-fix-20261029'
RUN=ROOT/'runs'/RUN_ID
OLD_RUNTIME='a3f03b9dd5956db92add454f9b3afd5663f84609'
RUNTIME='7fc3877e4f67cfcaecc6da1b47dbaf60ebdef61c'
BUNDLE_SHA='39ad9860eab2fb6f5a7fc5ed3b75d99af36779ed76e368de66efd1504dcfbfbc'
BOOT='65f52a67-afe4-4919-8646-4694255b48ee'
ASSETS_SHA='962ed4f1c1584e8f4c130e23e5ead049701bda8e5c8b0c764345e687d21b8716'
CONFIG_SHA='396e58b949fa5a74af5fd84df8524ea21a81ca8c13e650ca58ebc0ca3ccbdab8'
SITE={'/local/boyjiang/spaceserve/assets/envs/space/lib/python3.10/site-packages/distutils-precedence.pth':'2638ce9e2500e572a5e0de7faed6661eb569d1b696fcba07b0dd223da5f5d224',
      '/usr/lib/python3.10/sitecustomize.py':'43d81125d92376b1a69d53a71126a041cc9a18d8080e92dea0a2ae23be138b1e'}


def select_owned(records,known,nonce,launch_ticks):
    """Register only exact existing identities, marked children or actual descendants."""
    selected={}
    for _ in range(len(records)+1):
        changed=False
        for pid,row in records.items():
            if pid in selected or row['uid']!=2147 or row['start_ticks']<launch_ticks:continue
            saved=known.get(pid)
            if saved is not None and saved['start_ticks']!=row['start_ticks']:continue
            parent=(selected.get(row['ppid']) or known.get(row['ppid']))
            parent_now=records.get(row['ppid'])
            descendant=parent is not None and parent_now is not None and parent_now['start_ticks']==parent['start_ticks']
            marked=(row.get('nonce')==nonce and row.get('run_id')==RUN_ID and row.get('root')==str(RUN))
            if saved is not None or descendant or marked:selected[pid]=row;changed=True
        if not changed:break
    return selected


def process_records(launch_ticks):
    records={}
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit():continue
        try:
            if folder.stat().st_uid!=2147:continue
            fields=(folder/'stat').read_text().rsplit(')',1)[1].split();ticks=int(fields[19])
            if ticks<launch_ticks:continue
            values={}
            try:
                for item in (folder/'environ').read_bytes().split(b'\0'):
                    if b'=' in item:
                        name,value=item.split(b'=',1)
                        if name in (b'REPRO_CPU_NONCE',b'REPRO_CPU_RUN_ID',b'REPRO_CPU_ROOT'):values[name.decode()]=value.decode(errors='replace')
            except PermissionError:pass  # Unrelated SSH/PAM services do not gain ownership.
            records[int(folder.name)]={'pid':int(folder.name),'uid':2147,'start_ticks':ticks,'ppid':int(fields[1]),
                'nonce':values.get('REPRO_CPU_NONCE'),'run_id':values.get('REPRO_CPU_RUN_ID'),'root':values.get('REPRO_CPU_ROOT')}
        except (FileNotFoundError,ProcessLookupError):continue
    return records


def child_environment(nonce):
    tmp=ROOT/'tmp/cpu'
    return {'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LC_ALL':'C.UTF-8','TMPDIR':str(tmp),
        'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','CUDA_VISIBLE_DEVICES':'',
        'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_DATASETS_OFFLINE':'1',
        'HF_HOME':str(ROOT/'tmp/cpu-hf'),'TORCH_HOME':str(ROOT/'tmp/cpu-torch'),
        'SETUPTOOLS_USE_DISTUTILS':'stdlib','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null',
        'GIT_TERMINAL_PROMPT':'0','GIT_ATTR_NOSYSTEM':'1','REPRO_CPU_NONCE':nonce,
        'REPRO_CPU_ROOT':str(RUN),'REPRO_CPU_RUN_ID':RUN_ID}


def execute(argv,environment,stream,check,deadline,cleanup_deadline):
    known={};cleanup=[];process=None;starting=True;pending=None;failure=None
    launch_ticks=int(time.clock_gettime(time.CLOCK_BOOTTIME)*os.sysconf('SC_CLK_TCK'))-1
    previous={number:signal.getsignal(number) for number in (signal.SIGTERM,signal.SIGINT)}
    def interrupted(number,frame):
        nonlocal pending
        pending=pending or number
        if not starting:raise RuntimeError('CPU unit interrupted')
    for number in previous:signal.signal(number,interrupted)
    try:
        process=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,env=environment,start_new_session=True)
        initial=process_records(launch_ticks);root=initial.get(process.pid)
        if root is None or root['uid']!=2147:raise ValueError('Actual CPU child identity absent')
        known[process.pid]=root;starting=False
        if pending:raise RuntimeError('Deferred CPU startup interrupt')
        while True:
            check();current=select_owned(process_records(launch_ticks),known,environment['REPRO_CPU_NONCE'],launch_ticks);known.update(current)
            if process.poll() is not None:break
            if time.monotonic()>=deadline:raise TimeoutError('CPU work deadline')
            time.sleep(.05)
        if process.returncode:raise RuntimeError('Trusted CPU entry exit '+str(process.returncode))
    except BaseException as error:failure=error
    finally:
        for number in previous:signal.signal(number,signal.SIG_IGN)
        try:
            for number in (signal.SIGTERM,signal.SIGKILL):
                if process is not None:process.poll()
                current=select_owned(process_records(launch_ticks),known,environment['REPRO_CPU_NONCE'],launch_ticks);known.update(current)
                if not current:break
                for pid,row in current.items():
                    try:handle=os.pidfd_open(pid)
                    except ProcessLookupError:continue
                    try:
                        now=process_records(launch_ticks).get(pid)
                        if now is not None and now['uid']==row['uid'] and now['start_ticks']==row['start_ticks']:
                            signal.pidfd_send_signal(handle,number);cleanup.append({'signal':number,'identity':row})
                    except ProcessLookupError:pass
                    finally:os.close(handle)
                until=min(cleanup_deadline,time.monotonic()+2)
                while time.monotonic()<until:
                    if process is not None:process.poll()
                    if not select_owned(process_records(launch_ticks),known,environment['REPRO_CPU_NONCE'],launch_ticks):break
                    time.sleep(.05)
            remaining=select_owned(process_records(launch_ticks),known,environment['REPRO_CPU_NONCE'],launch_ticks)
            unknown=[row for pid,row in process_records(launch_ticks).items()
                     if row.get('nonce')==environment['REPRO_CPU_NONCE'] and row.get('root')==str(RUN)
                     and row.get('run_id')==RUN_ID and pid not in remaining]
            stream.write(('\n'+json.dumps({'registered_processes':list(known.values()),'cleanup':cleanup,'remaining':list(remaining.values()),'unknown_marked':unknown,
                'exit_code':None if process is None else process.returncode})+'\n').encode());stream.flush()
            if remaining or unknown:raise RuntimeError('CPU fixture release unconfirmed; no GPU continuation')
        finally:
            for number,handler in previous.items():signal.signal(number,handler)
    if failure is not None:raise failure


def run(data):
    started=time.monotonic();phase=data['phase'];proof=data['booking'];evidence=ROOT/'staging/cpu-validation-fixture'
    def check():
        migration.booking(proof,int(time.time()*1000))
        if time.monotonic()-started>=239:raise TimeoutError('CPU unit work budget')
    check();migration.validate_executor()
    if (phase not in ('deploy','prepare','cpu') or data['runtime_commit']!=RUNTIME
            or not re.fullmatch('[0-9a-f]{40}',data['tool_commit'])
            or Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT
            or sys.version_info[:3]!=(3,10,12) or not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal')):
        raise ValueError('Exact CPU phase/boot/Python/pidfd required')
    raw=base64.b64decode(data['source_config_base64'],validate=True)
    if (hashlib.sha256(raw).hexdigest()!=CONFIG_SHA or (ROOT/'assets/manifest.json').is_symlink()
            or migration.sha(ROOT/'assets/manifest.json')!=ASSETS_SHA):
        raise ValueError('Approved CPU configuration or shared assets manifest differs')
    for path,digest in SITE.items():
        if migration.sha(Path(path))!=digest:raise ValueError('Python startup file changed')
    site=ROOT/'assets/envs/space/lib/python3.10/site-packages'
    if {str(p) for p in site.glob('*.pth')}!={path for path in SITE if path.startswith(str(site))}:
        raise ValueError('Unexpected startup pth')
    for path in (evidence,RUN,ROOT/'tmp/cpu'):migration.real_ancestry(path)
    if phase=='deploy':
        if evidence.exists() or RUN.exists():raise ValueError('Existing CPU validation cohort; do not retry')
        evidence.mkdir(mode=0o700)
        with (evidence/'candidate.json').open('xb') as writer:writer.write(raw)
    else:
        previous='deploy' if phase=='prepare' else 'prepare'
        prior=json.loads((evidence/(previous+'.terminal.json')).read_bytes())
        binding={'runtime_commit':RUNTIME,'source_config_sha256':CONFIG_SHA,'assets_manifest_sha256':ASSETS_SHA,
                 'host':'qjh003','uid':2147,'boot_id':BOOT,'run_id':RUN_ID}
        if (prior['state']!='CPU_VALIDATION_UNIT_SUCCEEDED' or prior['tool_commit']!=data['tool_commit']
                or any(prior.get(k)!=v for k,v in binding.items()) or migration.sha(evidence/(previous+'.log'))!=prior['log_sha256']):
            raise ValueError('Actual matching prepare success required')
        if phase=='cpu':
            frozen=json.loads((RUN/'configs/project.json').read_bytes());original=json.loads(raw)
            generated={'source_manifest_sha256','asset_manifest_sha256'}
            if ({k:v for k,v in frozen.items() if k not in generated}!={k:v for k,v in original.items() if k not in generated}
                    or migration.sha(RUN/'configs/asset-inputs.json')!=ASSETS_SHA):
                raise ValueError('Exact generated CPU configuration and shared input bytes required')
    nonce=secrets.token_hex(16);claim={'phase':phase,'tool_commit':data['tool_commit'],'runtime_commit':RUNTIME,'booking':proof,
        'source_config_sha256':CONFIG_SHA,'assets_manifest_sha256':ASSETS_SHA,'host':socket.gethostname(),'uid':os.getuid(),'boot_id':BOOT,
        'run_id':RUN_ID,'nonce':nonce,'pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],
        'started_ms':int(time.time()*1000),'affinity':sorted(os.sched_getaffinity(0)),
        'nice':os.getpriority(os.PRIO_PROCESS,0)}
    migration.exclusive_json(evidence/(phase+'.claim.json'),claim);log=evidence/(phase+'.log');failure=None
    handlers={number:signal.getsignal(number) for number in (signal.SIGTERM,signal.SIGINT)}
    def stopped(number,frame):raise RuntimeError('CPU unit interrupted outside child')
    for number in handlers:signal.signal(number,stopped)
    try:
        for path in (ROOT/'tmp/cpu',ROOT/'tmp/cpu-hf',ROOT/'tmp/cpu-torch'):
            migration.real_ancestry(path);path.mkdir(mode=0o700,parents=True,exist_ok=True)
        if any((ROOT/'tmp/cpu').iterdir()):raise ValueError('CPU fixture temp root is not empty; do not clear unknown files')
        expected_head=OLD_RUNTIME if phase=='deploy' else RUNTIME
        if (ROOT/'repo/.git/HEAD').read_text().strip()!=expected_head:raise ValueError('Exact expected runtime HEAD required')
        if phase=='deploy':
            bundle=ROOT/'staging/space-fixture-fix.bundle'
            if bundle.is_symlink() or bundle.stat().st_uid!=2147 or bundle.stat().st_size!=918129 or migration.sha(bundle)!=BUNDLE_SHA:
                raise ValueError('Exact transferred incremental bundle required')
            os.environ.clear();os.environ.update(child_environment(nonce))
            with log.open('xb') as stream:
                base=['git','-c','core.fsmonitor=false','-c','core.excludesFile=/dev/null','-c','core.attributesFile=/dev/null','-c','core.hooksPath=/dev/null','-C',str(ROOT/'repo')]
                def command(args):
                    check();return migration.command_output(base+args,stream,max(.1,started+238-time.monotonic()),started+360)
                if command(['status','--porcelain','--untracked-files=all']).strip():raise ValueError('Runtime repository dirty')
                command(['bundle','verify',str(bundle)])
                if command(['bundle','list-heads',str(bundle)]).decode().strip()!=RUNTIME+' refs/heads/main':raise ValueError('Bundle target differs')
                command(['fetch',str(bundle),'refs/heads/main'])
                changed=command(['diff','--name-only',OLD_RUNTIME,RUNTIME,'--','spaceserve/runtime','reproduction_paths.py']).decode().splitlines()
                if changed!=['spaceserve/runtime/scripts/test_formal_cell.py']:raise ValueError('Production runtime changed outside fixture')
                command(['checkout','--detach',RUNTIME])
                if command(['rev-parse','HEAD']).decode().strip()!=RUNTIME:raise ValueError('Actual runtime HEAD differs')
                if command(['status','--porcelain','--untracked-files=all']).strip():raise ValueError('Deployment not clean')
                command(['fsck','--full'])
        else:
            spec=importlib.util.spec_from_file_location('asset_inventory',ROOT/'repo/spaceserve/runtime/scripts/stage_cpu.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            before=json.loads((ROOT/'assets/manifest.json').read_bytes())
            if phase=='cpu' and module.inventory(ROOT/'assets')!=before:raise ValueError('Assets changed before CPU suite')
            check();configuration=evidence/'candidate.json' if phase=='prepare' else RUN/'configs/project.json'
            python='/usr/bin/python3' if phase=='prepare' else str(ROOT/'assets/envs/space/bin/python')
            argv=[python,'-I','-B']+(['-S'] if phase=='prepare' else [])+[str(ROOT/'repo/spaceserve/runtime/entry.py'),phase,'--config',str(configuration)]
            if phase=='prepare':argv+=['--commit',RUNTIME]
            with log.open('xb') as stream:
                stream.write((json.dumps({'argv':argv,'scope':'trusted CPU only; no numeric/model/formal'})+'\n').encode());stream.flush()
                execute(argv,child_environment(nonce),stream,check,started+238,started+360)
            check()
            if phase=='cpu' and module.inventory(ROOT/'assets')!=before:raise ValueError('Assets changed during CPU suite')
            if any((ROOT/'tmp/cpu').iterdir()):raise ValueError('CPU fixture temp files remain; preserve them')
            check()
    except BaseException as error:failure=repr(error)
    for number in handlers:signal.signal(number,signal.SIG_IGN)
    try:
        migration.exclusive_json(evidence/(phase+'.terminal.json'),{**claim,'ended_ms':int(time.time()*1000),
            'elapsed_seconds':time.monotonic()-started,'state':'CPU_VALIDATION_UNIT_SUCCEEDED' if failure is None else 'FAILED_PRESERVED',
            'failure':failure,'log_sha256':migration.sha(log) if log.exists() else None,'GPU_requests':0,'grants_no_GPU':True})
    finally:
        for number,handler in handlers.items():signal.signal(number,handler)
    if failure is not None:raise RuntimeError(failure)
    return {'phase':phase,'state':'CPU_VALIDATION_UNIT_SUCCEEDED','GPU_requests':0}


if __name__=='__main__':
    raw=sys.stdin.buffer.read(100001)
    if len(raw)>100000:raise ValueError('CPU payload budget')
    print(json.dumps(run(json.loads(raw))))
