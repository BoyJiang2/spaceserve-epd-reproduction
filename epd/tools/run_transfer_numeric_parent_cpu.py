import pathlib,subprocess,time,os,signal,json,hashlib
root=pathlib.Path('/local/boyjiang/epd/assets/build')
run=pathlib.Path('/local/boyjiang/epd/runs/ncpu1')
env=dict(os.environ,CUDA_VISIBLE_DEVICES='0,1,2',PYTORCH_NO_CUDA_MEMORY_CACHING='1')
assert not run.exists()
with (root/'numeric_parent_sigterm.stdout').open('x') as out,(root/'numeric_parent_sigterm.stderr').open('x') as err:
 p=subprocess.Popen(['/local/boyjiang/epd/assets/envs/epd/bin/python',str(root/'test_transfer_numeric_parent_cpu.py'),str(run)],stdout=out,stderr=err,env=env)
 fd=os.pidfd_open(p.pid)
 try:
  deadline=time.monotonic()+20
  while len(list(run.glob('*.spawn.json')))<3:
   assert p.poll() is None,'parent exited early'
   assert time.monotonic()<deadline,'spawn evidence timeout'
   time.sleep(.05)
  signal.pidfd_send_signal(fd,signal.SIGTERM)
  rc=p.wait(timeout=15)
  v=json.loads((run/'terminal.json').read_text())
  assert rc!=0 and v['success'] is False and set(v['exits'])=={'E','P','D'}
  assert all(code==-signal.SIGTERM for code in v['exits'].values()),v
  assert 'import torch' not in (root/'test_transfer_numeric_parent_cpu.py').read_text()
  result=dict(parent_exit=rc,terminal=v,CPU_workers_only=True,actual_parent_SIGTERM=True,epoch=time.time(),
    source_sha256=hashlib.sha256((root/'official_transfer_numeric.py').read_bytes()).hexdigest())
  with (root/'numeric_parent_sigterm_cpu_20261104.json').open('x') as f:json.dump(result,f,indent=2)
  print(json.dumps(result))
 finally:
  if p.poll() is None:signal.pidfd_send_signal(fd,signal.SIGTERM);p.wait(timeout=15)
  os.close(fd)
