"""Actual local HTTP and POSIX timeout tests; no torch or GPU."""
import base64,hashlib,http.server,json,pathlib,subprocess,sys,threading,time
root=pathlib.Path('/local/boyjiang/spaceserve/assets')
base=root/'c4-nvtx-cpu-20261104'
base.mkdir()
client=root/'official_space_c4_nvtx_client.py'
finalizer=root/'official_space_c4_finalize.py'
images=['000328','000400','000623','001146']
digests=[hashlib.sha256(pathlib.Path('/local/boyjiang/epd/assets/dataset/COCO_val2014_000000'+x+'.jpg').read_bytes()).hexdigest() for x in images]
template=dict(model='reproduction-qwen2-vl7b',messages=[dict(role='user',content=[dict(type='image_url',image_url=dict(url='data:image/jpeg;base64,')),dict(type='text',text='Describe the image.')])],n=1,temperature=0.0,top_p=1.0,max_tokens=128,ignore_eos=True,stream=False)
results=[]
for mode in ['normal','http500','short','timeout']:
 run=base/mode;run.mkdir();(run/'request.json').write_text(json.dumps(template))
 observed=[];lock=threading.Lock();ready=threading.Event()
 class Handler(http.server.BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_POST(self):
   data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
   digest=hashlib.sha256(base64.b64decode(data['messages'][0]['content'][0]['image_url']['url'].split(',',1)[1])).hexdigest()
   with lock:
    observed.append(digest)
    if len(observed)==4:ready.set()
   assert ready.wait(3)
   if mode=='timeout' and digest==digests[0]:time.sleep(2)
   status=500 if mode=='http500' and digest==digests[0] else 200
   body=json.dumps(dict(choices=[dict(message=dict(content=digest),finish_reason='length')],usage=dict(completion_tokens=127 if mode=='short' and digest==digests[0] else 128))).encode()
   try:
    self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
   except (BrokenPipeError,ConnectionResetError):pass
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
 thread=threading.Thread(target=server.serve_forever);thread.start()
 command=[sys.executable,'-I','-S','-B',str(client),'http://127.0.0.1:'+str(server.server_port)+'/v1/chat/completions',str(run)]
 if mode=='timeout':command=['timeout','--signal=TERM','--kill-after=1s','.7s']+command
 try:
  with (run/'client.stdout').open('x') as out,(run/'client.stderr').open('x') as err:p=subprocess.run(command,stdout=out,stderr=err,timeout=6)
  assert sorted(observed)==sorted(digests)
  old={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in run.glob('client-*.record.json')}
  subprocess.run([sys.executable,'-I','-S','-B',str(finalizer),str(run),str(p.returncode)],check=True,stdout=subprocess.DEVNULL)
  assert all(hashlib.sha256((run/name).read_bytes()).hexdigest()==sha for name,sha in old.items())
  final=json.loads((run/'client-finalization.json').read_text())
  if mode=='normal':
   assert p.returncode==0 and final['measurement_accepted']
   batch=json.loads((run/'batch-result.json').read_text())
   assert batch['successes']==4 and batch['observed_peak_inflight']==4
   for i,r in enumerate(batch['requests']):
    assert r['output']==digests[i] and r['actual_output_tokens']==128
    assert r['client_ttft_s'] is None and r['server_tpot_s'] is None
  elif mode in ['http500','short']:
   assert p.returncode==1 and not final['measurement_accepted']
   assert json.loads((run/'batch-result.json').read_text())['successes']==3
   assert (run/'client-0.response.json').exists()
  else:
   assert p.returncode==124 and not final['measurement_accepted'] and final['incomplete_indices']==[0]
   recovery=json.loads((run/'client-0.recovery-record.json').read_text())
   assert recovery['completed_epoch'] is None and recovery['client_e2e_s'] is None
  results.append(dict(mode=mode,exit=p.returncode,finalizer=final,original_records_unchanged=True))
 finally:
  server.shutdown();server.server_close();thread.join(3);assert not thread.is_alive()
assert 'torch' not in sys.modules
v=dict(results=results,GPU=False,torch_imported=False,epoch=time.time())
(root/'space_c4_nvtx_cpu_20261104.json').open('x').write(json.dumps(v,indent=2))
print(json.dumps(dict(modes=[r['mode'] for r in results],passed=4,GPU=False)))
