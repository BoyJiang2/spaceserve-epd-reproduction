"""One actual CPU-only TERM/finally regression for the numeric supervisor."""
import base64,hashlib,json,os,secrets,signal,socket,sys,threading,time,types
from pathlib import Path

def main():
    assert socket.gethostname()=='qjh003' and os.getuid()==2147 and os.sched_getaffinity(0)=={50}
    assert os.getpriority(os.PRIO_PROCESS,0)==10
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='65f52a67-afe4-4919-8646-4694255b48ee'
    data=json.load(sys.stdin);loaded=[]
    for name in ('migrate_code_cpu','validate_space_cpu','run_space_numeric'):
        raw=base64.b64decode(data[name],validate=True)
        assert hashlib.sha256(raw).hexdigest()==data['hashes'][name]
        module=types.ModuleType(name);sys.modules[name]=module
        exec(compile(raw,name,'exec'),module.__dict__);loaded.append(module)
    migration,helper,numeric=loaded
    migration.booking(data['booking'],int(time.time()*1000));migration.validate_executor()
    root=Path('/local/boyjiang/spaceserve/staging/numeric-cleanup-test')
    migration.real_ancestry(root);root.mkdir(mode=0o700)
    helper.RUN=root;helper.RUN_ID='numeric-cleanup-test'
    environment=helper.child_environment(secrets.token_hex(24))
    child="""import os,signal,sys,time
from pathlib import Path
root=Path(sys.argv[1])
def stopped(n,f):raise SystemExit(0)
signal.signal(signal.SIGTERM,stopped)
try:
 (root/'ready').write_text(str(os.getpid()))
 time.sleep(20)
finally:
 time.sleep(3)
 (root/'finally-complete').write_text('real finally completed after 3 seconds')
"""
    errors=[]
    def trigger():
        deadline=time.monotonic()+10
        while not (root/'ready').exists() and time.monotonic()<deadline:time.sleep(.02)
        if not (root/'ready').exists():errors.append('child readiness missing');return
        os.kill(os.getpid(),signal.SIGTERM)
    thread=threading.Thread(target=trigger);thread.start();started=time.monotonic();expected=False
    try:
        with (root/'supervision.log').open('xb') as stream:
            numeric.supervise(helper,['/usr/bin/python3','-I','-S','-B','-c',child,str(root)],environment,stream,lambda:None)
    except TimeoutError:expected=True
    thread.join(timeout=1)
    rows=[json.loads(line) for line in (root/'supervision.log').read_text().splitlines() if line.startswith('{')]
    assert expected and not errors and not thread.is_alive()
    assert (root/'finally-complete').read_text()=='real finally completed after 3 seconds'
    assert 3<=time.monotonic()-started<30 and rows[-1]['remaining']==[] and rows[-1]['unknown_marked']==[]
    assert len(rows[-1]['signals'])==1 and rows[-1]['signals'][0]['signal']==signal.SIGTERM
    result=dict(passed=True,tests_passed=1,tests_skipped=0,elapsed_seconds=time.monotonic()-started,scope='actual POSIX CPU only; no CUDA/MPS/model',registered=rows[-1]['registered'],signals=rows[-1]['signals'])
    migration.exclusive_json(root/'result.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
