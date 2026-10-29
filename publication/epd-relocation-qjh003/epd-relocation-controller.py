"""One exact CPU relocation unit; remote API proof is mandatory before execution."""
import base64,hashlib,json,shlex,subprocess,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent
R=B.parents[1]/'work/repository-upload/checkout'
phase=sys.argv[1];assert phase=='inspect'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
assert subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=R,text=True).split()[0]==commit
source=subprocess.check_output(['git','show',commit+':tools/relocate_epd_assets_cpu.py'],cwd=R);digest=hashlib.sha256(source).hexdigest()
assert digest=='8ca5723e26e0083c703d46587a57416ad7e26a7d1386f34c34fd357aa1fcf28c'
verified=json.loads((B/'epd-relocation-remote-source-verified.json').read_bytes())
assert verified['commit']==commit and verified['sha256']==digest and verified['bytes']==len(source) and 0<=int(time.time()*1000)-verified['observed_ms']<=300000
r=subprocess.run([sys.executable,'-X','utf8','C:/Users/23520/.codex/skills/gputime-booking-agent/scripts/gputime_agent.py','snapshot'],capture_output=True,timeout=45);r.check_returncode();s=json.loads(r.stdout)
proof=dict(origin='gputime_read_only_api',read_only=True,observed_ms=int(time.time()*1000),resources=[{k:r[k] for k in ('id','node','active','gpu_count')} for r in s['resources'] if r['id']=='h20/qjh003'],bookings=[{k:b[k] for k in ('id','node','resource_id','kind','user','start_ms','end_ms')} for b in s['bookings'] if b['id']=='bk-20261029T0057-e2efd603'])
wire=json.dumps(dict(phase=phase,booking=proof)).encode()
wrapper='import base64,hashlib;source=base64.b64decode('+repr(base64.b64encode(source).decode())+');assert hashlib.sha256(source).hexdigest()=='+repr(digest)+';exec(compile(source,"<reviewed-cpu-relocation>","exec"))'
a=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=15','-l','boyjiang','qjh003','taskset -c 50 nice -n 10 timeout --foreground --signal=TERM --kill-after=30s 60s /usr/bin/python3 -I -S -B -c '+shlex.quote(wrapper)]
D=B/('epd-relocation-'+phase);D.mkdir(exist_ok=False);(D/'input.json').write_bytes(wire);(D/'command.json').write_text(json.dumps(dict(argv=a,commit=commit,source_sha256=digest,payload_sha256=hashlib.sha256(wire).hexdigest()),indent=2),encoding='utf8')
with (D/'stdout.json').open('xb') as o,(D/'stderr.log').open('xb') as e:
 r=subprocess.run(a,input=wire,stdout=o,stderr=e,timeout=115)
(D/'exit.json').write_text(json.dumps(dict(exit_code=r.returncode,finished_ms=int(time.time()*1000))),encoding='utf8');print(phase,'actual exit',r.returncode);r.check_returncode()
