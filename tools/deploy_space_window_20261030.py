"""Exact owned checkout update from a reviewed bundle; no run/asset modification."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

from control_space_window_20261030 import snapshot, verify_payload
from control_space_temporary_cpu import CHECKOUT, git, verified_file, process_identity
from space_window_20261030 import validate

BASE='730452dce69081ad7f668f890087362f1dd06326'


def server_command(commit):
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Exact published commit required')
    return r"""import base64,hashlib,json,os,signal,subprocess,sys,time,types
from pathlib import Path
p=json.load(sys.stdin);commit=%r;base=%r
started=time.monotonic();cancelled=[]
for number in (signal.SIGTERM,signal.SIGINT):signal.signal(number,lambda n,f:cancelled.append(n))
def check():
 if cancelled or time.monotonic()-started>=240:raise TimeoutError('Controlled deployment stop; preserve partial')
root=Path('/local/boyjiang/spaceserve');repo=root/'repo';stage=root/'staging/space-0400-deployment'
assert os.uname().nodename=='qjh003' and os.getuid()==2147 and os.sched_getaffinity(0)=={50} and os.getpriority(os.PRIO_PROCESS,0)==10
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='65f52a67-afe4-4919-8646-4694255b48ee'
policy={};exec(compile(base64.b64decode(p['policy']),'<published-window-policy>','exec'),policy)
policy['validate'](p['snapshot'],int(time.time()*1000),'prepare',p['config'])
review=base64.b64decode(p['review'],validate=True)
assert hashlib.sha256(review).hexdigest()==p['approval']['review_sha256']
assert p['approval']['passed'] is True and p['approval']['source_commit']==commit and p['approval']['phase']=='deploy'
git=['git','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',str(repo)]
assert subprocess.check_output(git+['rev-parse','HEAD'],text=True,timeout=10).strip()==base
assert not subprocess.check_output(git+['status','--porcelain','--untracked-files=all'],text=True,timeout=10).strip()
for name in ('migrate_code_cpu','materialize_assets_cpu'):
 raw=subprocess.check_output(git+['show',base+':tools/'+name+'.py'],timeout=10)
 module=types.ModuleType(name);module.__file__='git:'+base+':tools/'+name+'.py';sys.modules[name]=module
 exec(compile(raw,module.__file__,'exec'),module.__dict__)
assets=sys.modules['materialize_assets_cpu'];migration=sys.modules['migrate_code_cpu']
guard=types.ModuleType('space_user_service_guard')
exec(compile(base64.b64decode(p['user_service_guard']),'<published-user-service-guard>','exec'),guard.__dict__)
check();exceptions=guard.guard_processes(assets)
for path in (stage,repo,*repo.parents,stage.parent):
 assert not path.is_symlink()
 if path.exists() and path.is_relative_to(root):assert path.is_dir() and path.stat().st_uid==2147
assert not (root/'runs/space-formal-20261030-0400').exists()
rawgpu=subprocess.check_output(['nvidia-smi','--id=2','--query-gpu=uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=5)
apps=subprocess.check_output(['nvidia-smi','--id=2','--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True,timeout=5)
assert [v.strip() for v in rawgpu.strip().split(',')]==[p['config']['gpu_uuids'][0],'0','0'] and not apps.strip()
raw=base64.b64decode(p['bundle'],validate=True)
assert len(raw)==p['bundle_bytes'] and hashlib.sha256(raw).hexdigest()==p['bundle_sha256'] and len(raw)<8*1024**2
check();policy['validate'](p['snapshot'],int(time.time()*1000),'prepare',p['config'])
stage.mkdir(mode=0o700,exist_ok=False)
with (stage/'claim.json').open('x') as out:json.dump(dict(commit=commit,base=base,started_ms=int(time.time()*1000),exceptions=exceptions,bundle_sha256=p['bundle_sha256'],booking=p['snapshot']),out,indent=2)
bundle=stage/'source.bundle'
with bundle.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
assert hashlib.sha256(bundle.read_bytes()).hexdigest()==p['bundle_sha256']
terminal=dict(commit=commit,base=base,exit_code=1)
try:
 with (stage/'git.log').open('xb') as out:
  def command(args):
   check();policy['validate'](p['snapshot'],int(time.time()*1000),'prepare',p['config'])
   migration.command_output(git+args,out,min(45,max(.1,240-(time.monotonic()-started))),started+360)
   check()
  command(['bundle','verify',str(bundle)])
  command(['fetch',str(bundle),commit])
  assert not subprocess.check_output(git+['status','--porcelain','--untracked-files=all'],text=True,timeout=10).strip()
  guard.guard_processes(assets)
  command(['sparse-checkout','init','--cone'])
  command(['sparse-checkout','set','spaceserve/runtime','tests','tools'])
  command(['checkout','--detach',commit])
 assert subprocess.check_output(git+['rev-parse','HEAD'],text=True,timeout=10).strip()==commit
 assert not subprocess.check_output(git+['status','--porcelain','--untracked-files=all'],text=True,timeout=10).strip()
 rows=[]
 for entry in subprocess.check_output(git+['ls-files','-z'],timeout=15).split(b'\0'):
  check()
  if not entry:continue
  name=entry.decode();path=repo/name
  if not path.exists():continue  # Sparse entries are verified as Git objects, never called deployed files.
  assert not path.is_symlink() and path.stat().st_uid==2147 and path.resolve().is_relative_to(repo)
  actual=path.read_bytes();expected=subprocess.check_output(git+['show',commit+':'+name],timeout=10)
  assert actual==expected;rows.append(dict(path=name,bytes=len(actual),sha256=hashlib.sha256(actual).hexdigest()))
 for name in ('tools/run_space_window_20261030.py','tools/control_space_window_20261030.py','spaceserve/runtime/entry.py','spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json'):
  assert any(row['path']==name for row in rows)
 terminal.update(exit_code=0,files=rows,exceptions_after=guard.guard_processes(assets),new_GPU_requests=0,grants_no_runtime_Gate=True)
except BaseException as error:
 terminal['error']=repr(error);raise
finally:
 terminal['finished_ms']=int(time.time()*1000)
 with (stage/'exit.json').open('x') as out:json.dump(terminal,out,indent=2)
print(json.dumps(terminal))
""" % (commit,BASE)


def main():
    parser=argparse.ArgumentParser()
    for name in ('commit','bundle','approval','review','output'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();code=server_command(args.commit)
    if git('rev-parse','HEAD').decode().strip()!=args.commit:raise ValueError('Local commit differs')
    for name in ('tools/deploy_space_window_20261030.py','tools/space_user_service_guard.py','tools/control_space_window_20261030.py','tools/control_space_temporary_cpu.py','tools/space_window_20261030.py','spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json'):
        if verified_file(args.commit,name)!=(CHECKOUT/name).read_bytes():raise ValueError('Local/GitHub exact source differs')
    review=Path(args.review).read_bytes();approval=json.loads(Path(args.approval).read_bytes())
    if (approval.get('passed') is not True or approval.get('source_commit')!=args.commit or approval.get('phase')!='deploy'
            or approval.get('review_sha256')!=hashlib.sha256(review).hexdigest()):raise ValueError('Exact independent deployment approval required')
    cfg=json.loads((CHECKOUT/'spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json').read_bytes());proof=snapshot()
    validate(proof,int(time.time()*1000),'prepare',cfg)
    raw=Path(args.bundle).read_bytes()
    wire=json.dumps(dict(approval=approval,review=base64.b64encode(review).decode(),config=cfg,snapshot=proof,
        policy=base64.b64encode(git('show',args.commit+':tools/space_window_20261030.py')).decode(),
        user_service_guard=base64.b64encode(git('show',args.commit+':tools/space_user_service_guard.py')).decode(),
        bundle=base64.b64encode(raw).decode(),bundle_bytes=len(raw),bundle_sha256=hashlib.sha256(raw).hexdigest())).encode()
    output=Path(args.output).resolve()
    if not output.is_relative_to(CHECKOUT.parents[2]/'outputs'):raise ValueError('Evidence outside workspace outputs')
    output.mkdir(parents=True,exist_ok=False);(output/'input.json').write_bytes(wire)
    argv=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=15','-l','boyjiang','qjh003','taskset -c 50 nice -n 10 timeout --foreground --signal=TERM --kill-after=120s 240s /usr/bin/python3 -I -S -B -c '+shlex.quote(code)]
    (output/'command.json').write_text(json.dumps(dict(argv=argv,commit=args.commit,bundle_sha256=hashlib.sha256(raw).hexdigest()),indent=2),encoding='utf8')
    with (output/'input.json').open('rb') as stdin,(output/'stdout.log').open('xb') as out,(output/'stderr.log').open('xb') as err:
        verify_payload(stdin,hashlib.sha256(wire).hexdigest(),output)
        process=subprocess.Popen(argv,stdin=stdin,stdout=out,stderr=err)
        try:
            (output/'controller.json').write_text(json.dumps(process_identity(process),indent=2),encoding='utf8');process.wait(timeout=390)
        except BaseException as error:
            (output/'UNKNOWN.json').write_text(json.dumps(dict(pid=process.pid,error=repr(error),do_not_restart=True)),encoding='utf8');raise
    (output/'exit.json').write_text(json.dumps(dict(exit_code=process.returncode)),encoding='utf8')
    if process.returncode:raise SystemExit(process.returncode)


if __name__=='__main__':main()
