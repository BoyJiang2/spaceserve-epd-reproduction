"""CPU-only fixed qjh003 code migration. No assets, GPU APIs, deletion or retries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import time

PARENT=Path('/local/boyjiang')
PROJECTS=('spaceserve','epd')
TICKET='bk-20261028T0925-0332cf80'
START,END=1793192400000,1793235600000
ORIGIN='https://github.com/BoyJiang2/spaceserve-epd-reproduction.git'


def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        while block:=stream.read(1024**2):value.update(block)
    return value.hexdigest()


def booking(snapshot,now):
    if (snapshot.get('origin')!='gputime_read_only_api' or snapshot.get('read_only') is not True
            or type(snapshot.get('observed_ms')) is not int or not 0<=now-snapshot['observed_ms']<=300000):
        raise ValueError('Fresh actual read-only API snapshot required')
    matches=[row for row in snapshot['bookings'] if row.get('id')==TICKET]
    resources=[row for row in snapshot['resources'] if row.get('id')=='h20/qjh003']
    expected={'id':TICKET,'kind':'cpu','node':'qjh003','resource_id':'h20/qjh003','user':'boyjiang',
              'start_ms':START,'end_ms':END}
    if (len(matches)!=1 or any(matches[0].get(k)!=v for k,v in expected.items())
            or len(resources)!=1 or resources[0].get('active') is not True
            or now<START or now+1020000>END):
        raise ValueError('Exact owned CPU ticket and complete 900+120s coverage required')
    return expected


def real_ancestry(path):
    for ancestor in (path,*path.parents):
        if ancestor.is_symlink():raise ValueError('Linked migration ancestry refused')
        if ancestor.exists() and ancestor.is_relative_to(PARENT):
            if not ancestor.is_dir() or ancestor.stat().st_uid!=2147:
                raise ValueError('Project directory owner/type differs')


def validate_executor():
    if (socket.gethostname()!='qjh003' or os.getuid()!=2147 or os.sched_getaffinity(0)!={50}
            or os.getpriority(os.PRIO_PROCESS,0)!=10):
        raise ValueError('Requires actual qjh003 UID2147 CPU50 nice10')
    real_ancestry(PARENT)
    if not PARENT.is_dir() or shutil.disk_usage(PARENT).free<2*1024**3:
        raise ValueError('Real owned parent and at least 2GiB free required')


def exclusive_json(path,data):
    if path.is_symlink():raise ValueError('Linked evidence refused')
    with path.open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2)


class MigrationInterrupted(RuntimeError):pass


def session_members(session):
    members=[]
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit():continue
        try:
            raw=(folder/'stat').read_text();fields=raw[raw.rfind(')')+2:].split()
            if int(fields[3])!=session:continue
            uid=folder.stat().st_uid
            if uid!=os.getuid():raise ValueError('Foreign UID in command session; refuse group signal')
            members.append({'pid':int(folder.name),'group':int(fields[2]),'session':session,
                            'start_ticks':int(fields[19]),'uid':uid})
        except (FileNotFoundError,ProcessLookupError):continue
    return members


def command_output(argv,stream,timeout,deadline):
    """One isolated own session; preserve diagnostics and terminal proof on every exit."""
    stream.write((json.dumps({'argv':argv,'started_ms':int(time.time()*1000)})+'\n').encode());stream.flush()
    started=time.monotonic();process=None;root_identity=None;output=b'';pending=None;starting=True;failure=None;cleanup=[]
    previous={number:signal.getsignal(number) for number in (signal.SIGTERM,signal.SIGINT)}
    def interrupted(number,frame):
        nonlocal pending
        pending=pending or number
        if not starting:
            for item in previous:signal.signal(item,signal.SIG_IGN)
            raise MigrationInterrupted('CPU migration interrupted by '+str(number))
    if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):
        raise RuntimeError('Linux pidfd support required before spawning any command')
    for number in previous:signal.signal(number,interrupted)
    launch_ticks=int(time.clock_gettime(time.CLOCK_BOOTTIME)*os.sysconf('SC_CLK_TCK'))-1
    try:
        process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        root_identity=next(item for item in session_members(process.pid) if item['pid']==process.pid)
        starting=False
        if pending:raise MigrationInterrupted('Deferred CPU startup signal '+str(pending))
        output=process.communicate(timeout=timeout)[0]
        if process.returncode:raise subprocess.CalledProcessError(process.returncode,argv,output=output)
    except BaseException as error:
        failure=error
        if isinstance(error,subprocess.TimeoutExpired):output=error.output or b''
    finally:
        for number in previous:signal.signal(number,signal.SIG_IGN)
        try:
            if process is not None:
                stop_at=min(deadline,time.monotonic()+10)
                for number in (signal.SIGTERM,signal.SIGKILL):
                    members=session_members(process.pid)
                    if any(item['start_ticks']<launch_ticks for item in members):
                        raise ValueError('Command session identity changed; refuse signal')
                    if not members:break
                    for saved in members:
                        # pidfd binds the signal to this actual process, even if its numeric PID is recycled.
                        try:handle=os.pidfd_open(saved['pid'])
                        except ProcessLookupError:continue
                        try:
                            current=session_members(process.pid)
                            root_now=next((item for item in current if item['pid']==process.pid),None)
                            if root_now is not None and root_now!=root_identity:raise ValueError('Command root PID identity changed')
                            if saved not in current:continue
                            signal.pidfd_send_signal(handle,number)
                            cleanup.append({'signal':number,'identity':saved})
                        except ProcessLookupError:pass
                        finally:os.close(handle)
                    until=min(stop_at,time.monotonic()+2)
                    while time.monotonic()<until:
                        process.poll()  # Reap the direct child while helpers unwind.
                        if not session_members(process.pid):break
                        time.sleep(.02)
                output=process.communicate(timeout=max(.01,min(2,stop_at-time.monotonic())))[0]
                if session_members(process.pid):raise RuntimeError('Command session release unconfirmed; preserve partial')
        except BaseException as error:
            failure=failure or error
            cleanup.append({'release_unconfirmed':repr(error)})
        finally:
            stream.write(output);stream.write(('\n'+json.dumps({'exit_code':None if process is None else process.returncode,
                'elapsed_seconds':time.monotonic()-started,'failure':None if failure is None else repr(failure),
                'output_bytes':len(output),'output_sha256':hashlib.sha256(output).hexdigest(),'cleanup':cleanup})+'\n').encode())
            stream.flush()
            for number,handler in previous.items():signal.signal(number,handler)
    if failure is not None:raise failure
    return output


def run(args):
    started=time.monotonic();now=int(time.time()*1000)
    proof=json.loads(args.booking_json);actual_booking=booking(proof,now);validate_executor()
    if not re.fullmatch('[0-9a-f]{40}',args.commit):raise ValueError('Full pushed Git commit required')
    roots=[PARENT/project for project in PROJECTS]
    for root in roots:real_ancestry(root)
    if args.action=='prepare':
        if any(root.exists() for root in roots):raise ValueError('Existing/partial project: inspect, do not repeat prepare')
        for root in roots:
            root.mkdir(mode=0o700)
            for child in ('assets','runs','staging','archives'):(root/child).mkdir(mode=0o700)
            exclusive_json(root/'staging/migration-prepared.json',{'booking':actual_booking,'api_observed_ms':proof['observed_ms'],
                'host':socket.gethostname(),'uid':os.getuid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'observed_ms':now,'affinity':sorted(os.sched_getaffinity(0)),'nice':os.getpriority(os.PRIO_PROCESS,0),'commit':args.commit,'scope':'CPU directories only; no code/assets/tests/GPU success'})
        return {'state':'CPU_DIRECTORIES_PREPARED','GPU_requests':0}
    bundle=roots[0]/'staging/source.bundle'
    if (not args.bundle_sha256 or not re.fullmatch('[0-9a-f]{64}',args.bundle_sha256)
            or bundle.is_symlink() or not bundle.is_file() or bundle.stat().st_uid!=2147
            or bundle.stat().st_size!=args.bundle_bytes or sha(bundle)!=args.bundle_sha256):
        raise ValueError('Exact transferred Git bundle size/SHA/owner required')
    # Validate both targets before the first Git mutation. Preserve any failure/partial checkout.
    for root in roots:
        if (root/'repo').exists():raise ValueError('Partial/existing checkout: inspect, no duplicate deployment')
        if json.loads((root/'staging/migration-prepared.json').read_bytes())['commit']!=args.commit:
            raise ValueError('Prepared designated commit differs')
    def command(argv,stream):
        booking(proof,int(time.time()*1000))
        left=900-(time.monotonic()-started)
        if left<=0:raise TimeoutError('CPU migration unit exhausted')
        return command_output(argv,stream,min(left,180),started+1020)
    for project,root in zip(PROJECTS,roots):
        receipt=root/'staging/CPU_CODE_DEPLOYED.json';log=root/'staging/code-deployment.log'
        with log.open('xb') as stream:
            def git(*arguments):
                argv=['git','-C',str(root/'repo'),*arguments]
                stream.write((json.dumps(argv)+'\n').encode());stream.flush()
                return command(argv,stream)
            command(['git','clone','--no-checkout',str(bundle),str(root/'repo')],stream)
            git('remote','set-url','origin',ORIGIN)
            git('sparse-checkout','init','--cone');git('sparse-checkout','set',project+'/runtime','tests')
            git('checkout','--detach',args.commit)
            if git('rev-parse','HEAD').decode().strip()!=args.commit or git('status','--porcelain','--untracked-files=all').strip():
                raise ValueError('Git HEAD/clean differs')
            git('fsck','--full','--no-reflogs')
            rows=[]
            for record in git('ls-files','-s','-z').split(b'\0'):
                if not record:continue
                info,name=record.split(b'\t',1);mode,blob,stage=info.decode().split();relative=name.decode()
                path=root/'repo'/relative
                if not path.exists():continue  # Explicit sparse exclusions remain Git objects, not source copies.
                if mode not in ('100644','100755') or path.is_symlink() or not path.resolve().is_relative_to(root/'repo'):
                    raise ValueError('Unexpected checked-out source file mode/link/path')
                actual=git('hash-object','--',relative).decode().strip()
                if actual!=blob:raise ValueError('Checked-out Git blob differs')
                rows.append({'path':relative,'git_blob':blob,'bytes':path.stat().st_size,'sha256':sha(path)})
            review=json.loads((root/'repo'/project/'migration'/(
                'space-refactor-source-review-snapshot.json' if project=='spaceserve' else 'epd-refactor-source-review-snapshot.json')).read_bytes()) if (root/'repo'/project/'migration').exists() else None
            # Migration metadata is sparse-excluded; compare the original G2 SHA list from the designated commit.
            if review is None:
                name=project+'/migration/'+('space-refactor-source-review-snapshot.json' if project=='spaceserve' else 'epd-refactor-source-review-snapshot.json')
                review=json.loads(git('show',args.commit+':'+name))
            for item in review:
                if project=='epd' and not (item['path'].startswith('epd/runtime/') or item['path']=='reproduction_paths.py'):
                    raise ValueError('Unexpected EPD G2 member')
                path=root/'repo'/item['path']
                if not path.is_file() or path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:
                    raise ValueError('Actual checked-out source differs from its G2 snapshot')
            state={'state':'CPU_CODE_DEPLOYED_only','commit':args.commit,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),
                'project':project,'root':str(root),'host':socket.gethostname(),'uid':os.getuid(),
                'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'booking':actual_booking,
                'api_observed_ms':proof['observed_ms'],'observed_ms':int(time.time()*1000),
                'started_ms':now,'affinity':sorted(os.sched_getaffinity(0)),'nice':os.getpriority(os.PRIO_PROCESS,0),
                'bundle_sha256':args.bundle_sha256,'bundle_bytes':args.bundle_bytes,'files':rows,
                'CPU_tests_executed':0,'assets_migrated':False,'GPU_requests':0,'grants_no_Gates':True}
        state['log_sha256']=sha(log);exclusive_json(receipt,state)
    return {'state':'TWO_CODE_CHECKOUTS_DEPLOYED_only','commit':args.commit,'GPU_requests':0}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('prepare','deploy'))
    parser.add_argument('--booking-json',required=True)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--bundle-sha256')
    parser.add_argument('--bundle-bytes',type=int)
    print(json.dumps(run(parser.parse_args())))


if __name__=='__main__':main()
