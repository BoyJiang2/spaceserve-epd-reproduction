"""Run the frozen 97 correctness plus 216 diagnostic requests; no formal measurements."""
import asyncio
import contextlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request
import uuid

from booking_window import require
from resource_guard import ROOT,UUIDS,idle,sha
from model_guard import exclusive_models
from owned_processes import stop
from correctness_suite import run as correctness
from check_mask_sets import validate as validate_mask

PYTHON=str(ROOT/'envs/space/bin/python')
ROLES=('baseline-space','space','space-mask')


def command(arguments,environment,path,timeout=120):
    with path.open('x') as log:
        subprocess.run(arguments,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=timeout)


@contextlib.contextmanager
def service(role,trial,destination):
    if require()<900:
        raise RuntimeError('insufficient time for a preflight service plus cleanup')
    idle()
    destination.mkdir(exist_ok=False)
    (destination/'traces').mkdir()
    identity=str(ROOT)+':service:'+uuid.uuid4().hex
    environment=dict(os.environ,EXP_ROOT=str(ROOT),REPRO_RUN_ID=identity,REPRO_HOST_LOCK_HELD='1',
        REPRO_USE_MPS='1',CUDA_MPS_ACTIVE_THREAD_PERCENTAGE='100',
        REPRO_SPACE_RUN_LABEL=f'preflight-{trial}-{role}',REPRO_SM_PROBE='0' if role=='baseline-space' else '1',
        VLLM_TORCH_PROFILER_DIR=str(destination/'traces'))
    for key in ('PYTHONPATH','VLLM_LIBSMCTRL_PATH','REPRO_OBSERVE','VLLM_TORCH_PROFILER_DIR_OLD'):
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
        attempted=True
        command(['bash',str(ROOT/'scripts/mps_control.sh'),'start','4'],mps_environment,destination/'mps-start.log',60)
        environment.update(CUDA_MPS_PIPE_DIRECTORY=str(ROOT/'tmp/mps'),CUDA_MPS_LOG_DIRECTORY=str(ROOT/'logs/mps'))
        server_log=(destination/'server.log').open('x')
        server=subprocess.Popen(['bash',str(ROOT/'scripts/start_server.sh'),role,'4','19770'],env=environment,
                                stdout=server_log,stderr=subprocess.STDOUT,start_new_session=True)
        with (destination/'launch.json').open('x') as output:
            import psutil
            json.dump({'api_pid':server.pid,'api_created':psutil.Process(server.pid).create_time(),
                       'run_id':identity,'role':role,'trial':trial,'mps_intent':str(intent_path)},output,indent=2)
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


def validate_devices(folder,role):
    rows=[json.loads(p.read_text()) for p in folder.glob('worker-*.json')]
    if len(rows)!=(1 if role=='baseline-space' else 2):
        raise RuntimeError('actual worker count differs')
    for row in rows:
        if row['system']!=role or row['cuda_visible_devices']!=UUIDS[0] or row['parameters_by_device'].keys()!={'cuda:0'} or row['parameters_by_dtype'].keys()!={'torch.float16'}:
            raise RuntimeError('actual loaded model role/device/precision differs')
        if row['mps_active_thread_percentage']!='100' or row['mps_pipe']!=str(ROOT/'tmp/mps'):
            raise RuntimeError('worker MPS identity differs')
        if role!='space-mask' and row['loaded_smctrl']:
            raise RuntimeError('actual loaded SM library differs from role')
        if role=='space-mask' and row['only_vision_encoder'] and not row['loaded_smctrl']:
            raise RuntimeError('masked encoder did not load SM library')
        if any(path!=str(ROOT/'build/libsmctrl.so') or value!=sha(ROOT/'build/libsmctrl.so')
               for path,value in row['loaded_smctrl_sha256'].items()):
            raise RuntimeError('loaded SM library path/SHA differs')
    if role!='baseline-space':
        if sum(row['only_vision_encoder'] for row in rows)!=1:
            raise RuntimeError('encoder/decoder parameter placement not distinguished')
        records=[json.loads(line) for path in folder.glob('sm-stream-*.jsonl') for line in path.read_text().splitlines()]
        result=validate_mask(records,role=='space-mask')
        with (folder/'SM-validated.json').open('x') as output:
            json.dump(result,output,indent=2)


def main():
    if not __debug__:
        raise RuntimeError('optimized model preflight refused')
    with exclusive_models() as code:
        inputs=json.loads((ROOT/'evidence/MODEL_INPUTS_VERIFIED.json').read_text())
        if not inputs['passed'] or inputs['boot_id']!=Path('/proc/sys/kernel/random/boot_id').read_text().strip() or inputs['input_manifest_sha256']!=sha(ROOT/'configs/relocated-inputs.json'):
            raise RuntimeError('CPU model inputs have not been verified')
        if not 0<=time.time()-inputs['verified_epoch']<900:
            raise RuntimeError('CPU model input verification stale')
        output=ROOT/'results/preflight-models'
        output.mkdir(exist_ok=False)
        count=0
        for trial in ('cold','restart'):
            for role in ROLES:
                destination=output/f'{trial}-{role}'
                with service(role,trial,destination) as (environment,pid):
                    if trial=='cold' and role=='baseline-space':
                        count+=asyncio.run(correctness(ROOT,output/'reference.json'))
                    count+=asyncio.run(correctness(ROOT,destination/'correctness.json',output/'reference.json'))
                    device_records=ROOT/'results/runtime-devices'/environment['REPRO_SPACE_RUN_LABEL']
                    validate_devices(device_records,role)
                    command([PYTHON,str(ROOT/'scripts/capture_mps_clients.py'),'--api-pid',str(pid),'--output',str(destination/'mps-before.json')],environment,destination/'mps-before.log')
                    command([PYTHON,str(ROOT/'scripts/check_rgb_cache.py'),'--dataset',str(ROOT/'dataset'),'--urls','http://127.0.0.1:19770','--output',str(destination/'rgb-before.json')],environment,destination/'rgb-before.log')
                    command([PYTHON,str(ROOT/'scripts/capture_runtime.py'),str(destination/'runtime.json'),'--server-pids',str(pid),'--devices','4','--note','Fresh preflight service before diagnostic profiler'],environment,destination/'runtime.log')
                    command([PYTHON,str(ROOT/'scripts/benchmark.py'),'--urls','http://127.0.0.1:19770',
                        '--model',str(ROOT/'models/Qwen2-VL-7B-Instruct'),'--dataset',str(ROOT/'dataset'),
                        '--output',str(destination/'profile-requests'),'--images','4','--concurrency','8',
                        '--tokens','128','--warmup','20','--requests','16','--repetitions','1','--profile-after-warmup'],
                        environment,destination/'profile-requests.log',360)
                    count+=36
                    command([PYTHON,str(ROOT/'scripts/wait_for_traces.py'),'--directory',str(destination/'traces'),
                        '--device-records',str(device_records),'--workers','1' if role=='baseline-space' else '2',
                        '--output',str(destination/'trace-export.json')],environment,destination/'trace-export.log',330)
                    command([PYTHON,str(ROOT/'scripts/check_rgb_cache.py'),'--dataset',str(ROOT/'dataset'),'--urls','http://127.0.0.1:19770','--output',str(destination/'rgb-after.json')],environment,destination/'rgb-after.log')
                    command([PYTHON,str(ROOT/'scripts/capture_mps_clients.py'),'--api-pid',str(pid),'--output',str(destination/'mps-after.json')],environment,destination/'mps-after.log')
                shutil.copytree(device_records,destination/'device-records')
                if role!='baseline-space':
                    command([PYTHON,str(ROOT/'scripts/analyze_trace.py'),str(destination/'traces'),
                        '--server-log',str(destination/'server.log'),'--output',str(destination/'overlap.json')],
                        dict(os.environ),destination/'overlap.log')
                    if not json.loads((destination/'overlap.json').read_text())['kernel_overlap_observed']:
                        raise RuntimeError('actual encoder/decoder kernel overlap not observed')
                with (destination/'COMPLETED.json').open('x') as marker:
                    json.dump({'code_manifest_sha256':code,'correctness_targets':15,'diagnostic_requests':36},marker,indent=2)
        if count!=313:
            raise RuntimeError('unexpected preflight request budget')
        from model_guard import model_code
        if model_code()!=code:
            raise RuntimeError('model deployment identity changed during preflight')
        idle()
        with (output/'COMPLETED.json').open('x') as marker:
            json.dump({'code_manifest_sha256':code,'generated_requests':count,'scope':'requires independent actual service/model G3'},marker,indent=2)


if __name__=='__main__':
    main()
