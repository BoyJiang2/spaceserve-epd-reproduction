"""Capture an existing service configuration without changing the service."""
import argparse
import datetime
import importlib.metadata
import json
import pathlib
import psutil


parser = argparse.ArgumentParser()
parser.add_argument("output", type=pathlib.Path)
parser.add_argument("--server-pids", required=True)
parser.add_argument("--devices", required=True)
parser.add_argument("--note", default="Captured from the still-running service after measurement; initial matrix predates the runtime-config writer")
args = parser.parse_args()
keys = ["CUDA_VISIBLE_DEVICES", "CUDA_MPS_PIPE_DIRECTORY", "VLLM_USE_V1", "PYTHONPATH", "VLLM_LIBSMCTRL_PATH", "CUDA_IPC_LIB_PATH"]
servers = []
for pid in map(int, args.server_pids.split(",")):
    process = psutil.Process(pid)
    environment = process.environ()
    servers.append({"pid": pid, "created_epoch_seconds": process.create_time(), "command": process.cmdline(),
                    "environment": {key: environment.get(key) for key in keys}})
record = {"captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "capture_note": args.note,
          "devices": args.devices, "servers": servers,
          "packages": {name: importlib.metadata.version(name) for name in ["vllm", "torch", "transformers"]}}
args.output.write_text(json.dumps(record, indent=2))
print(json.dumps(record, indent=2))
