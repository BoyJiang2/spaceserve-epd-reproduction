"""Windows one-phase controller; publish/API verification precedes every SSH CPU unit."""
import argparse
import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import time
import types
import urllib.parse

REPOSITORY='BoyJiang2/spaceserve-epd-reproduction'
CHECKOUT=Path(__file__).resolve().parents[1]
EVIDENCE=CHECKOUT.parents[2]/'outputs/migration-qjh003'
API_PROOFS=[]


def api(path):
    if not path.startswith('repos/'+REPOSITORY+'/') and path!='repos/'+REPOSITORY:
        raise ValueError('Wrong repository')
    raw=subprocess.check_output(['curl.exe','--disable','--silent','--show-error','--fail',
        '--proto','=https','--max-redirs','0','--connect-timeout','15','--max-time','45',
        '-H','Accept: application/vnd.github+json','https://api.github.com/'+path],timeout=50)
    data=json.loads(raw)
    API_PROOFS.append({'path':path,'observed_ms':int(time.time()*1000),'response':data})
    return data


def git(*arguments):
    return subprocess.check_output(['git',*arguments],cwd=CHECKOUT,timeout=45)


def verified_file(commit,path):
    expected=git('show',commit+':'+path)
    remote=api('repos/'+REPOSITORY+'/contents/'+path+'?ref='+urllib.parse.quote(commit))
    actual=base64.b64decode(remote['content'],validate=False)
    blob=hashlib.sha1(b'blob '+str(len(actual)).encode()+b'\0'+actual).hexdigest()
    if actual!=expected or remote['sha']!=blob:
        raise ValueError('Actual GitHub file bytes/blob differ: '+path)
    return expected


def process_identity(process):
    fields=[wintypes.FILETIME() for _ in range(4)]
    if not ctypes.windll.kernel32.GetProcessTimes(wintypes.HANDLE(int(process._handle)),*[ctypes.byref(value) for value in fields]):
        raise ctypes.WinError()
    return {'pid':process.pid,'creation_filetime':(fields[0].dwHighDateTime<<32)|fields[0].dwLowDateTime,
            'controller_pid':os.getpid(),'observed_ms':int(time.time()*1000)}


def launch_cpu(argv,output,payload_sha256):
    path=output/'input.json'
    if path.is_symlink():raise ValueError('Linked CPU payload refused')
    with path.open('rb') as payload,(output/'stdout.log').open('xb') as stdout,(output/'stderr.log').open('xb') as stderr:
        identity=os.fstat(payload.fileno())
        actual=hashlib.sha256(payload.read()).hexdigest();payload.seek(0)
        if not stat.S_ISREG(identity.st_mode) or actual!=payload_sha256:raise ValueError('CPU payload identity/bytes differ')
        (output/'input-file.json').write_text(json.dumps({'device':identity.st_dev,'inode':identity.st_ino,
            'bytes':identity.st_size,'sha256':actual},indent=2),encoding='utf8')
        process=subprocess.Popen(argv,stdin=payload,stdout=stdout,stderr=stderr)
        try:
            (output/'controller.json').write_text(json.dumps(process_identity(process),indent=2),encoding='utf8')
            process.wait(timeout=390)
        except BaseException as error:
            state='OBSERVER_TIMEOUT_REMOTE_TERMINAL_UNKNOWN' if isinstance(error,subprocess.TimeoutExpired) else 'OBSERVER_ERROR_REMOTE_TERMINAL_UNKNOWN'
            (output/'UNKNOWN.json').write_text(json.dumps({'state':state,'error':repr(error),
                'do_not_restart':True,'pid':process.pid}),encoding='utf8')
            raise
    return process


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('deploy','prepare','cpu'));args=parser.parse_args()
    if os.name!='nt' or not __debug__:raise ValueError('Use the approved Windows controller')
    commit=git('rev-parse','HEAD').decode().strip()
    if git('ls-remote','origin','refs/heads/main').decode().split()[0]!=commit:raise ValueError('GitHub main differs')
    repository=api('repos/'+REPOSITORY)
    if repository['id']!=1433331669 or repository['private'] is not False:raise ValueError('Public repository identity differs')
    if api('repos/'+REPOSITORY+'/git/ref/heads/main')['object']['sha']!=commit:raise ValueError('API main differs')
    controller=verified_file(commit,'tools/control_space_temporary_cpu.py')
    if controller!=Path(__file__).read_bytes():raise ValueError('Running controller differs from committed/API source')
    source=verified_file(commit,'tools/prepare_space_temporary.py')
    modules={name:base64.b64encode(verified_file(commit,'tools/'+name+'.py')).decode()
             for name in ('migrate_code_cpu','validate_space_cpu')}
    config=(EVIDENCE/'temporary-gpu2-config.json').read_bytes()
    user=(EVIDENCE/'space-temporary-idle-user-authorization.txt').read_bytes()
    module=types.ModuleType('reviewed_temporary_cpu_validation')
    exec(compile(source,'<API-verified-CPU-validation>','exec'),module.__dict__)
    settings=module.validate_config(config,commit,user);now=int(time.time()*1000);grant=settings['temporary_gpu_use']
    if not grant['start_ms']<=now or now+360000>=grant['end_ms']:raise ValueError('Complete CPU unit cannot fit the fixed temporary batch')
    raw=subprocess.check_output([sys.executable,'-X','utf8','C:/Users/23520/.codex/skills/gputime-booking-agent/scripts/gputime_agent.py','snapshot'],timeout=45)
    snapshot=json.loads(raw)
    resource_snapshot={'origin':'gputime_read_only_api','read_only':True,'observed_ms':int(time.time()*1000),
        'resources':[{k:row.get(k) for k in ('id','node','active')} for row in snapshot['resources'] if row.get('id')=='h20/qjh003'],
        'bookings':[{k:row.get(k) for k in ('id','kind','resource_id','user','start_ms','end_ms')} for row in snapshot['bookings'] if row.get('resource_id')=='h20/qjh003' and row.get('end_ms',0)>now]}
    payload={'phase':args.phase,'runtime_commit':commit,'config':base64.b64encode(config).decode(),
             'user':base64.b64encode(user).decode(),'resource_snapshot':resource_snapshot,**modules}
    wire=json.dumps(payload).encode();digest=hashlib.sha256(source).hexdigest()
    wrapper='import base64,hashlib;source=base64.b64decode('+repr(base64.b64encode(source).decode())+');assert hashlib.sha256(source).hexdigest()=='+repr(digest)+';exec(compile(source,"<reviewed-temporary-cpu-unit>","exec"))'
    argv=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=15','-l','boyjiang','qjh003',
          'taskset -c 50 nice -n 10 timeout --foreground --signal=TERM --kill-after=120s 240s /usr/bin/python3 -I -S -B -c '+shlex.quote(wrapper)]
    if len(subprocess.list2cmdline(argv))>=30000:raise ValueError('Reviewed inline command exceeds Windows limit')
    output=EVIDENCE/('temporary-gpu2-cpu-'+args.phase);output.mkdir(exist_ok=False)
    (output/'api-evidence.json').write_text(json.dumps(API_PROOFS,indent=2),encoding='utf8')
    (output/'input.json').write_bytes(wire)
    (output/'command.json').write_text(json.dumps({'argv':argv,'commit':commit,'source_sha256':digest,
        'config_sha256':hashlib.sha256(config).hexdigest(),'payload_sha256':hashlib.sha256(wire).hexdigest(),
        'API_byte_verification_before_SSH':True},indent=2),encoding='utf8')
    process=launch_cpu(argv,output,hashlib.sha256(wire).hexdigest())
    terminal={'exit_code':process.returncode,'finished_ms':int(time.time()*1000),'commit':commit}
    (output/'exit.json').write_text(json.dumps(terminal,indent=2),encoding='utf8')
    print(json.dumps(terminal))
    if process.returncode:raise SystemExit(process.returncode)


if __name__=='__main__':main()
