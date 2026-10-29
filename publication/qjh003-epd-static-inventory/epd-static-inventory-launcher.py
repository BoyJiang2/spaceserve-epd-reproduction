import base64,hashlib,json,shlex,subprocess,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent
R=B.parents[1]/'work/repository-upload/checkout'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
assert subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=R,text=True).split()[0]==commit
source=subprocess.check_output(['git','show',commit+':tools/inspect_epd_assets_cpu.py'],cwd=R)
assert hashlib.sha256(source).hexdigest()=='665e1ca755f624b8b132e6a48292c5da082f3f4731bfd047c36f2b48405b0324'
snapshot=subprocess.run([sys.executable,'-X','utf8','C:/Users/23520/.codex/skills/gputime-booking-agent/scripts/gputime_agent.py','snapshot'],capture_output=True,timeout=45);snapshot.check_returncode();s=json.loads(snapshot.stdout)
proof=dict(origin='gputime_read_only_api',read_only=True,observed_ms=int(time.time()*1000),resources=[{k:r[k] for k in ('id','node','active','gpu_count')} for r in s['resources'] if r['id']=='h20/qjh003'],bookings=[{k:b[k] for k in ('id','node','resource_id','kind','user','start_ms','end_ms')} for b in s['bookings'] if b['id']=='bk-20261028T0925-0332cf80'])
capture=B/'successful-model-originals/space-http-20261029/evidence/model-attempt1-terminal.json'
wire=json.dumps(dict(booking=proof,space_capture_sha256=hashlib.sha256(capture.read_bytes()).hexdigest())).encode()
wrapper="import base64,hashlib;source=base64.b64decode("+repr(base64.b64encode(source).decode())+");assert hashlib.sha256(source).hexdigest()=='665e1ca755f624b8b132e6a48292c5da082f3f4731bfd047c36f2b48405b0324';exec(compile(source,'<reviewed-static-inventory>','exec'))"
argv=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=15','-l','boyjiang','qjh003','taskset -c 50 nice -n 10 timeout --foreground --signal=TERM --kill-after=30s 60s /usr/bin/python3 -I -S -B -c '+shlex.quote(wrapper)]
D=B/'epd-static-inventory';D.mkdir(exist_ok=False)
(D/'command.json').write_text(json.dumps(dict(argv=argv,source_commit=commit,source_sha256=hashlib.sha256(source).hexdigest(),payload_sha256=hashlib.sha256(wire).hexdigest()),indent=2),encoding='utf8');(D/'input.json').write_bytes(wire)
with (D/'stdout.json').open('xb') as o,(D/'stderr.log').open('xb') as e:
 result=subprocess.run(argv,input=wire,stdout=o,stderr=e,timeout=115)
(D/'exit.json').write_text(json.dumps(dict(exit_code=result.returncode,finished_ms=int(time.time()*1000))),encoding='utf8');print('static inventory exit',result.returncode);result.check_returncode()
