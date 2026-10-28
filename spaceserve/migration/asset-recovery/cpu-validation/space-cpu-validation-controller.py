import base64,ctypes,datetime,hashlib,json,os,shlex,subprocess,sys,time
from ctypes import wintypes
from pathlib import Path

BASE=Path(__file__).resolve().parent
REPO=BASE.parents[1]/'work/repository-upload/checkout'
SSH=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=15','-l','boyjiang','qjh003']
def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(name,data):
    with (BASE/name).open('x',encoding='utf8') as stream:json.dump(data,stream,indent=2)
def created(process):
    values=[wintypes.FILETIME() for _ in range(4)]
    if not ctypes.windll.kernel32.GetProcessTimes(wintypes.HANDLE(int(process._handle)),*[ctypes.byref(v) for v in values]):
        raise ctypes.WinError()
    ticks=(values[0].dwHighDateTime<<32)|values[0].dwLowDateTime
    return datetime.datetime.fromtimestamp(ticks/10000000-11644473600,datetime.timezone.utc).isoformat()
def remote_read(code,label):
    argv=SSH+['/usr/bin/python3 -I -S -B -c '+shlex.quote(code)]
    save(label+'-command.json',dict(argv=argv))
    result=subprocess.run(argv,capture_output=True,timeout=35)
    for suffix,raw in [('stdout',result.stdout),('stderr',result.stderr)]:
        with (BASE/(label+'.'+suffix+'.log')).open('xb') as stream:stream.write(raw)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
    return json.loads(result.stdout)

commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
assert json.loads((BASE/'space-cpu-validation-publication-verified.json').read_bytes())['commit']==commit
wrapper=(BASE/'space-cpu-validation-wrapper.py').read_text()
assert sha(wrapper.encode())=='d90efa0e981141fe9c29f7affb9d85139688eb9852194d35677f32f31c9ee3f2'
modules=[]
for name,digest in [('migrate_code_cpu','9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405'),('validate_space_cpu','fd4ccfd1a7c4ff689d7eb39eee83067abee52359e29717d5373166694329631c')]:
 raw=subprocess.check_output(['git','show',commit+':tools/'+name+'.py'],cwd=REPO);assert sha(raw)==digest
 modules.append(dict(name=name,sha256=digest,base64=base64.b64encode(raw).decode()))
config=subprocess.check_output(['git','show',commit+':spaceserve/migration/asset-recovery/cpu-validation/project.json'],cwd=REPO)
assert sha(config)=='2f914400aa04d53637c761fc8b7dcd46d8825168aa60604af562b8d25ba0d4b3'
save('space-cpu-validation-controller.json',dict(driver_pid=os.getpid(),started_ms=int(time.time()*1000),tool_commit=commit,stop_on_failure=True))
progress=[]
for phase in ('prepare','cpu'):
 prefix='space-cpu-validation-'+phase
 api=subprocess.run([sys.executable,'-X','utf8','C:/Users/23520/.codex/skills/gputime-booking-agent/scripts/gputime_agent.py','snapshot'],capture_output=True,timeout=45);assert api.returncode==0
 snapshot=json.loads(api.stdout);now=int(time.time()*1000)
 proof=dict(origin='gputime_read_only_api',read_only=True,observed_ms=now,resources=[dict(id=r['id'],node=r['node'],active=r['active']) for r in snapshot['resources'] if r['id']=='h20/qjh003'],bookings=[r for r in snapshot['bookings'] if r['id']=='bk-20261028T0925-0332cf80'])
 assert len(proof['bookings'])==len(proof['resources'])==1 and proof['resources'][0]['active'] is True
 ticket=proof['bookings'][0]
 assert all(ticket.get(k)==v for k,v in dict(user='boyjiang',kind='cpu',resource_id='h20/qjh003',node='qjh003',start_ms=1793192400000,end_ms=1793235600000).items())
 assert ticket['start_ms']<=now and now+1020000<=ticket['end_ms']
 save(prefix+'-booking.json',proof)
 paths=['/local/boyjiang/spaceserve/staging/cpu-validation/'+phase+'.claim.json']
 if phase=='prepare':paths+=['/local/boyjiang/spaceserve/staging/cpu-validation','/local/boyjiang/spaceserve/runs/migration-cpu-003-20261029']
 code="""import json,os,socket,time,shutil
from pathlib import Path
root=Path('/local/boyjiang/spaceserve');pinned=[]
for folder in Path('/proc').iterdir():
 if not folder.name.isdigit():continue
 try:
  if folder.stat().st_uid==2147 and os.sched_getaffinity(int(folder.name))=={50}:pinned.append(int(folder.name))
 except (FileNotFoundError,ProcessLookupError):pass
parents=[root,root/'staging',root.parent]
print(json.dumps(dict(observed_ms=int(time.time()*1000),host=socket.gethostname(),uid=os.getuid(),boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),cpu50=pinned,free=shutil.disk_usage(root).free,parents_owned=all(p.is_dir() and p.stat().st_uid==2147 and p.resolve()==p for p in parents),linked_ancestors=any(p.is_symlink() for p in [root,*root.parents]),existing=[p for p in PATHS if os.path.lexists(p)])))""".replace('PATHS',repr(paths))
 before=int(time.time()*1000);actual=remote_read(code,prefix+'-admission');after=int(time.time()*1000)
 assert actual['host']=='qjh003' and actual['uid']==2147 and actual['boot']=='65f52a67-afe4-4919-8646-4694255b48ee'
 assert not actual['cpu50'] and not actual['existing'] and actual['free']>=120*1024**3 and actual['parents_owned'] and not actual['linked_ancestors']
 assert before-2000<=actual['observed_ms']<=after+2000 and after-proof['observed_ms']<60000
 save(prefix+'-admission.json',dict(actual=actual,local_before_ms=before,local_after_ms=after,passed=True))
 data=dict(phase=phase,tool_commit=commit,runtime_commit='a3f03b9dd5956db92add454f9b3afd5663f84609',booking=proof,source_config_base64=base64.b64encode(config).decode(),modules=modules)
 wire=json.dumps(data).encode();assert len(wire)<=100000
 with (BASE/(prefix+'-payload.json')).open('xb') as stream:stream.write(wire)
 assert sha((BASE/(prefix+'-payload.json')).read_bytes())==sha(wire)
 argv=SSH+['taskset -c 50 nice -n 10 timeout --signal=TERM --kill-after=120s 240s /usr/bin/python3 -I -S -B -c '+shlex.quote(wrapper)]
 save(prefix+'-command.json',dict(argv=argv,wire_payload_sha256=sha(wire),wrapper_sha256=sha(wrapper.encode())));started=time.monotonic()
 with (BASE/(prefix+'.stdout.log')).open('xb') as out,(BASE/(prefix+'.stderr.log')).open('xb') as err:
  process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=out,stderr=err)
  save(prefix+'-controller.json',dict(pid=process.pid,created_utc=created(process)))
  try:process.communicate(wire,timeout=390)
  except subprocess.TimeoutExpired:
   save(prefix+'-unknown.json',dict(state='OBSERVER_TIMEOUT_UNKNOWN_DO_NOT_RESTART'));raise
 result=dict(phase=phase,exit_code=process.returncode,elapsed_seconds=time.monotonic()-started,tool_commit=commit)
 save(prefix+'-exit.json',result);progress.append(result);(BASE/'space-cpu-validation-progress.json').write_text(json.dumps(progress,indent=2));print(json.dumps(result),flush=True)
 if process.returncode:sys.exit(process.returncode)
save('space-cpu-validation-sequence-complete.json',dict(actions=progress,actual_CPU_audit_pending=True,GPU_requests=0))
