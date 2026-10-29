"""Capture an existing service configuration without changing the service."""
import argparse
import datetime
import importlib.metadata
import json
import os
import pathlib
import re
import psutil
from cpu_placement import snapshot, validate, ENVIRONMENT
from runtime_config import context


parser = argparse.ArgumentParser()
parser.add_argument("output", type=pathlib.Path)
parser.add_argument("--server-pids", required=True)
parser.add_argument("--devices", required=True)
parser.add_argument("--note", default="Captured from the still-running service after measurement; initial matrix predates the runtime-config writer")
args = parser.parse_args()
keys = ["CUDA_VISIBLE_DEVICES", "CUDA_MPS_PIPE_DIRECTORY", "VLLM_USE_V1", "PYTHONPATH", "VLLM_LIBSMCTRL_PATH", "CUDA_IPC_LIB_PATH", *ENVIRONMENT]
layout = context()
config = layout.config
servers = []
for pid in map(int, args.server_pids.split(",")):
    process = psutil.Process(pid)
    environment = process.environ()
    placement = snapshot(pid)
    validate(placement, config)
    servers.append({"pid": pid, "created_epoch_seconds": process.create_time(), "command": process.cmdline(),
                    "cpu_placement": placement,
                    "environment": {key: environment.get(key) for key in keys}})
workers = []
if 'workload_cpu_affinity' in config:
    label = os.environ.get('REPRO_SPACE_RUN_LABEL', '')
    if not re.fullmatch('[a-z0-9-]+', label):
        raise RuntimeError('Missing CPU placement worker label')
    folder = layout.run_root/'results/runtime-devices'/label
    for path in sorted(folder.glob('worker-*.json')):
        original = json.loads(path.read_text())['cpu_placement']
        current = snapshot(original['pid'])
        if (current['start_ticks'], current['uid']) != (original['start_ticks'], original['uid']):
            raise RuntimeError('Worker identity changed before CPU placement boundary')
        validate(current, config)
        workers.append(current)
    if not workers:
        raise RuntimeError('Missing actual worker CPU placement evidence')
record = {"captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "capture_note": args.note,
          "devices": args.devices, "servers": servers, "workers_cpu_placement": workers,
          "packages": {name: importlib.metadata.version(name) for name in ["vllm", "torch", "transformers"]}}
args.output.write_text(json.dumps(record, indent=2))
print(json.dumps(record, indent=2))
