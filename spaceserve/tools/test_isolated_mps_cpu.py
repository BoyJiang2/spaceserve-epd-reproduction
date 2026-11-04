"""CPU-only guards: real own processes, pidfds, fake control CLI, deadlines."""
import importlib.util,json,os,pathlib,signal,subprocess,sys,time
root=pathlib.Path('/local/boyjiang/spaceserve/assets')
base=root/'mps-cpu-20261104';base.mkdir(mode=0o700)
spec=importlib.util.spec_from_file_location('mps',root/'official_isolated_mps_numeric.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
env=dict(os.environ,EXP_ROOT=m.ROOT,REPRO_RUN_ID='cpu-fixture-only',CUDA_MPS_PIPE_DIRECTORY=str(base))
checks=[]
assert m.pid_list('12\n34\n')=={12,34}
for text in ['bad protocol','0','-1']:
 try:m.pid_list(text);raise RuntimeError('invalid list accepted')
 except AssertionError:pass
checks.append('PID parser rejects invalid protocol')
p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'],env=env)
fd=os.pidfd_open(p.pid)
try:
 ident=m.identity(p.pid,env,0);assert ident['pid']==p.pid and ident['uid']==os.getuid()
 for wrong,minimum in [(dict(env,REPRO_RUN_ID='foreign'),0),(env,ident['start_ticks']+1)]:
  try:m.identity(p.pid,wrong,minimum);raise RuntimeError('wrong identity accepted')
  except AssertionError:pass
 checks.append('actual own process identity and wrong RUNID/start rejection')
 m.stop(p,fd);p.wait(timeout=3);assert p.returncode==-signal.SIGTERM
 checks.append('actual own pidfd termination and wait')
finally:
 if p.poll() is None:m.stop(p,fd,signal.SIGKILL);p.wait(timeout=3)
 os.close(fd)
fake=base/'fake-control'
fake.write_text('#!/usr/bin/python3\nimport sys,time\nc=sys.stdin.readline().strip()\nif c=="slow":time.sleep(2)\nif c=="failure":print("retained failure",file=sys.stderr);sys.exit(7)\nprint("123\\n456" if c=="get_server_list" else "")\n')
fake.chmod(0o700);m.CONTROL=str(fake)
assert m.pid_list(m.rpc(env,'get_server_list',time.monotonic()+2,base))=={123,456}
try:m.rpc(env,'failure',time.monotonic()+2,base);raise RuntimeError('failure accepted')
except AssertionError:pass
try:m.rpc(env,'slow',time.monotonic()+.05,base);raise RuntimeError('deadline ignored')
except subprocess.TimeoutExpired:pass
try:m.rpc(env,'get_server_list',time.monotonic()-1,base);raise RuntimeError('expired deadline accepted')
except AssertionError:pass
checks.append('real fake-CLI stdout/stderr/nonzero/timeout/shared deadline')
old=signal.signal(signal.SIGTERM,m.interrupt)
try:
 try:signal.raise_signal(signal.SIGTERM);raise RuntimeError('SIGTERM ignored')
 except TimeoutError:pass
finally:signal.signal(signal.SIGTERM,old)
checks.append('actual POSIX SIGTERM handler exception')
assert 'torch' not in sys.modules
result=dict(checks=checks,torch_imported=False,MPS_started=False,GPU=False,epoch=time.time())
(root/'isolated_mps_cpu_20261104.json').open('x').write(json.dumps(result,indent=2))
print(json.dumps(result))
