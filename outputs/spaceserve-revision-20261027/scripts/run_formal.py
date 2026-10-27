"""Execute exactly the approved 54-cell schedule, with diagnostics disabled."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import psutil

from resource_guard import ROOT,sha,idle
from formal_guard import exclusive_formal,formal_code
from formal_service import service
from run_models import command,PYTHON
from audit_formal_cell import audit
from numeric_launcher import terminate_owned

SCHEDULE_SHA='7248d8829180d3df25f04204cd7e1e89b7b7462ea5f39651986f118418c0d8d3'


def host_snapshot(path):
    state={'utc_ns':time.time_ns(),'host_ns':time.perf_counter_ns(),
           'load_average':list(os.getloadavg()),'meminfo':Path('/proc/meminfo').read_text()}
    for name,fields in (('gpus','index,uuid,memory.used,utilization.gpu'),('compute_processes','pid,gpu_uuid,used_memory')):
        query='--query-gpu=' if name=='gpus' else '--query-compute-apps='
        state[name]=subprocess.check_output(['nvidia-smi',query+fields,'--format=csv,noheader,nounits'],text=True,timeout=15)
    state['finished_utc_ns']=time.time_ns()
    state['finished_host_ns']=time.perf_counter_ns()
    with path.open('x') as output:
        json.dump(state,output,indent=2)


def validate_devices(folder,role):
    rows=[json.loads(path.read_text()) for path in folder.glob('worker-*.json')]
    if len(rows)!=(1 if role=='baseline-space' else 2) or list(folder.glob('sm-stream-*.jsonl')):
        raise RuntimeError('wrong workers or SM diagnostics active in formal service')
    imported=json.loads((folder/'imports.json').read_text())
    if imported['profiler_directory'] or imported['SM_diagnostics']:
        raise RuntimeError('profiler/SM diagnostic environment active')
    expected_prefix=ROOT/('envs/space/lib/python3.10/site-packages/vllm' if role=='baseline-space' else 'src/SpaceServe/vllm')
    if not Path(imported['vllm_file']).is_relative_to(expected_prefix):
        raise RuntimeError('formal imported wrong vLLM implementation')
    options=json.loads((folder/'engine-args.json').read_text())
    expected={'model':str(ROOT/'models/Qwen2-VL-7B-Instruct'),'dtype':'float16','tensor_parallel_size':1,
              'enforce_eager':True,'seed':0,'max_model_len':4096,'max_num_seqs':8,'max_num_batched_tokens':4096,
              'enable_prefix_caching':False,'disable_mm_preprocessor_cache':True,'gpu_memory_utilization':.65,
              'limit_mm_per_prompt':{'image':4},'mm_processor_kwargs':{'min_pixels':200704,'max_pixels':200704}}
    if any(options.get(name)!=value for name,value in expected.items()):
        raise RuntimeError('formal engine options differ from approved preflight')
    for row in rows:
        if row['system']!=role or row['cuda_visible_devices']!='GPU-79214c80-7778-37d9-282b-89228debbb69' or row['parameters_by_device'].keys()!={'cuda:0'} or row['parameters_by_dtype'].keys()!={'torch.float16'}:
            raise RuntimeError('formal loaded parameters differ from reviewed model/device/precision')
        if row['mps_active_thread_percentage']!='100' or row['mps_pipe']!=str(ROOT/'tmp/mps'):
            raise RuntimeError('formal private MPS identity differs')
        if role!='space-mask' and row['loaded_smctrl']:
            raise RuntimeError('unmasked group loaded SM library')
        if role=='space-mask' and row['only_vision_encoder'] and not row['loaded_smctrl']:
            raise RuntimeError('masked encoder library not loaded')
        if any(path!=str(ROOT/'build/libsmctrl.so') or value!=sha(ROOT/'build/libsmctrl.so') for path,value in row['loaded_smctrl_sha256'].items()):
            raise RuntimeError('actual SM library differs')
    if role!='baseline-space' and sum(row['only_vision_encoder'] for row in rows)!=1:
        raise RuntimeError('formal encoder/decoder components not distinguished')


def boundary(destination,environment,pid,suffix):
    command([PYTHON,str(ROOT/'scripts/check_rgb_cache.py'),'--dataset',str(ROOT/'dataset'),'--urls','http://127.0.0.1:19770','--output',str(destination/f'rgb-{suffix}.json')],environment,destination/f'rgb-{suffix}.log')
    command([PYTHON,str(ROOT/'scripts/capture_mps_clients.py'),'--api-pid',str(pid),'--output',str(destination/f'mps-{suffix}.json')],environment,destination/f'mps-{suffix}.log')


def supervised_benchmark(arguments,environment,path,monitor):
    with path.open('x') as log:
        benchmark=subprocess.Popen(arguments,env=environment,stdout=log,stderr=subprocess.STDOUT)
        created=None
        try:
            created=psutil.Process(benchmark.pid).create_time()
            deadline=time.monotonic()+900
            while True:
                if monitor.poll() is not None:
                    raise RuntimeError('formal monitor stopped; immediately stop submitting requests')
                status=benchmark.poll()
                if status is not None:
                    if status!=0: raise RuntimeError('benchmark failed; preserve partial cell')
                    return
                if time.monotonic()>deadline:
                    raise RuntimeError('formal cell timeout; preserve partial')
                time.sleep(.1)
        finally:
            if benchmark.poll() is None:
                terminate_owned(benchmark,created)
                benchmark.wait(timeout=15)


def main():
    if not __debug__:
        raise RuntimeError('optimized formal controller refused')
    with exclusive_formal() as code:
        schedule_path=ROOT/'configs/schedule-v2.json'
        if sha(schedule_path)!=SCHEDULE_SHA:
            raise RuntimeError('frozen schedule changed')
        schedule=json.loads(schedule_path.read_text())
        if len(schedule['cells'])!=54 or sum(row['requests'] for row in schedule['cells'])!=5400 or sum(row['warmup'] for row in schedule['cells'])!=1080:
            raise RuntimeError('formal budget changed')
        output=ROOT/'results/formal'
        output.mkdir(exist_ok=False)
        for row in schedule['cells']:
            destination=output/f'{row["index"]:03d}-b{row["block"]}-i{row["images"]}-c{row["concurrency"]}-{row["role"]}'
            print(json.dumps({'starting':str(destination),'row':row}),flush=True)
            with service(row['role'],row['block'],destination) as (environment,pid):
                records=ROOT/'results/runtime-devices'/environment['REPRO_SPACE_RUN_LABEL']
                validate_devices(records,row['role'])
                boundary(destination,environment,pid,'before')
                command([PYTHON,str(ROOT/'scripts/capture_runtime.py'),str(destination/'runtime.json'),'--server-pids',str(pid),'--devices','4','--note','Formal service; profiler and SM diagnostic kernels disabled'],environment,destination/'runtime.log')
                host_snapshot(destination/'host-before.json')
                with (destination/'gpu-memory.jsonl').open('x') as memory,(destination/'monitor-stderr.log').open('x') as error_log:
                    monitor=subprocess.Popen([PYTHON,'-u',str(ROOT/'scripts/formal_monitor.py'),'--devices','4','--server-pids',str(pid)],env=environment,stdout=memory,stderr=error_log)
                    monitor_created=None
                    try:
                        monitor_created=psutil.Process(monitor.pid).create_time()
                        supervised_benchmark([PYTHON,str(ROOT/'scripts/benchmark.py'),'--urls','http://127.0.0.1:19770',
                            '--model',str(ROOT/'models/Qwen2-VL-7B-Instruct'),'--dataset',str(ROOT/'dataset'),
                            '--output',str(destination/'measurement'),'--images',str(row['images']),
                            '--concurrency',str(row['concurrency']),'--tokens','128','--warmup','20','--requests','100','--repetitions','1'],
                            environment,destination/'benchmark.log',monitor)
                    finally:
                        if monitor.poll() is None:
                            terminate_owned(monitor,monitor_created)
                        if monitor.wait(timeout=15)!=0:
                            raise RuntimeError('GPU monitor failed; preserve partial cell')
                host_snapshot(destination/'host-after.json')
                boundary(destination,environment,pid,'after')
                with (destination/'technical-audit.json').open('x') as check:
                    json.dump(audit(destination,row),check,indent=2)
            shutil.copytree(records,destination/'device-records')
            with (destination/'COMPLETED.json').open('x') as marker:
                json.dump({'formal_code_manifest_sha256':code,'schedule_index':row['index'],
                           'formal_requests':100,'warmup_requests':20},marker,indent=2)
        if formal_code()!=code:
            raise RuntimeError('formal code identity changed')
        idle()
        with (output/'COMPLETED.json').open('x') as marker:
            json.dump({'formal_code_manifest_sha256':code,'schedule_sha256':SCHEDULE_SHA,'formal_requests':5400,'warmup_requests':1080},marker,indent=2)


if __name__=='__main__':
    main()
