"""Diagnostic-only SMID sampling on the encoder's actual CUDA stream."""
import ctypes
import json
import os
from pathlib import Path
import torch


def measure(stream, label):
    root = Path(os.environ['EXP_ROOT']).resolve()
    if str(root) != '/var/tmp/boyjiang-spaceserve-window-20261028-2300' or os.environ.get('REPRO_SM_PROBE') != '1' or os.environ.get('REPRO_HOST_LOCK_HELD') != '1':
        raise RuntimeError('service SM probe is only enabled for owned diagnostics')
    library = ctypes.CDLL(str(root / 'build/service_sm_probe.so'))
    sample = library.repro_sample_actual_stream
    sample.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    sample.restype = ctypes.c_int
    seen = (ctypes.c_int * 512)()
    code = sample(ctypes.c_void_p(stream.cuda_stream), seen)
    if code:
        raise RuntimeError('actual encoder stream SMID probe CUDA error: ' + str(code))
    properties = torch.cuda.get_device_properties(stream.device)
    record = {'label': label, 'pid': os.getpid(), 'stream': stream.cuda_stream,
              'logical_device': str(stream.device), 'gpu_uuid': str(getattr(properties, 'uuid', 'unavailable')),
              'visible_gpu_uuid': os.environ.get('CUDA_VISIBLE_DEVICES'),
              'physical_sm_count': properties.multi_processor_count,
              'sm_ids': [number for number, value in enumerate(seen) if value],
              'masked_group': os.environ['REPRO_SYSTEM_ROLE'] == 'space-mask',
              'mps_pipe': os.environ.get('CUDA_MPS_PIPE_DIRECTORY'),
              'mps_active_thread_percentage': os.environ.get('CUDA_MPS_ACTIVE_THREAD_PERCENTAGE'),
              'scope': 'actual stream diagnostic; observed SM set is not a throughput/resource fraction'}
    if not record['sm_ids']:
        raise RuntimeError('actual stream probe recorded no SMs')
    destination = root / 'results/runtime-devices' / os.environ['REPRO_SPACE_RUN_LABEL']
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / f'sm-stream-{os.getpid()}.jsonl').open('a') as output:
        output.write(json.dumps(record) + '\n')
    print('REPRO_SM_STREAM ' + json.dumps(record), flush=True)
    return record


def arm_first_execution(worker):
    original = worker.execute_vision_encoder

    def measured(*args, **kwargs):
        measure(torch.cuda.current_stream(), 'first-encoder-execution')
        worker.execute_vision_encoder = original
        return original(*args, **kwargs)

    worker.execute_vision_encoder = measured
