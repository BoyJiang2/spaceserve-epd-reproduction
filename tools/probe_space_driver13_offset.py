"""Bounded official MASK_OFF native diagnostic, never a model or MPS launch."""
import base64,fcntl,hashlib,json,os,stat,subprocess,sys,time,types
from pathlib import Path
ROOT=Path('/local/boyjiang/spaceserve')
OUT=ROOT/'staging/sm-driver13-port'
UUID='GPU-dd8ab4ed-e34e-4141-ced9-271897da8282'
BOOT='65f52a67-afe4-4919-8646-4694255b48ee'
INPUTS={'runs/space-003-20261029/results/numeric/probe_sm_mask':'e1c739868516e399c0499419d7559d0bdef73786dd00c59a6c27b9e633535797','runs/space-003-20261029/scripts/probe_sm_mask.cu':'2919f83d0988ec23576199389b2d3b2765944188f9526393a34f8daea21e1935','assets/build/libsmctrl.so':'529e2502f633b0d7ef07db2848c64e42154cea73992a794c27a31d0361e5e7c5'}
def validate(raw):
    rows=[json.loads(line) for line in raw.decode().splitlines() if line.startswith('{')]
    if rows[0].get('physical_sms')!=78 or rows[0].get('cuda_driver_version')!=13000:raise ValueError('Unexpected physical GPU/driver')
    labels=['unmasked','spaceserve_encoder_mask_0xfff','restored_to_zero_mask','reapplied_encoder_mask']
    if len(rows)!=6 or [r.get('label') for r in rows[1:5]]!=labels:raise ValueError('Probe record sequence differs')
    values=[set(r['sm_ids']) for r in rows[1:5]]
    if any(r['sm_count']!=len(r['sm_ids']) or len(r['sm_ids'])!=len(set(r['sm_ids'])) for r in rows[1:5]):raise ValueError('Malformed SM record')
    before,after,restored,reapplied=values
    passed=bool(after) and before==set(range(78)) and after<before and restored==before and reapplied==after
    if rows[-1].get('mask_effect_observed') is not passed:raise ValueError('Probe result inconsistent')
    return passed,rows

def main():
    data=json.load(sys.stdin);raw=base64.b64decode(data['migration_source'],validate=True)
    if hashlib.sha256(raw).hexdigest()!='9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405':raise ValueError('Supervisor source differs')
    migration=types.ModuleType('migration');exec(compile(raw,'migrate_code_cpu','exec'),migration.__dict__)
    started=time.monotonic();deadline=started+180
    tickets=[b for b in data['booking']['bookings'] if b.get('id')=='bk-20261028T0925-cb01ec55']
    expected=dict(id='bk-20261028T0925-cb01ec55',resource_id='h20/qjh003',node='qjh003',user='boyjiang',kind='gpu',start_ms=1793192400000,end_ms=1793235600000)
    if len(tickets)!=1 or any(tickets[0].get(k)!=v for k,v in expected.items()):raise ValueError('Exact owned GPU ticket required')
    def check():
        migration.booking(data['booking'],int(time.time()*1000));migration.validate_executor()
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT:raise ValueError('Boot changed')
        if time.monotonic()>=deadline:raise TimeoutError('180 second total diagnostic budget')
    def idle(cleanup=False):
        if not cleanup:check()
        elif time.monotonic()>started+300:raise TimeoutError('Diagnostic cleanup budget')
        limit=started+300 if cleanup else deadline
        def remaining():
            value=limit-time.monotonic()
            if value<=0:raise TimeoutError('GPU query deadline')
            return min(10,value)
        gpu=subprocess.check_output(['nvidia-smi','--id=0','--query-gpu=uuid,memory.used','--format=csv,noheader,nounits'],text=True,timeout=remaining())
        apps=subprocess.check_output(['nvidia-smi','--id=0','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=remaining())
        parts=[s.strip() for s in gpu.strip().split(',')]
        if parts!=[UUID,'0'] or apps.strip():raise ValueError('GPU UUID/busy/release mismatch')
        if cleanup:
            if time.monotonic()>=limit:raise TimeoutError('Cleanup GPU query deadline')
        else:check()
        return dict(gpu=gpu,compute_apps=apps,observed_ms=int(time.time()*1000))
    check();migration.real_ancestry(OUT)
    if OUT.exists():raise ValueError('Existing diagnostic; no retry')
    for name,digest in INPUTS.items():
        path=ROOT/name
        for parent in (path,*path.parents):
            if parent.is_symlink():raise ValueError('Linked input ancestry')
        if path.stat().st_uid!=2147 or migration.sha(path)!=digest:raise ValueError('Pinned source/binary/library differs')
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit():continue
        try:
            if (folder/'comm').read_text().startswith('nvidia-cuda-mps') and (folder/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':raise ValueError('Existing MPS; native diagnostic refused')
        except (FileNotFoundError,ProcessLookupError):pass
    lock=ROOT.parent/'.spaceserve-epd-host.lock';fd=os.open(lock,os.O_RDWR|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if info.st_uid!=2147 or not stat.S_ISREG(info.st_mode):raise ValueError('Host lock identity differs')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);initial=idle();OUT.mkdir(mode=0o700)
        migration.exclusive_json(OUT/'claim.json',dict(pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],started_ms=int(time.time()*1000),boot=BOOT,uuid=UUID,inputs=INPUTS,booking=data['booking'],initial=initial))
        wrapper="import json,os,sys,time; from pathlib import Path; p=Path('/proc/self/stat'); ticks=int(p.read_text().rsplit(')',1)[1].split()[19]); btime=int(next(line.split()[1] for line in Path('/proc/stat').read_text().splitlines() if line.startswith('btime '))); raw=json.dumps(dict(pid=os.getpid(),uid=os.getuid(),start_ticks=ticks,created_epoch=btime+ticks/os.sysconf('SC_CLK_TCK'),observed_ms=int(time.time()*1000))); f=open(sys.argv[1],'x'); f.write(raw); f.close(); os.execv(sys.argv[2],sys.argv[2:])"
        os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',HOME='/nonexistent',LC_ALL='C.UTF-8',CUDA_VISIBLE_DEVICES=UUID,TMPDIR=str(OUT))
        results=[];selected=None;failure=None
        def probe(offset,label):
            check()
            if deadline-time.monotonic()<3:raise TimeoutError('Insufficient full candidate budget')
            os.environ['MASK_OFF']=str(offset)
            with (OUT/(label+'.log')).open('xb') as stream:
                try:
                    output=migration.command_output(['/usr/bin/python3','-I','-S','-B','-c',wrapper,str(OUT/(label+'-identity.json')),str(ROOT/'runs/space-003-20261029/results/numeric/probe_sm_mask'),str(ROOT/'assets/build/libsmctrl.so')],stream,3,started+300);code=0
                except subprocess.CalledProcessError as error:
                    if error.returncode!=3:raise
                    output=error.output;code=error.returncode
            passed,rows=validate(output)
            if passed!=(code==0):raise ValueError('Exit code and SM sets disagree')
            released=idle();result=dict(offset=offset,label=label,passed=passed,exit_code=code,records=rows,released=released)
            migration.exclusive_json(OUT/(label+'.json'),result);results.append(result);return passed
        try:
            for offset in range(0,256,8):
                if probe(offset,'candidate-'+str(offset)):selected=offset;break
            if selected is not None:
                for repetition in range(3):
                    if not probe(selected,'repeat-'+str(repetition)):raise ValueError('Candidate failed independent repetition')
        except BaseException as error:failure=repr(error)
        try:final_resource=idle(cleanup=True)
        except BaseException as error:failure=failure or repr(error);final_resource=dict(release_unconfirmed=repr(error))
        result=dict(final_resource=final_resource,selected_offset=selected,passed=selected is not None and failure is None,results=results,failure=failure,elapsed_seconds=time.monotonic()-started,scope='native driver layout diagnostic only; no MPS/model/G3')
        migration.exclusive_json(OUT/'terminal.json',result);print(json.dumps(result),flush=True)
        if failure is not None:raise RuntimeError(failure)
    finally:os.close(fd)
if __name__=='__main__':main()
