"""Record actual loaded parameters once, before inference measurements."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import time
import torch


def record(worker):
    root = Path(os.environ['EXP_ROOT']).resolve()
    label = os.environ['REPRO_SPACE_RUN_LABEL']
    if str(root) != '/var/tmp/boyjiang-spaceserve-revision-20261027' or not re.fullmatch('[a-z0-9-]+', label):
        raise RuntimeError('unexpected device-record destination')
    model = worker.model_runner.model
    devices, dtypes, components, examples = Counter(), Counter(), Counter(), []
    example_counts = Counter()
    for name, parameter in model.named_parameters():
        devices[str(parameter.device)] += parameter.numel()
        dtypes[str(parameter.dtype)] += parameter.numel()
        component = name.split('.')[0]
        components[component] += parameter.numel()
        if example_counts[component] < 3:
            examples.append({'name': name, 'shape': list(parameter.shape), 'device': str(parameter.device), 'dtype': str(parameter.dtype)})
            example_counts[component] += 1
    if not devices or any(not device.startswith('cuda:') for device in devices):
        raise RuntimeError('model parameters are not entirely CUDA-resident')
    properties = torch.cuda.get_device_properties(worker.device)
    folder = root / 'results/runtime-devices' / label
    folder.mkdir(parents=True, exist_ok=True)
    record = {'pid': os.getpid(), 'perf_counter': time.perf_counter(), 'system': os.environ['REPRO_SYSTEM_ROLE'],
              'only_vision_encoder': bool(getattr(worker.vllm_config.model_config, 'only_vision_encoder', False)),
              'model_class': type(model).__name__, 'parameters_by_device': dict(devices), 'parameters_by_dtype': dict(dtypes),
              'parameters_by_component': dict(components),
              'parameter_examples': examples, 'logical_device': str(worker.device), 'gpu_name': properties.name,
              'cuda_device_uuid': str(getattr(properties, 'uuid', 'not exposed by this torch build')),
              'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'), 'mps_pipe': os.environ.get('CUDA_MPS_PIPE_DIRECTORY'),
              'mps_active_thread_percentage': os.environ.get('CUDA_MPS_ACTIVE_THREAD_PERCENTAGE'),
              'loaded_smctrl': sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libsmctrl' in line})}
    record['loaded_smctrl_sha256'] = {}
    for library in record['loaded_smctrl']:
        value = hashlib.sha256()
        with Path(library).open('rb') as source:
            while data := source.read(1024**2):
                value.update(data)
        record['loaded_smctrl_sha256'][library] = value.hexdigest()
    (folder / f'worker-{os.getpid()}.json').write_text(json.dumps(record, indent=2))
    print('REPRO_DEVICE ' + json.dumps(record), flush=True)
    if record['only_vision_encoder'] and os.environ.get('REPRO_SM_PROBE') == '1':
        from service_sm_probe import arm_first_execution
        arm_first_execution(worker)
