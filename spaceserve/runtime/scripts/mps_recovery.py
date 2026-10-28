"""Recover only a uniquely identified daemon after an interrupted MPS start."""
import os
import time
import psutil


def validate_intent(root,intent):
    if intent.get('root')!=str(root) or intent.get('uid')!=os.getuid() or intent.get('pipe')!=str(root/'tmp/mps'):
        raise RuntimeError('MPS start intent root/UID/pipe mismatch')
    if not intent.get('token','').startswith(str(root)+':') or not intent.get('run_id','').startswith(str(root)+':'):
        raise RuntimeError('MPS start intent is unbound')


def recover(root,intent,processes):
    validate_intent(root,intent)
    matches=[]
    owned=[]
    for process in processes:
        try:
            if not process.name().startswith('nvidia-cuda-mps') or process.uids().real!=os.getuid() or process.status()==psutil.STATUS_ZOMBIE:
                continue
            environment=process.environ()
            if environment.get('REPRO_MPS_OWNER')!=intent['token'] or environment.get('CUDA_MPS_PIPE_DIRECTORY')!=intent['pipe']:
                continue
            if environment.get('EXP_ROOT')!=str(root) or environment.get('REPRO_RUN_ID')!=intent['run_id']:
                raise RuntimeError('partial MPS identity mismatch')
            created=process.create_time()
            if created<intent['started_epoch']-1:
                raise RuntimeError('MPS creation predates its intent')
            owned.append(process.pid)
            if process.name().startswith('nvidia-cuda-mps-control'):
                matches.append((process.pid,created))
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied as error:
            raise RuntimeError('MPS recovery identity unconfirmed; no quit permitted') from error
    control=root/'tmp/mps/control'
    if not matches and not owned and not control.exists():
        return None
    if len(matches)!=1 or not control.exists() or control.is_symlink():
        raise RuntimeError('cannot recover a unique private MPS daemon; no quit permitted')
    info=control.stat()
    if info.st_uid!=os.getuid():
        raise RuntimeError('MPS endpoint owner differs')
    pid,created=matches[0]
    return {'state':'running','pid':pid,'created':created,'token':intent['token'],
            'pipe':intent['pipe'],'uuid':intent['uuid'],'active_thread_percentage':100,
            'control_inode':info.st_ino,'recovered_start':True}


def recover_bounded(root,intent):
    deadline=time.monotonic()+4
    last_error=None
    while True:
        try:
            state=recover(root,intent,psutil.process_iter())
            if state is not None:
                return state
            last_error=None
        except RuntimeError as error:
            last_error=error
        if time.monotonic()>=deadline:
            if last_error is not None:
                raise last_error
            return None
        time.sleep(.1)
