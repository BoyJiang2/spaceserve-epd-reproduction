"""One exact CPU-only relocation unit with mandatory prior API byte verification."""
import base64,hashlib,json,shlex,subprocess,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent
R=B.parents[1]/'work/repository-upload/checkout'
phase=sys.argv[1];assert phase in ('apply','verify')
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True,timeout=45).strip()
assert subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=R,text=True,timeout=45).split()[0]==commit
source=subprocess.check_output(['git','show',commit+':tools/relocate_epd_assets_cpu.py'],cwd=R,timeout=15);digest=hashlib.sha256(source).hexdigest()
assert digest=='d403e7df8ab3b87406a5e841a3f41ff487f5f76a0ec7843c88786d1327604363'
config=subprocess.check_output(['git','show',commit+':epd/migration/qjh003-asset-relocation.json'],cwd=R,timeout=15)
assert hashlib.sha256(config).hexdigest()=='afab6795c25600d7fdfa3de215e30ab97ae367d81deb3897cc2a7f29f3e09a66'
verified=json.loads((B/('epd-relocation-'+phase+'-remote-verified.json')).read_bytes())
assert verified['commit']==commit and verified['source_sha256']==digest and verified['source_bytes']==len(source) and verified['config_sha256']==hashlib.sha256(config).hexdigest() and 0<=int(time.time()*1000)-verified['observed_ms']<=300000
r=subprocess.run([sys.executable,'-X','utf8','C:/Users/23520/.codex/skills/gputime-booking-agent/scripts/gputime_agent.py','snapshot'],capture_output=True,timeout=45);r.check_returncode();s=json.loads(r.stdout)
proof=dict(origin='gputime_read_only_api',read_only=True,observed_ms=int(time.time()*1000),resources=[{k:r[k] for k in ('id','node','active','gpu_count')} for r in s['resources'] if r['id']=='h20/qjh003'],bookings=[{k:b.get(k) for k in ('id','node','resource_id','kind','user','start_ms','end_ms')} for b in s['bookings'] if b.get('resource_id')=='h20/qjh003' and b.get('kind')!='gpu'])
wire=json.dumps(dict(phase=phase,booking=proof,config=base64.b64encode(config).decode())).encode()
wrapper='import base64,hashlib;source=base64.b64decode('+repr(base64.b64encode(source).decode())+');assert hashlib.sha256(source).hexdigest()=='+repr(digest)+';exec(compile(source,"<reviewed-cpu-relocation>","exec"))'
seconds=120 if phase=='apply' else 60
a=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=15','-l','boyjiang','qjh003','taskset -c 50 nice -n 10 timeout --foreground --signal=TERM --kill-after=30s '+str(seconds)+'s /usr/bin/python3 -I -S -B -c '+shlex.quote(wrapper)]
D=B/('epd-relocation-'+phase);D.mkdir(exist_ok=False);(D/'input.json').write_bytes(wire);(D/'command.json').write_text(json.dumps(dict(argv=a,commit=commit,source_sha256=digest,config_sha256=hashlib.sha256(config).hexdigest(),payload_sha256=hashlib.sha256(wire).hexdigest()),indent=2),encoding='utf8')
with (D/'stdout.json').open('xb') as o,(D/'stderr.log').open('xb') as e:
 r=subprocess.run(a,input=wire,stdout=o,stderr=e,timeout=seconds+55)
(D/'exit.json').write_text(json.dumps(dict(exit_code=r.returncode,finished_ms=int(time.time()*1000))),encoding='utf8');print(phase,'actual exit',r.returncode);r.check_returncode()
