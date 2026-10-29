"""Windows one-phase SSH controller; records UNKNOWN without killing or redispatch."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import stat
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

from control_space_temporary_cpu import verified_file, process_identity, CHECKOUT, git
from space_window_20261030 import BUDGETS


def bootstrap(commit, phase):
    if not re.fullmatch('[a-f0-9]{40}',commit) or phase not in BUDGETS:
        raise ValueError('Exact phase and revision required')
    return """import base64,hashlib,json,os,subprocess,sys,time,types
from pathlib import Path
p=json.load(sys.stdin);commit=%r;phase=%r
root=Path('/local/boyjiang/spaceserve');repo=root/'repo';stage=root/'staging/space-formal-20261030-0400'
git=['git','-C',str(repo)]
assert os.uname().nodename=='qjh003' and os.getuid()==2147 and os.sched_getaffinity(0)=={50} and os.getpriority(os.PRIO_PROCESS,0)==10
assert subprocess.check_output(git+['rev-parse','HEAD'],text=True,timeout=10).strip()==commit
assert not subprocess.check_output(git+['status','--porcelain','--untracked-files=all'],text=True,timeout=10).strip()
def source(name):return subprocess.check_output(git+['show',commit+':'+name],timeout=10)
policy={};exec(compile(source('tools/space_window_20261030.py'),'git:window-policy','exec'),policy)
cfg=json.loads(source('spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json'))
policy['validate'](p['snapshot'],int(time.time()*1000),phase,cfg)
review=base64.b64decode(p['review'],validate=True)
assert hashlib.sha256(review).hexdigest()==p['approval']['review_sha256']
for path in (stage,*stage.parents):
 assert not path.is_symlink()
 if path.exists() and path.is_relative_to(root):assert path.is_dir() and path.stat().st_uid==2147
stage.mkdir(mode=0o700,exist_ok=True)
folder=stage/(phase+'-inputs');folder.mkdir(mode=0o700,exist_ok=False)
for name,raw in [('snapshot.json',json.dumps(p['snapshot']).encode()),('approval.json',json.dumps(p['approval']).encode()),('review.md',review)]:
 with (folder/name).open('xb') as out:out.write(raw)
raw=source('tools/run_space_window_20261030.py')
sys.argv=['run_space_window_20261030.py',phase,'--commit',commit,'--snapshot',str(folder/'snapshot.json'),'--approval',str(folder/'approval.json')]
exec(compile(raw,'git:'+commit+':tools/run_space_window_20261030.py','exec'),{'__name__':'__main__'})
""" % (commit,phase)


def snapshot():
    path=Path('C:/Users/23520/.codex/skills/gputime-booking-agent/scripts/gputime_agent.py')
    spec=importlib.util.spec_from_file_location('owned_booking_client',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    class Args:token_file=str(module.default_token_file())
    config='url = "https://gputime.approaching-ai.com/api/agent/snapshot"\nheader = '+json.dumps('Authorization: Bearer '+module.load_token(Args()))+'\nheader = "Accept: application/json"\n'
    response=subprocess.run(['curl.exe','--disable','--silent','--show-error','--fail','--connect-timeout','10','--max-time','25','--config','-'],input=config.encode(),capture_output=True,timeout=30)
    if response.returncode:raise RuntimeError('Booking read failed; sensitive response omitted; no dispatch')
    data=json.loads(response.stdout);now=int(time.time()*1000)
    return dict(origin='gputime_read_only_api',read_only=True,observed_ms=now,
        resources=[{k:r.get(k) for k in ('id','node','active','gpu_count')} for r in data['resources'] if r.get('id')=='h20/qjh003'],
        bookings=[{k:r.get(k) for k in ('id','node','resource_id','kind','user','start_ms','end_ms')} for r in data['bookings'] if r.get('resource_id')=='h20/qjh003' and r['end_ms']>now])


def verify_payload(payload, expected_sha256, output):
    info = os.fstat(payload.fileno())
    if not stat.S_ISREG(info.st_mode):raise ValueError('SSH payload is not a regular file')
    actual = hashlib.sha256(payload.read()).hexdigest()
    after = os.fstat(payload.fileno())
    if ((info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns) !=
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) or actual != expected_sha256):
        raise ValueError('Actual open SSH payload differs; no dispatch')
    payload.seek(0)
    with (output/'input-file.json').open('x',encoding='utf8') as record:
        json.dump(dict(device=info.st_dev,inode=info.st_ino,bytes=info.st_size,sha256=actual),record,indent=2)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=tuple(BUDGETS))
    parser.add_argument('--commit',required=True)
    parser.add_argument('--approval',required=True,type=Path)
    parser.add_argument('--review',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();code=bootstrap(args.commit,args.phase)
    if git('rev-parse','HEAD').decode().strip()!=args.commit:raise ValueError('Local source commit differs')
    for name in ('tools/control_space_window_20261030.py','tools/control_space_temporary_cpu.py','tools/run_space_window_20261030.py','tools/space_window_20261030.py','tools/run_space_numeric.py','tools/validate_space_cpu.py','tools/migrate_code_cpu.py','spaceserve/runtime/entry.py','spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json'):
        if verified_file(args.commit,name)!=(CHECKOUT/name).read_bytes():raise ValueError('Local/GitHub source bytes differ')
    approval=json.loads(args.approval.read_bytes());review=args.review.read_bytes()
    if (approval.get('review_sha256')!=hashlib.sha256(review).hexdigest() or approval.get('source_commit')!=args.commit
            or approval.get('phase')!=args.phase or approval.get('passed') is not True):
        raise ValueError('Independent exact phase review required')
    proof=snapshot()
    from space_window_20261030 import validate
    cfg=json.loads((CHECKOUT/'spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json').read_bytes())
    limits=validate(proof,int(time.time()*1000),args.phase,cfg)
    output=args.output.resolve()
    if not output.is_relative_to(CHECKOUT.parents[2]/'outputs'):raise ValueError('Evidence must remain in workspace outputs')
    output.mkdir(parents=True,exist_ok=False)
    wire=json.dumps(dict(approval=approval,review=base64.b64encode(review).decode(),snapshot=proof)).encode()
    (output/'input.json').write_bytes(wire)
    total=limits['work_seconds']+120
    argv=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=15','-l','boyjiang','qjh003',
        'taskset -c 50 nice -n 10 timeout --foreground --signal=TERM --kill-after=120s '+str(total)+'s /usr/bin/python3 -I -S -B -c '+shlex.quote(code)]
    (output/'command.json').write_text(json.dumps(dict(argv=argv,commit=args.commit,phase=args.phase,payload_sha256=hashlib.sha256(wire).hexdigest()),indent=2),encoding='utf8')
    with (output/'input.json').open('rb') as stdin,(output/'stdout.log').open('xb') as out,(output/'stderr.log').open('xb') as err:
        verify_payload(stdin,hashlib.sha256(wire).hexdigest(),output)
        process=subprocess.Popen(argv,stdin=stdin,stdout=out,stderr=err)
        try:
            (output/'controller.json').write_text(json.dumps(process_identity(process),indent=2),encoding='utf8')
            process.wait(timeout=total+150)
        except BaseException as error:
            (output/'UNKNOWN.json').write_text(json.dumps(dict(pid=process.pid,error=repr(error),do_not_restart=True)),encoding='utf8')
            raise
    (output/'exit.json').write_text(json.dumps(dict(exit_code=process.returncode,finished_ms=int(time.time()*1000))),encoding='utf8')
    print(json.dumps(dict(exit_code=process.returncode,phase=args.phase)))
    if process.returncode:raise SystemExit(process.returncode)


if __name__=='__main__':main()
