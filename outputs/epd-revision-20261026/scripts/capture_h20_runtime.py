"""Record actual libraries and GPU placement of this experiment's live workers."""
import argparse
import datetime
import hashlib
import sys
import importlib.metadata
import json
import os
import pathlib
import subprocess
import psutil
from resource_guard import DEVICES

parser = argparse.ArgumentParser()
parser.add_argument('root', type=pathlib.Path)
parser.add_argument('--output', type=pathlib.Path, required=True)
args = parser.parse_args()
root = str(args.root.resolve())
raw = subprocess.check_output(['nvidia-smi', '--id=' + ','.join(map(str, DEVICES)), '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader'], text=True)
workers = []
for line in raw.splitlines():
    uuid, pid = line.split(',')
    process = psutil.Process(int(pid))
    assert process.uids().real == os.getuid()
    assert any(root in ' '.join(parent.cmdline()) for parent in [process] + process.parents())
    environment = process.environ()
    assert environment.get('REPRO_RUN_ID') == os.environ['REPRO_RUN_ID'], 'worker lacks current cleanup identity'
    workers.append({'gpu_uuid': uuid.strip(), 'pid': process.pid, 'command': [arg for arg in process.cmdline() if arg],
                    'cuda_visible_devices': environment.get('CUDA_VISIBLE_DEVICES'),
                    'cpu_affinity': process.cpu_affinity(),
                    'allowed_numa_nodes': next(line.split(':',1)[1].strip() for line in pathlib.Path('/proc',str(process.pid),'status').read_text().splitlines() if line.startswith('Mems_allowed_list:')),
                    'loaded_cublas_libraries': sorted({mapping.path for mapping in process.memory_maps() if 'libcublas' in mapping.path})})
assert len(workers) == 3 and all(len(worker['loaded_cublas_libraries']) == 2 for worker in workers)
libraries = {path: hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest() for path in {path for worker in workers for path in worker['loaded_cublas_libraries']}}
record = {'python_prefix': sys.prefix, 'loaded_cublas_sha256': libraries, 'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'collector_cpu_affinity': sorted(os.sched_getaffinity(0)),
          'cpu_numa_strategy': 'No added taskset/numactl policy; inherited affinity recorded per worker.',
          'boot_id': pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'packages': {name: importlib.metadata.version(name) for name in ['torch', 'vllm', 'transformers', 'nvidia-cublas-cu12']},
          'workers': workers}
args.output.write_text(json.dumps(record, indent=2))
print(json.dumps({'workers': len(workers), 'packages': record['packages'], 'boot_id': record['boot_id']}))
