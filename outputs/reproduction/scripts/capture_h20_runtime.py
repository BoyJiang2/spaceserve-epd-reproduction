"""Record actual libraries and GPU placement of this experiment's live workers."""
import argparse
import datetime
import importlib.metadata
import json
import os
import pathlib
import subprocess
import psutil

parser = argparse.ArgumentParser()
parser.add_argument('root', type=pathlib.Path)
parser.add_argument('--output', type=pathlib.Path, required=True)
args = parser.parse_args()
root = str(args.root.resolve())
raw = subprocess.check_output(['nvidia-smi', '--id=0,1,2', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader'], text=True)
workers = []
for line in raw.splitlines():
    uuid, pid = line.split(',')
    process = psutil.Process(int(pid))
    assert process.uids().real == os.getuid()
    assert any(root in ' '.join(parent.cmdline()) for parent in [process] + process.parents())
    environment = process.environ()
    workers.append({'gpu_uuid': uuid.strip(), 'pid': process.pid, 'command': [arg for arg in process.cmdline() if arg],
                    'cuda_visible_devices': environment.get('CUDA_VISIBLE_DEVICES'),
                    'loaded_cublas_libraries': sorted({mapping.path for mapping in process.memory_maps() if 'libcublas' in mapping.path})})
assert len(workers) == 3 and all(len(worker['loaded_cublas_libraries']) == 2 for worker in workers)
record = {'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'boot_id': pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'packages': {name: importlib.metadata.version(name) for name in ['torch', 'vllm', 'transformers', 'nvidia-cublas-cu12']},
          'workers': workers}
args.output.write_text(json.dumps(record, indent=2))
print(json.dumps({'workers': len(workers), 'packages': record['packages'], 'boot_id': record['boot_id']}))
