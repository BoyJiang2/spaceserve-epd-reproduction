import importlib.util,multiprocessing as mp,pathlib,os,signal,time,json,sys
root=pathlib.Path('/local/boyjiang/epd/assets/build')
spec=importlib.util.spec_from_file_location('numeric',root/'official_transfer_numeric.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=[]
a,b=mp.Pipe();b.send(17);assert m.receive(a,time.monotonic()+1)==17
try:m.receive(a,time.monotonic()+.05);raise AssertionError()
except TimeoutError:checks.append('actual pipe receive and shared deadline')
ctx=mp.get_context('spawn');p=ctx.Process(target=time.sleep,args=(.05,));p.start()
m.join_before(p,time.monotonic()+3);checks.append('actual spawn join exit0')
p=ctx.Process(target=time.sleep,args=(10,));p.start();fd=os.pidfd_open(p.pid)
try:
 try:m.join_before(p,time.monotonic()+.05);raise AssertionError()
 except TimeoutError:pass
 m.stop_child(p,fd,signal.SIGTERM);p.join(3)
 assert p.exitcode==-signal.SIGTERM and not p.is_alive()
 checks.append('actual own pidfd TERM after shared join timeout')
finally:
 if p.is_alive():m.stop_child(p,fd,signal.SIGKILL);p.join(2)
 os.close(fd)
class ObservedLive:
 def is_alive(self):return True
original=m.signal.pidfd_send_signal
def gone(*args):raise ProcessLookupError('injected exit race')
m.signal.pidfd_send_signal=gone
try:m.stop_child(ObservedLive(),123,signal.SIGTERM)
finally:m.signal.pidfd_send_signal=original
checks.append('injected ProcessLookupError exit race does not abort cleanup')
old=signal.signal(signal.SIGTERM,m.interrupt)
try:
 try:signal.raise_signal(signal.SIGTERM);raise AssertionError()
 except TimeoutError:checks.append('actual POSIX SIGTERM becomes finally-compatible exception')
finally:signal.signal(signal.SIGTERM,old)
assert 'torch' not in sys.modules
v=dict(checks=checks,all_child_processes_terminal=True,torch_imported=False,GPU=False,epoch=time.time())
with (root/'official_transfer_numeric_cpu_v2_20261104.json').open('x') as f:json.dump(v,f,indent=2)
print(json.dumps(v))
