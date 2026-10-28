"""Fixed numeric/model launches with independent phase Gates and explicit mask compatibility."""
import base64,hashlib,json,os,secrets,signal,subprocess,sys,time,types
from pathlib import Path
ROOT=Path('/local/boyjiang/spaceserve')
RUN_ID='space-http-20261029'
RUN=ROOT/'runs'/RUN_ID
BOOT='65f52a67-afe4-4919-8646-4694255b48ee'
def supervise(helper,argv,environment,stream,check,budget=900):
    started=time.monotonic();hard=started+budget+120;known={};signals=[];requested=[]
    ticks=int(time.clock_gettime(time.CLOCK_BOOTTIME)*os.sysconf('SC_CLK_TCK'))-1
    previous={n:signal.getsignal(n) for n in (signal.SIGTERM,signal.SIGINT)}
    for number in previous:signal.signal(number,lambda n,f:requested.append(n))
    child=None;failure=None
    def current():
        if child is not None:child.poll()
        found=helper.select_owned(helper.process_records(ticks),known,environment['REPRO_CPU_NONCE'],ticks)
        known.update(found);return found
    def send(pid,row,number):
        try:handle=os.pidfd_open(pid)
        except ProcessLookupError:return
        try:
            actual=helper.process_records(ticks).get(pid)
            if actual is None:return
            if actual['uid']!=row['uid'] or actual['start_ticks']!=row['start_ticks']:raise ValueError('PID identity changed; refuse signal')
            signal.pidfd_send_signal(handle,number);signals.append(dict(pid=pid,start_ticks=row['start_ticks'],signal=number))
        except ProcessLookupError:pass
        finally:os.close(handle)
    try:
        child=subprocess.Popen(argv,env=environment,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        record=helper.process_records(ticks).get(child.pid)
        if record is None:raise ValueError('Actual entry identity absent')
        known[child.pid]=record
        while child.poll() is None:
            current();check()
            if requested or time.monotonic()>=started+budget:raise TimeoutError('Phase exit requested or work budget')
            time.sleep(.1)
        if child.returncode:raise RuntimeError('Numeric entry exit '+str(child.returncode))
    except BaseException as error:failure=error
    finally:
        for number in previous:signal.signal(number,signal.SIG_IGN)
        try:
            remaining=current()
            if remaining:
                # Ask only the actual entry first, allowing launcher/finally/MPS recovery.
                if child is not None and child.pid in remaining:send(child.pid,remaining[child.pid],signal.SIGTERM)
                until=min(time.monotonic()+90,hard-20)
                while current() and time.monotonic()<until:time.sleep(.1)
                for pid,row in current().items():send(pid,row,signal.SIGTERM)
                until=min(time.monotonic()+10,hard-5)
                while current() and time.monotonic()<until:time.sleep(.1)
                for pid,row in current().items():send(pid,row,signal.SIGKILL)
                if child is not None and child.poll() is None:child.wait(timeout=max(.1,hard-time.monotonic()))
            remaining=current()
            unknown=[row for pid,row in helper.process_records(ticks).items()
                     if row.get('nonce')==environment['REPRO_CPU_NONCE'] and row.get('root')==str(helper.RUN)
                     and row.get('run_id')==helper.RUN_ID and pid not in remaining]
            stream.write(('\n'+json.dumps(dict(registered=list(known.values()),signals=signals,remaining=list(remaining.values()),unknown_marked=unknown,exit_code=None if child is None else child.returncode))+'\n').encode());stream.flush()
            if remaining or unknown:raise RuntimeError('Numeric process release unconfirmed')
        finally:
            for number,handler in previous.items():signal.signal(number,handler)
    if failure is not None:raise failure

def main():
    data=json.load(sys.stdin);phase=data.get('phase','numeric')
    if phase not in ('numeric','model'):raise ValueError('Numeric/model phases only')
    budget=900 if phase=='numeric' else 1800
    modules=[]
    for name,digest in [('migrate_code_cpu','9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405'),('validate_space_cpu','c9d895c8567fac7f2248c8af63996e6eb4b60080edf493b51002c1c4da4a641b')]:
        raw=base64.b64decode(data[name],validate=True)
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Supervisor source changed')
        module=types.ModuleType(name);sys.modules[name]=module
        exec(compile(raw,name,'exec'),module.__dict__);modules.append(module)
    migration,helper=modules;helper.RUN_ID=RUN_ID;helper.RUN=RUN
    migration.booking(data['booking'],int(time.time()*1000));migration.validate_executor()
    snapshot=data['booking'];now=int(time.time()*1000)
    tickets=[b for b in snapshot['bookings'] if b.get('id')=='bk-20261028T0925-cb01ec55']
    expected=dict(id='bk-20261028T0925-cb01ec55',resource_id='h20/qjh003',node='qjh003',user='boyjiang',kind='gpu',start_ms=1793192400000,end_ms=1793235600000)
    if len(tickets)!=1 or any(tickets[0].get(k)!=v for k,v in expected.items()) or now+(budget+120)*1000>expected['end_ms']:raise ValueError('Fresh exact GPU booking required')
    def check():
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT or int(time.time()*1000)+120000>=expected['end_ms']:raise ValueError('Boot/window boundary')
    check()
    if (ROOT/'repo/.git/HEAD').read_text().strip()!='beadff9c4cc4693cd2ea8675020f757e313659e8':raise ValueError('Runtime HEAD changed')
    if migration.sha(ROOT/'assets/manifest.json')!=helper.ASSETS_SHA:raise ValueError('Assets manifest changed')
    for path in (RUN,ROOT/'staging/gpu-execution-http',ROOT/'tmp/cpu'):migration.real_ancestry(path)
    execution=ROOT/'staging/gpu-execution-http';execution.mkdir(mode=0o700,exist_ok=True)
    evidence=execution/phase
    marker='NUMERIC_STARTED.json' if phase=='numeric' else 'MODELS_ATTEMPT1_STARTED.json'
    if evidence.exists() or (RUN/'evidence'/marker).exists():raise ValueError('Existing numeric attempt; no automatic retry')
    evidence.mkdir(mode=0o700)
    prior=json.loads((ROOT/'staging/gpu-preparation-http/cpu.terminal.json').read_bytes())
    if prior['exit_code']!=0 or prior['boot']!=BOOT or prior['run_id']!=RUN_ID or prior['log_sha256']!=migration.sha(ROOT/'staging/gpu-preparation-http/cpu.log'):raise ValueError('Actual CPU success missing')
    config=json.loads((RUN/'configs/project.json').read_bytes())
    proof=ROOT/'staging/sm-driver13-port/terminal.json'
    if config.get('mask_off')!=56 or config.get('mask_compatibility_proof_sha256')!=migration.sha(proof) or migration.sha(proof)!='f8cff8a12b7a613d2ccb1241f8126945fef5935425c13f1851ca961957b89aa4' or json.loads(proof.read_bytes()).get('passed') is not True:raise ValueError('Unverified mask compatibility setting')
    nonce=secrets.token_hex(24);environment=helper.child_environment(nonce)
    environment['MASK_OFF']='56'
    environment['SPACESERVE_CONFIG']=str(RUN/'configs/project.json')
    environment['EXP_ROOT']=str(RUN)
    environment['REPRO_PHASE']=phase
    environment['PATH']='/usr/local/cuda-12.8/bin:/usr/bin:/bin'
    migration.exclusive_json(evidence/'claim.json',dict(pid=os.getpid(),start_ticks=helper.process_records(0)[os.getpid()]['start_ticks'],boot=BOOT,run_id=RUN_ID,phase=phase,started_ms=int(time.time()*1000),config_sha256=migration.sha(RUN/'configs/project.json'),actual_environment={k:environment[k] for k in ('MASK_OFF','SPACESERVE_CONFIG','EXP_ROOT','REPRO_PHASE','CUDA_VISIBLE_DEVICES')},compatibility_proof_sha256=migration.sha(proof)))
    argv=['/usr/bin/python3','-I','-S','-B',str(ROOT/'repo/spaceserve/runtime/entry.py'),phase,'--config',str(RUN/'configs/project.json')]
    started=time.monotonic();result=dict(exit_code=1,boot=BOOT,run_id=RUN_ID,phase=phase,mask_off=56,compatibility_proof_sha256=migration.sha(proof))
    try:
        with (evidence/'numeric.log').open('xb') as stream:
            supervise(helper,argv,environment,stream,check,budget)
        result['exit_code']=0
    except BaseException as error:result['error']=repr(error);raise
    finally:
        result.update(finished_ms=int(time.time()*1000),log_sha256=migration.sha(evidence/'numeric.log'))
        migration.exclusive_json(evidence/'terminal.json',result)
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
