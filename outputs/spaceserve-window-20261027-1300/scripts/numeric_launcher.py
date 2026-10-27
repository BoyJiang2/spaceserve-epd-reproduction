"""Single numeric launch with a persistent PID identity and actual child exit receipt."""
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import time
import uuid
import psutil

ROOT=Path('/var/tmp/boyjiang-spaceserve-window-20261027-1300')


def terminate_owned(child,created):
    if child.poll() is not None:
        return
    process=psutil.Process(child.pid)
    if created is None or process.create_time()!=created or process.uids().real!=os.getuid():
        raise RuntimeError('refuse forwarding to an unconfirmed child')
    child.terminate()


def launch(command,root):
    identity={'controller_id':uuid.uuid4().hex,'pid':os.getpid(),
              'process_created':psutil.Process().create_time(),'started_unix':time.time()}
    # A rejected duplicate never enters the try/finally that owns the exit receipt.
    with (root/'evidence/NUMERIC_STARTED.json').open('x') as marker:
        json.dump(identity,marker,indent=2)
    status=dict(identity)
    requested=[]
    previous={number:signal.getsignal(number) for number in (signal.SIGTERM,signal.SIGINT)}
    for number in previous:
        signal.signal(number,lambda number,frame:requested.append(number))
    child=None
    created=None
    try:
        with (root/'evidence/numeric-controller.log').open('x') as log:
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
            created=psutil.Process(child.pid).create_time()
            status.update(child_pid=child.pid,child_created=created)
            forwarded=False
            while child.poll() is None:
                if requested and not forwarded:
                    terminate_owned(child,created)
                    forwarded=True
                    status['forwarded_controlled_SIGTERM']=True
                time.sleep(.05)
            status['exit_code']=child.wait()
    except BaseException as error:
        status.update(exit_code=1,error_type=type(error).__name__,error=str(error))
        if child is not None and child.poll() is None:
            try:
                terminate_owned(child,created)
                status['child_exit_after_wrapper_error']=child.wait()
            except Exception as cleanup_error:
                status['cleanup_identity_unconfirmed']=type(cleanup_error).__name__+': '+str(cleanup_error)
        raise
    finally:
        status['finished_unix']=time.time()
        with (root/'evidence/numeric-exit.json').open('x') as receipt:
            json.dump(status,receipt,indent=2)
        for number,handler in previous.items():
            signal.signal(number,handler)
    return status['exit_code']


if __name__=='__main__':
    if not __debug__ or os.uname().nodename!='qjh000' or os.getuid()!=2147 or os.environ.get('EXP_ROOT')!=str(ROOT):
        raise RuntimeError('numeric launcher host/root/UID mismatch')
    raise SystemExit(launch([sys.executable,'-B',str(ROOT/'scripts/run_numeric.py')],ROOT))
