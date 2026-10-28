"""Fail fast on formal GPU contamination or attribution loss; preserve the triggering sample."""
import argparse
import json
import os
import signal
import time
import psutil
import pynvml as nv


running = True


def is_owned(pid, roots):
    try:
        process = psutil.Process(pid)
        if process.uids().real != os.getuid():
            return False
        # Compare Process identities (PID and creation time), not recycled PIDs.
        if any(root.is_running() and (process == root or root in process.parents()) for root in roots):
            return True
        pipe = os.environ.get("CUDA_MPS_PIPE_DIRECTORY")
        return bool(pipe and process.name().startswith("nvidia-cuda-mps")
                    and process.environ().get("CUDA_MPS_PIPE_DIRECTORY") == pipe)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def stop(*_):
    global running
    running = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--devices", required=True)
    parser.add_argument("--server-pids", required=True)
    args = parser.parse_args()
    devices = [int(value) for value in args.devices.split(",")]
    roots = [psutil.Process(int(value)) for value in args.server_pids.split(",")]
    assert all(process.uids().real == os.getuid() for process in roots)
    nv.nvmlInit()
    handles = {device: nv.nvmlDeviceGetHandleByIndex(device) for device in devices}
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        sample(handles, roots)
    finally:
        nv.nvmlShutdown()


def validate_sample(rows):
    if any(row['foreign_compute_pids'] for row in rows):
        raise RuntimeError('foreign target-GPU process observed; stop this cell')
    if any(not row['owned_processes'] or row['owned_process_sum_bytes'] is None for row in rows):
        raise RuntimeError('formal GPU memory attribution unavailable; stop this cell')


def sample(handles, roots):
    while running:
        rows = []
        for device, handle in handles.items():
            processes = nv.nvmlDeviceGetComputeRunningProcesses(handle)
            owned = {process.pid for process in processes if is_owned(process.pid, roots)}
            total_bytes = nv.nvmlDeviceGetMemoryInfo(handle).total
            attribution = [{"pid": process.pid, "used_bytes": process.usedGpuMemory
                            if 0 <= process.usedGpuMemory <= total_bytes else None}
                           for process in processes if process.pid in owned]
            rows.append({"device": device, "physical_used_bytes": nv.nvmlDeviceGetMemoryInfo(handle).used,
                         "owned_processes": attribution,
                         "owned_process_sum_bytes": sum(item["used_bytes"] for item in attribution)
                         if all(item["used_bytes"] is not None for item in attribution) else None,
                         "foreign_compute_pids": [process.pid for process in processes if process.pid not in owned],
                         "sm_clock_mhz": nv.nvmlDeviceGetClockInfo(handle, nv.NVML_CLOCK_SM),
                         "temperature_c": nv.nvmlDeviceGetTemperature(handle, nv.NVML_TEMPERATURE_GPU),
                         "utilization_gpu_percent": nv.nvmlDeviceGetUtilizationRates(handle).gpu})
        print(json.dumps({"perf_counter": time.perf_counter(), "cpu_loadavg": os.getloadavg(), "gpus": rows}), flush=True)
        validate_sample(rows)
        time.sleep(.1)


if __name__ == '__main__':
    main()
