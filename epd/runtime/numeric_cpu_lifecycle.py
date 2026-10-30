"""Finite four-scenario CPU Ray diagnostic. Not a GPU/backend entrypoint."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import traceback

from numeric_cpu_ray import load_cpu_ray
from numeric_descendants import HeadDescendants, HeadProc
from numeric_gcs import GCSActorReader
from numeric_head import construct_node, node_parameters
from numeric_cpu_receipts import publish as write
from lifecycle_policy import budgets as lifecycle_budgets, scenario_deadline, scenarios as lifecycle_scenarios, scope as lifecycle_scope


def check_cpu_port(port):
    if type(port) is not int or not 1024<=port<=65535:raise ValueError('Exact CPU TCP port required')
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as v4,socket.socket(socket.AF_INET6,socket.SOCK_STREAM) as v6:
        v6.setsockopt(socket.IPPROTO_IPV6,socket.IPV6_V6ONLY,1)
        v4.bind(('0.0.0.0',port));v6.bind(('::',port))


def control_service_exception(proc,pid):
    tools=Path(__file__).resolve().parents[2]/'tools'
    pins={'space_user_service_guard.py':'48fe3fc2bf9d4070f48db6b60b44671c40761850014f650a0f54b82678c357fd',
        'materialize_assets_cpu.py':'8ffccf7061b2ebc8ac90543d0d60c79efaf7ff87552cef8fcf1bd6555dbd0c0c',
        'migrate_code_cpu.py':'9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405'}
    for name,expected in pins.items():
        path=tools/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('Published read-only control-service validator differs')
    sys.path.insert(0,str(tools))
    from space_user_service_guard import exception
    from materialize_assets_cpu import ssh_exception
    return exception(proc,pid) or ssh_exception(proc,pid)


def small_json(path,uid):
    if path.is_symlink() or path.stat().st_uid!=uid or path.stat().st_size>16384:
        raise ValueError('Owned bounded diagnostic receipt required')
    return json.loads(path.read_bytes())


def terminate(identity,proc,record,check,*,clock=time.monotonic,sleep=time.sleep,reap=lambda:None):
    """Signal only an originally registered process through a stable handle."""
    keys=('pid','uid','proc_start_ticks','boot_id','cwd')
    def live():
        actual=proc.snapshot(identity['pid'],identity['uid'])['identity']
        if (any(actual[key]!=identity[key] for key in keys)
                or actual['environment']!=identity['environment']):
            raise ValueError('Registered CPU process identity changed')
        return actual
    check();reap()
    try:live()
    except (FileNotFoundError,ProcessLookupError):
        if proc.exists(identity['pid']):raise
        record('CPU_registered_process_absent',identity=identity)
        return dict(controlled_signal_sent=False,already_absent=True,TERM_sent=False,KILL_sent=False)
    fd=proc.open_pidfd(identity['pid'])
    try:
        live();record('CPU_TERM_intent',identity=identity);check();live()
        proc.signal_pidfd(fd,signal.SIGTERM)
        record('CPU_TERM_sent',identity=identity)
        deadline=clock()+1
        while clock()<deadline:
            check();reap()
            if not proc.exists(identity['pid']):return dict(controlled_signal_sent=True,already_absent=False,TERM_sent=True,KILL_sent=False)
            sleep(.05)
        reap();live();record('CPU_KILL_intent',identity=identity);check();live()
        proc.signal_pidfd(fd,signal.SIGKILL)
        record('CPU_KILL_sent',identity=identity)
        return dict(controlled_signal_sent=True,already_absent=False,TERM_sent=True,KILL_sent=True)
    finally:proc.close_pidfd(fd)


class Diagnostic:
    def __init__(self,root,run_id,folder,base,port,package,smoke=False):
        self.root,self.run_id,self.folder,self.base,self.port,self.package=Path(root),run_id,Path(folder),Path(base),port,Path(package)
        self.uid=os.getuid();self.proc=HeadProc();self.boot=self.proc.boot()
        self.smoke=smoke;self.started=time.monotonic()
        self.work_end,self.end=lifecycle_budgets(smoke,self.started)
        self.scenarios=lifecycle_scenarios(smoke)
        self.cleaning=False;self.cancelled=set();self.collector=None;self.processes=[];self.reader=None
        self.expected=[];self.pending_scenarios=set();self.journal=self.folder/'lifecycle.jsonl'
        with self.journal.open('x',encoding='utf8'):pass

    def record(self,event,**data):
        with self.journal.open('a',encoding='utf8') as out:
            out.write(json.dumps(dict(event=event,monotonic_s=time.monotonic(),**data))+'\n')
            out.flush();os.fsync(out.fileno())

    def check(self):
        if time.monotonic()>=(self.end if self.cleaning else self.work_end):raise TimeoutError('CPU diagnostic deadline')
        if self.cancelled and not self.cleaning:raise RuntimeError('CPU diagnostic cancelled')

    def register(self,process):
        if self.collector is None:
            values=[arg.split('=',1)[1] for arg in process.args if arg.startswith('--log_dir=')]
            if len(values)!=1:raise ValueError('First actual private GCS log directory missing')
            session=Path(values[0]).parent
            if not session.is_relative_to(self.base) or session.parent!=self.base or not session.name.startswith('session_'):
                raise ValueError('Actual selected private session escapes fresh base')
            self.collector=HeadDescendants(uid=self.uid,boot_id=self.boot,root=self.root,run_id=self.run_id,
                session=session,supervisor_pid=os.getpid(),proc=self.proc,record=self.record,check=self.check)
        self.collector.register(process)

    def poll(self):
        self.check()
        self.reap()
        self.collector.collect()

    def reap(self):
        for process in self.processes:process.poll()

    def leftovers(self):
        """Read-only detection of late children; unknown identities are never killed."""
        selected=[]
        for path in Path('/proc').iterdir():
            self.check()
            if not path.name.isdigit() or int(path.name)==os.getpid():continue
            try:
                if path.stat().st_uid!=self.uid:continue
                try:cwd=(path/'cwd').resolve(strict=True)
                except PermissionError:
                    proof=control_service_exception(Path('/proc'),int(path.name))
                    if proof is None:raise RuntimeError('Final CPU candidate cwd unconfirmed')
                    self.record('CPU_verified_control_service_exception',pid=int(path.name),proof=proof,
                        scope='cwd permission only; no signalling or project ownership grant')
                    continue
                if not cwd.is_relative_to(self.root):continue
                if self.proc.environment(int(path.name))=={'EXP_ROOT':str(self.root),'REPRO_RUN_ID':self.run_id}:
                    selected.append(self.proc.snapshot(int(path.name),self.uid))
            except (FileNotFoundError,ProcessLookupError):
                if self.proc.exists(int(path.name)):raise RuntimeError('Final CPU candidate still exists without identity')
                continue
        self.record('CPU_final_scope_inventory',selected=selected,unknown_process_signal_authorized=False)
        return selected

    def events(self,folder):
        path=folder/'driver-events.jsonl'
        if not path.exists():return []
        if path.is_symlink() or path.stat().st_uid!=self.uid or path.stat().st_size>65536:
            raise ValueError('Driver journal differs')
        raw=path.read_bytes()
        # A concurrent final write may be partial; only complete fsynced-stage
        # records are consumed after their associated exclusive receipt exists.
        return [json.loads(line) for line in raw.split(b'\n')[:-1] if line]

    def scenario(self,detached,controlled,index):
        self.poll();folder=self.folder/str(index);folder.mkdir(mode=0o700)
        spec=dict(root=str(self.root),run_id=self.run_id,session=str(self.collector.session),folder=str(folder),
            address='127.0.0.2:'+str(self.port),namespace=self.run_id,name='CPU-'+str(index),
            detached=detached,delay_seconds=15 if controlled else 0)
        write(folder/'spec.json',spec)
        script=Path(__file__).with_name('numeric_cpu_driver.py')
        loader='import runpy,sys;sys.path.insert(0,'+repr(str(script.parent))+');sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name="__main__")'
        args=[sys.executable,'-I','-B','-c',loader,str(script),
            '--session-dir='+str(self.collector.session),'--spec='+str(folder/'spec.json'),'--ray-package='+str(self.package)]
        self.record('CPU_driver_spawn_intent',spec=spec,argv=args)
        self.pending_scenarios.add(index)
        out=(folder/'stdout.log').open('xb');err=(folder/'stderr.log').open('xb')
        try:
            driver=subprocess.Popen(args,cwd=self.root,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
            self.processes.append(driver);self.register(driver)
            deadline=scenario_deadline(self.work_end,time.monotonic());expected=identity=None;stopped=actor_stopped=False;connection_observed=False
            while time.monotonic()<deadline:
                self.poll();events=self.events(folder)
                connections=[e for e in events if e['event']=='connected_existing_head']
                if len(connections)>1:raise ValueError('Duplicate driver connection fact')
                if connections and not connection_observed:
                    row=connections[0]
                    if (set(row)!={'event','monotonic_s','address','private_session','owns_processes'}
                            or row['address']!=spec['address'] or row['private_session']!=str(self.collector.session)
                            or row['owns_processes'] is not False or type(row['monotonic_s']) not in (int,float)
                            or not math.isfinite(row['monotonic_s']) or not 0<=row['monotonic_s']<=time.monotonic()):
                        raise ValueError('Actual driver connection fact differs')
                    self.record('connected_existing_head',address=row['address'],private_session=row['private_session'],
                        owns_processes=row['owns_processes'],driver_pid=driver.pid,
                        driver_event_monotonic_s=row['monotonic_s'],provenance='verified_current_driver_events')
                    connection_observed=True
                submitted=[e['expected'] for e in events if e['event']=='actor_submitted']
                if submitted and not connection_observed:raise ValueError('Actor submission before verified connection')
                if submitted and expected is None and (folder/'actor-submitted.json').exists():
                    if len(submitted)!=1:raise ValueError('Duplicate CPU actor submission')
                    expected=small_json(folder/'actor-submitted.json',self.uid)
                    if expected!=submitted[0]:raise ValueError('Durable submission and driver journal differ')
                    self.expected.append(dict(expected=expected,identity=None))
                    self.record('CPU_actor_submission_observed',expected=expected)
                entered=folder/'constructor-entered.json'
                if expected and entered.exists() and identity is None:
                    facts=small_json(entered,self.uid)
                    if any(facts.get(k)!=v for k,v in expected.items()):raise ValueError('Constructor ActorID scope differs')
                    candidate=facts['process']['identity'];known=self.collector.known.get(candidate['pid'])
                    if known is None:raise ValueError('Constructor process lacks verified original parent chain')
                    if any(candidate[k]!=known[k] for k in ('pid','uid','proc_start_ticks','boot_id','cwd','environment')):
                        raise ValueError('Constructor actual process differs from parent inventory')
                    identity=dict(known);self.expected[-1]['identity']=identity
                    self.record('CPU_actor_original_parent_verified',expected=expected,identity=identity)
                if expected and identity:
                    state=self.reader.read(expected,deadline)
                    if controlled and not stopped:
                        if driver.poll() is not None or state['state']=='DEAD' or (folder/'driver-ready.json').exists():
                            raise ValueError('Controlled exit missed live driver/creation window')
                        if facts['delay_seconds']!=15 or type(facts['constructor_monotonic_s']) not in (int,float):
                            raise ValueError('Actual constructor delay window missing')
                        def window_check():
                            self.check()
                            remaining=facts['constructor_monotonic_s']+15-time.monotonic()
                            if not 2<=remaining<=15:raise TimeoutError('Controlled constructor window expired')
                        window_check()
                        self.record('CPU_controlled_driver_exit',expected=expected,
                            constructor_monotonic_s=facts['constructor_monotonic_s'],
                            controlled_exit_intent_monotonic_s=time.monotonic(),minimum_window_remaining_s=2)
                        outcome=terminate(self.collector.known[driver.pid],self.proc,self.record,window_check,reap=self.reap)
                        if outcome.get('controlled_signal_sent') is not True:raise RuntimeError('Driver already absent; no controlled exit')
                        stopped=True
                    elif not controlled and (folder/'driver-ready.json').exists() and not (folder/'parent-observed.json').exists():
                        if state['state']!='ALIVE' or state['pid']!=identity['pid']:raise ValueError('Normal parent observation needs exact live actor')
                        actual=self.collector.observe(identity['pid'])
                        if not self.collector.same_identity(actual['identity'],identity):raise ValueError('Normal CPU actor identity changed')
                        actual_after=self.collector.stable(actual)
                        self.record('CPU_normal_live_actor_bound',GCS=state,before=actual,after=actual_after)
                        write(folder/'parent-observed.json',expected)
                        # Inventory resumes only after the held child has fully exited.
                        self.record('CPU_normal_driver_exit_wait',expected=expected,driver_pid=driver.pid,deadline=deadline)
                        while driver.poll() is None:
                            self.check()
                            if time.monotonic()>=deadline:raise TimeoutError('Normal CPU driver exit deadline')
                            time.sleep(.05)
                        self.check()
                        if time.monotonic()>=deadline:raise TimeoutError('Normal CPU driver exit deadline')
                        self.record('CPU_normal_driver_exit_observed',expected=expected,
                            driver_pid=driver.pid,driver_exit=driver.returncode)
                    if driver.poll() is not None:
                        if not controlled and driver.returncode!=0:raise RuntimeError('Normal CPU driver failed')
                        state=self.reader.read(expected,deadline)
                        if not detached and state['state']!='DEAD':time.sleep(.05);continue
                        if detached and state['state']=='ALIVE' and not actor_stopped:
                            if state['pid']!=identity['pid']:raise ValueError('Detached GCS PID differs')
                            actual=self.collector.observe(identity['pid'])
                            if not self.collector.same_identity(actual['identity'],identity):raise ValueError('Detached live PID changed')
                            actual_after=self.collector.stable(actual)
                            self.record('CPU_detached_survived_driver',expected=expected,driver_exit=driver.returncode,
                                GCS_after_driver_exit=state,before=actual,after=actual_after)
                            outcome=terminate(identity,self.proc,self.record,self.check,reap=self.reap)
                            if outcome.get('controlled_signal_sent') is not True:raise RuntimeError('Detached actor already absent; parent release not performed')
                            actor_stopped=True
                        final=self.reader.read(expected,deadline)
                        if final['state']=='DEAD' and not self.proc.exists(identity['pid']):
                            if detached and not actor_stopped:raise RuntimeError('Detached actor died without observed survival and parent release')
                            self.record('CPU_scenario_terminal_observed',expected=expected,driver_exit=driver.returncode,
                                GCS=final,original_PID_absent=True)
                            self.pending_scenarios.remove(index)
                            return
                if driver.poll() is not None and expected is None:raise RuntimeError('CPU driver exited before submission')
                time.sleep(.05)
            raise TimeoutError('Single CPU lifecycle scenario observation exhausted')
        finally:out.close();err.close()

    def run(self):
        old={n:signal.getsignal(n) for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
        for number in old:signal.signal(number,lambda n,f:self.cancelled.add(n))
        failure=None
        try:
            check_cpu_port(self.port)
            ray,preimport=load_cpu_ray(self.package);self.record('CPU_preimport',facts=preimport)
            node=construct_node(node_parameters(self.base,self.port,gpu_count=0),self.check,self.register,self.processes)
            if Path(node.get_session_dir_path())!=self.collector.session:raise ValueError('Actual Node session differs')
            self.poll();self.reader=GCSActorReader.connect(node.address,self.package,self.record,self.check)
            for index,(detached,controlled) in enumerate(self.scenarios):
                self.scenario(detached,controlled,index)
        except BaseException as error:
            failure=error;self.record('CPU_diagnostic_failed',error=repr(error),
                traceback=traceback.format_exc(),missing_path=getattr(error,'filename',None))
        finally:
            self.cleaning=True
            try:
                if self.pending_scenarios:raise RuntimeError('FAILED_RELEASE_UNCONFIRMED CPU creation/scenario pending')
                if any(process.poll() is None and (self.collector is None or process.pid not in self.collector.known) for process in self.processes):
                    raise RuntimeError('FAILED_RELEASE_UNCONFIRMED unregistered head child')
                if self.reader:
                    for row in self.expected:
                        if row['identity'] is None:raise RuntimeError('FAILED_RELEASE_UNCONFIRMED pending CPU actor')
                        state=self.reader.read(row['expected'],self.end)
                        if state['state']!='DEAD' or self.proc.exists(row['identity']['pid']):
                            raise RuntimeError('FAILED_RELEASE_UNCONFIRMED actor; retain head')
                if self.collector:
                    self.poll()
                    # Stop verified raylet first, preventing new idle workers;
                    # original verified parent chains remain in the journal.
                    rows=list(self.collector.known.values())
                    rows.sort(key=lambda r:0 if Path(r['exe']).name=='raylet' else 1)
                    for identity in rows:
                        for process in self.processes:process.poll()
                        terminate(identity,self.proc,self.record,self.check,reap=self.reap)
                    for process in self.processes:process.poll()
                    remaining=[r['pid'] for r in rows if self.proc.exists(r['pid'])]
                    if remaining:raise RuntimeError('CPU known processes still present: '+repr(remaining))
                if self.leftovers():raise RuntimeError('FAILED_RELEASE_UNCONFIRMED late CPU scope process; no unknown cleanup')
                self.record('CPU_known_processes_absent',scope='registered CPU-only diagnostic; no GPU/backend approval')
            except BaseException as error:
                failure=error;self.record('CPU_cleanup_unconfirmed',error=repr(error))
            if self.reader:self.reader.close()
            for number,handler in old.items():signal.signal(number,handler)
            write(self.folder/'terminal.json',dict(exit_code=1 if failure else 0,error=repr(failure) if failure else None,
                scope=lifecycle_scope(self.smoke),smoke=self.smoke,affinity=sorted(os.sched_getaffinity(0)),
                nice=os.getpriority(os.PRIO_PROCESS,0)))
        if failure:raise failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--smoke',action='store_true',
        help='single scenario; proves the real Ray connect path without GPU or a full window')
    args=parser.parse_args();cfg=small_json(args.config,os.getuid())
    root=Path('/local/boyjiang/epd')
    affinity=os.sched_getaffinity(0);nice=os.getpriority(os.PRIO_PROCESS,0)
    exact=(affinity=={50} and nice==10)
    relaxed=args.smoke and len(affinity)==1 and nice>=0
    if (set(cfg)!={'run_id','folder','ray_base','port','ray_package'}
            or os.uname().nodename!='qjh003' or os.getuid()!=2147 or not (exact or relaxed)
            or os.environ.get('CUDA_VISIBLE_DEVICES')!=''
            or os.environ.get('EXP_ROOT')!=str(root) or os.environ.get('REPRO_RUN_ID')!=cfg['run_id']):
        raise ValueError('Actual single-core CPU diagnostic scope differs')
    for path in (root,Path(cfg['folder']),Path(cfg['ray_base'])):
        if not path.is_relative_to(root) or path.resolve(strict=True)!=path or path.is_symlink() or path.stat().st_uid!=2147:
            raise ValueError('Fresh owned canonical CPU scope required')
    if Path.cwd()!=root:raise ValueError('CPU parent actual cwd differs')
    os.environ['PYTHONPATH']=str(Path(__file__).parent)
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    Diagnostic(root,cfg['run_id'],cfg['folder'],cfg['ray_base'],cfg['port'],cfg['ray_package'],smoke=args.smoke).run()


if __name__=='__main__':main()
