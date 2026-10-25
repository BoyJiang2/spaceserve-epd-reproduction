"""Sample physical GPU use and memory attributed to experiment process trees."""
import argparse
import json
import os
import signal
import time
import psutil
import pynvml as nv


parser = argparse.ArgumentParser()
parser.add_argument("--devices", required=True)
parser.add_argument("--server-pids", required=True)
args = parser.parse_args()
devices = [int(value) for value in args.devices.split(",")]
roots = [psutil.Process(int(value)) for value in args.server_pids.split(",")]
assert all(process.uids().real == os.getuid() for process in roots)
nv.nvmlInit()
handles = {device: nv.nvmlDeviceGetHandleByIndex(device) for device in devices}
running = True


def stop(*_):
    global running
    running = False


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    while running:
        owned = set()
        for process in roots:
            try:
                owned.add(process.pid)
                owned.update(child.pid for child in process.children(recursive=True))
            except psutil.NoSuchProcess:
                pass
        if os.environ.get("CUDA_MPS_PIPE_DIRECTORY"):
            for process in psutil.process_iter(["pid", "name", "uids"]):
                try:
                    if (process.info["name"].startswith("nvidia-cuda-mps")
                            and process.info["uids"].real == os.getuid()
                            and process.environ().get("CUDA_MPS_PIPE_DIRECTORY") == os.environ["CUDA_MPS_PIPE_DIRECTORY"]):
                        owned.add(process.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        rows = []
        for device, handle in handles.items():
            processes = nv.nvmlDeviceGetComputeRunningProcesses(handle)
            total_bytes = nv.nvmlDeviceGetMemoryInfo(handle).total
            attribution = [{"pid": process.pid, "used_bytes": process.usedGpuMemory
                            if 0 <= process.usedGpuMemory <= total_bytes else None}
                           for process in processes if process.pid in owned]
            rows.append({"device": device, "physical_used_bytes": nv.nvmlDeviceGetMemoryInfo(handle).used,
                         "owned_processes": attribution,
                         "owned_process_sum_bytes": sum(item["used_bytes"] for item in attribution)
                         if all(item["used_bytes"] is not None for item in attribution) else None,
                         "utilization_gpu_percent": nv.nvmlDeviceGetUtilizationRates(handle).gpu})
        print(json.dumps({"perf_counter": time.perf_counter(), "gpus": rows}), flush=True)
        time.sleep(.1)
finally:
    nv.nvmlShutdown()
