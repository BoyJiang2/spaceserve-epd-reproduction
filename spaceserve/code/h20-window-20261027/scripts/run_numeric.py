"""Only reviewed numeric probes; no model loading or performance fallback."""
import json
import os
import subprocess
import time
import uuid

from resource_guard import ROOT,UUIDS,exclusive,idle,sha


def main():
    if not __debug__:
        raise RuntimeError('optimized numeric runner refused')
    os.environ['EXP_ROOT']=str(ROOT)
    with exclusive('numeric') as code:
        output=ROOT/'results/numeric'
        output.mkdir(exist_ok=False)
        environment=dict(os.environ,REPRO_HOST_LOCK_HELD='1',REPRO_USE_MPS='0',
                         REPRO_RUN_ID=str(ROOT)+':numeric:'+uuid.uuid4().hex,CUDA_VISIBLE_DEVICES=UUIDS[0])
        for key in ('CUDA_MPS_PIPE_DIRECTORY','CUDA_MPS_LOG_DIRECTORY','CUDA_MPS_ACTIVE_THREAD_PERCENTAGE','PYTHONPATH'):
            environment.pop(key,None)
        python=str(ROOT/'envs/space/bin/python')
        with (output/'fp16.log').open('x') as log:
            subprocess.run([python,'-B',str(ROOT/'scripts/probe_runtime.py')],env=environment,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        # Compilation occurs before any formal measurement and needs no CUDA context.
        with (output/'build.log').open('x') as log:
            subprocess.run(['/usr/local/cuda-12.8/bin/nvcc','-gencode','arch=compute_90,code=sm_90',
                str(ROOT/'scripts/probe_sm_mask.cu'),'-o',str(output/'probe_sm_mask'),'-ldl'],
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        environment['REPRO_USE_MPS']='1'
        intent_path=ROOT/'evidence'/('mps-start-intent-'+uuid.uuid4().hex+'.json')
        with intent_path.open('x') as intent:
            json.dump({'root':str(ROOT),'uid':os.getuid(),'pipe':str(ROOT/'tmp/mps'),
                'token':str(ROOT)+':mps:'+uuid.uuid4().hex,'run_id':environment['REPRO_RUN_ID'],
                'started_epoch':time.time(),'uuid':UUIDS[0]},intent,indent=2)
        environment['REPRO_MPS_INTENT']=str(intent_path)
        start_attempted=False
        try:
            idle()
            start_attempted=True
            with (output/'mps-start.log').open('x') as log:
                subprocess.run(['bash',str(ROOT/'scripts/mps_control.sh'),'start','4'],env=environment,
                    stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
            environment.update(CUDA_MPS_PIPE_DIRECTORY=str(ROOT/'tmp/mps'),
                CUDA_MPS_LOG_DIRECTORY=str(ROOT/'logs/mps'),CUDA_MPS_ACTIVE_THREAD_PERCENTAGE='100')
            for repetition in range(3):
                with (output/f'mask-{repetition}.jsonl').open('x') as log:
                    subprocess.run([str(output/'probe_sm_mask'),str(ROOT/'build/libsmctrl.so')],env=environment,
                        stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        finally:
            if start_attempted:
                with (output/'mps-stop.log').open('x') as log:
                    subprocess.run(['bash',str(ROOT/'scripts/mps_control.sh'),'recover-stop'],env=environment,
                        stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        idle()
        with (output/'COMPLETED.json').open('x') as marker:
            json.dump({'code_manifest_sha256':code,'FP16_passed':True,'mask_repetitions':3,
                       'new_model_requests':0,'libsmctrl_sha256':sha(ROOT/'build/libsmctrl.so'),
                       'probe_sha256':sha(output/'probe_sm_mask'),'scope':'numeric only; actual service G3 still required'},marker,indent=2)


if __name__=='__main__':
    main()
