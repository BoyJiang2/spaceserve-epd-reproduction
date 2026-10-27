"""Formal-only service lifecycle; reviewed preflight source remains byte-identical."""
import contextlib
import json
import os
import subprocess
import time
import urllib.request
import uuid
from booking_window import require
from resource_guard import ROOT,UUIDS,idle
from owned_processes import stop
from run_models import command,PYTHON


@contextlib.contextmanager
def service(role,block,destination):
    if require()<900:
        raise RuntimeError('insufficient time for a formal cell plus cleanup')
    idle()
    destination.mkdir(exist_ok=False)
    identity=str(ROOT)+':service:'+uuid.uuid4().hex
    environment=dict(os.environ,EXP_ROOT=str(ROOT),REPRO_RUN_ID=identity,REPRO_HOST_LOCK_HELD='1',
        REPRO_USE_MPS='1',CUDA_MPS_ACTIVE_THREAD_PERCENTAGE='100',
        REPRO_SPACE_RUN_LABEL=f'formal-{destination.name}',REPRO_SM_PROBE='0')
    for key in ('PYTHONPATH','VLLM_LIBSMCTRL_PATH','REPRO_OBSERVE','VLLM_TORCH_PROFILER_DIR'):
        environment.pop(key,None)
    mps_environment=dict(environment,REPRO_RUN_ID=str(ROOT)+':mps:'+uuid.uuid4().hex)
    intent_path=ROOT/'evidence'/('mps-start-intent-model-'+uuid.uuid4().hex+'.json')
    with intent_path.open('x') as output:
        json.dump({'root':str(ROOT),'uid':os.getuid(),'pipe':str(ROOT/'tmp/mps'),
            'token':str(ROOT)+':mps:'+uuid.uuid4().hex,'run_id':mps_environment['REPRO_RUN_ID'],
            'started_epoch':time.time(),'uuid':UUIDS[0]},output,indent=2)
    mps_environment['REPRO_MPS_INTENT']=str(intent_path)
    attempted=False
    server_log=None
    try:
        command([PYTHON,str(ROOT/'scripts/prune_stopped_mps.py')],environment,destination/'mps-prune.log',30)
        attempted=True
        command(['bash',str(ROOT/'scripts/mps_control.sh'),'start','4'],mps_environment,destination/'mps-start.log',60)
        environment.update(CUDA_MPS_PIPE_DIRECTORY=str(ROOT/'tmp/mps'),CUDA_MPS_LOG_DIRECTORY=str(ROOT/'logs/mps'))
        server_log=(destination/'server.log').open('x')
        server=subprocess.Popen(['bash',str(ROOT/'scripts/start_server.sh'),role,'4','19770'],env=environment,
                                stdout=server_log,stderr=subprocess.STDOUT,start_new_session=True)
        with (destination/'launch.json').open('x') as output:
            import psutil
            json.dump({'api_pid':server.pid,'api_created':psutil.Process(server.pid).create_time(),
                       'run_id':identity,'role':role,'block':block,'mps_intent':str(intent_path)},output,indent=2)
        deadline=time.monotonic()+500
        while True:
            require()
            if server.poll() is not None:
                raise RuntimeError('server exited before ready; retain original server.log')
            try:
                with urllib.request.urlopen('http://127.0.0.1:19770/health',timeout=1) as response:
                    if response.status==200:
                        break
            except (OSError,TimeoutError):
                pass
            if time.monotonic()>deadline:
                raise RuntimeError('server startup timeout')
            time.sleep(.5)
        yield environment,server.pid
    finally:
        try:
            stop(identity)
        finally:
            try:
                if attempted:
                    command(['bash',str(ROOT/'scripts/mps_control.sh'),'recover-stop'],mps_environment,destination/'mps-stop.log',60)
            finally:
                if server_log is not None:
                    server_log.close()
