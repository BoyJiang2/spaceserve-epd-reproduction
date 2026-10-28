import base64,datetime,hashlib,json,os,shlex,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
REPO=BASE.parents[1]/"work/repository-upload/checkout"
SSH=["ssh","-o","BatchMode=yes","-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=15","-l","boyjiang","qjh003"]
def save(name,data):
 with (BASE/name).open("x",encoding="utf8") as f:json.dump(data,f,indent=2)
def sha(raw):return hashlib.sha256(raw).hexdigest()
commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip()
assert json.loads((BASE/"environment-batches-publication-verified.json").read_bytes())["commit"]==commit
wrapper=(BASE/"environment-batches-wrapper.py").read_text()
assert sha(wrapper.encode())=="70760e66519615ba6c4adee147aefbc33b66e9d96077d5cf366df19475838a85"
modules=[]
for name,digest in [("migrate_code_cpu","9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405"),("build_space_environment_cpu","e9f8806be7bdc00b643976acf867573c24ff961d2ffb6f86b29e16409ad8ad71")]:
 raw=subprocess.check_output(["git","show",commit+":tools/"+name+".py"],cwd=REPO);assert sha(raw)==digest
 modules.append(dict(name=name,sha256=digest,base64=base64.b64encode(raw).decode()))
old=json.loads((BASE/"env-action-bootstrap-payload.json").read_bytes());inputs=old["inputs"]
save("environment-batches-controller.json",dict(driver_pid=os.getpid(),started_ms=int(time.time()*1000),tool_commit=commit,stop_on_failure=True))
progress=[]
for action in tuple(f"{kind}-{part:02}" for kind in ("lock","install") for part in range(1,11))+("framework","verify"):
 prefix="environment-batches-"+action
 api=subprocess.run([sys.executable,"-X","utf8","C:/Users/23520/.codex/skills/gputime-booking-agent/scripts/gputime_agent.py","snapshot"],capture_output=True,timeout=45);assert api.returncode==0
 snap=json.loads(api.stdout);now=int(time.time()*1000)
 proof=dict(origin="gputime_read_only_api",read_only=True,observed_ms=now,resources=[dict(id=r["id"],node=r["node"],active=r["active"]) for r in snap["resources"] if r["id"]=="h20/qjh003"],bookings=[r for r in snap["bookings"] if r["id"]=="bk-20261028T0925-0332cf80"])
 save(prefix+"-booking.json",proof)
 admission="""import json,os,socket,time,shutil
from pathlib import Path
root=Path('/local/boyjiang/spaceserve')
rows=[]
for f in Path('/proc').iterdir():
 if not f.name.isdigit():continue
 try:
  if f.stat().st_uid!=2147:continue
  if os.sched_getaffinity(int(f.name))=={50}:rows.append(int(f.name))
 except (FileNotFoundError,ProcessLookupError):pass
paths=[root/'staging/env-build-batched/%s.claim.json']
if '%s'=='lock-01':paths += [root/'staging/env-build-batched']
print(json.dumps(dict(observed_ms=int(time.time()*1000),host=socket.gethostname(),uid=os.getuid(),boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),cpu50=rows,free=shutil.disk_usage(root).free,existing=[str(p) for p in paths if os.path.lexists(p)])))"""%(action,action)
 before=int(time.time()*1000);r=subprocess.run(SSH+["/usr/bin/python3 -I -S -B -c "+shlex.quote(admission)],capture_output=True,timeout=35);after=int(time.time()*1000)
 (BASE/(prefix+"-admission.stdout.log")).write_bytes(r.stdout);(BASE/(prefix+"-admission.stderr.log")).write_bytes(r.stderr)
 assert r.returncode==0
 actual=json.loads(r.stdout);assert actual['host']=='qjh003' and actual['uid']==2147 and actual['boot']=='65f52a67-afe4-4919-8646-4694255b48ee' and not actual['cpu50'] and not actual['existing'] and actual['free']>=120*1024**3 and before-2000<=actual['observed_ms']<=after+2000
 save(prefix+"-admission.json",dict(actual=actual,local_before_ms=before,local_after_ms=after,passed=True))
 data=dict(action=action,tool_commit=commit,runtime_commit="a3f03b9dd5956db92add454f9b3afd5663f84609",booking=proof,inputs=inputs,modules=modules);wire=json.dumps(data).encode();assert len(wire)<=100000
 with (BASE/(prefix+"-payload.json")).open("xb") as payload_file:payload_file.write(wire)
 assert sha((BASE/(prefix+"-payload.json")).read_bytes())==sha(wire)
 argv=SSH+["taskset -c 50 nice -n 10 timeout --signal=TERM --kill-after=120s 240s /usr/bin/python3 -I -S -B -c "+shlex.quote(wrapper)]
 save(prefix+"-command.json",dict(argv=argv,payload_sha256=sha(wire)))
 started=time.monotonic()
 with (BASE/(prefix+".stdout.log")).open('xb') as out,(BASE/(prefix+".stderr.log")).open('xb') as err:
  p=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=out,stderr=err)
  creation=subprocess.check_output(['powershell','-NoProfile','-Command',"(Get-Process -Id "+str(p.pid)+").StartTime.ToUniversalTime().ToString('o')"],text=True).strip()
  save(prefix+"-controller.json",dict(pid=p.pid,created_utc=creation))
  try:p.communicate(wire,timeout=390)
  except subprocess.TimeoutExpired:
   save(prefix+"-unknown.json",dict(state='OBSERVER_TIMEOUT_UNKNOWN_DO_NOT_RESTART'));raise
 result=dict(action=action,exit_code=p.returncode,elapsed_seconds=time.monotonic()-started,tool_commit=commit)
 save(prefix+"-exit.json",result);progress.append(result)
 (BASE/'environment-batches-progress.json').write_text(json.dumps(progress,indent=2))
 print(json.dumps(result),flush=True)
 if p.returncode:sys.exit(p.returncode)
save('environment-batches-sequence-complete.json',dict(actions=progress,actual_asset_audit_pending=True,GPU_requests=0))
