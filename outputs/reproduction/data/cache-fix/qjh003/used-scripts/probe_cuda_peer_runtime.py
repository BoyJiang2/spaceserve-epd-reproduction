"""Independent CUDA-runtime P2P copy check; no PyTorch, Ray, or EPD imports."""
import argparse
import ctypes as C
import hashlib
import json
import os
import pathlib
import subprocess
import time


parser = argparse.ArgumentParser()
parser.add_argument("--bytes", type=int, default=1048576)
parser.add_argument("--output", type=pathlib.Path, required=True)
args = parser.parse_args()
visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
assert len(visible.split(",")) == 2 and all(visible.split(",")), "set CUDA_VISIBLE_DEVICES to two confirmed available GPUs"
apps = subprocess.check_output(["nvidia-smi", "--id=" + visible, "--query-compute-apps=pid", "--format=csv,noheader"], text=True).strip()
assert not apps, f"GPU processes already present: {apps}"
cuda = C.CDLL("/usr/local/cuda/lib64/libcudart.so")
cuda.cudaGetErrorString.restype = C.c_char_p


def check(code, label):
    if code:
        raise RuntimeError(f"{label}: {code}: {cuda.cudaGetErrorString(code).decode()}")


size = C.c_size_t(args.bytes)
source, destination = C.c_void_p(), C.c_void_p()
check(cuda.cudaSetDevice(0), "select source")
check(cuda.cudaMalloc(C.byref(source), size), "allocate source")
try:
    check(cuda.cudaMemset(source, 0x5A, size), "fill source")
    check(cuda.cudaDeviceSynchronize(), "synchronize source")
    source_host = (C.c_ubyte * args.bytes)()
    check(cuda.cudaMemcpy(source_host, source, size, 2), "verify source D2H")
    source_valid = bytes(source_host) == b"\x5a" * args.bytes
    assert source_valid
    check(cuda.cudaSetDevice(1), "select destination")
    check(cuda.cudaMalloc(C.byref(destination), size), "allocate destination")
    try:
        check(cuda.cudaMemset(destination, 0xA5, size), "fill destination")
        check(cuda.cudaDeviceSynchronize(), "synchronize destination")
        peer = C.c_int()
        check(cuda.cudaDeviceCanAccessPeer(C.byref(peer), 1, 0), "peer capability")
        enabled = cuda.cudaDeviceEnablePeerAccess(0, 0)
        assert enabled in (0, 704), enabled
        if enabled == 704:
            cuda.cudaGetLastError()
        started = time.perf_counter()
        check(cuda.cudaMemcpyPeer(destination, 1, source, 0, size), "peer copy")
        check(cuda.cudaDeviceSynchronize(), "peer completion")
        elapsed = time.perf_counter() - started
        destination_host = (C.c_ubyte * args.bytes)()
        check(cuda.cudaMemcpy(destination_host, destination, size, 2), "read destination D2H")
        actual = bytes(destination_host)
        result = {"cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"), "bytes": args.bytes,
                  "source_validated": source_valid, "peer_capability": bool(peer.value),
                  "copy_seconds": elapsed, "data_equal": actual == bytes(source_host),
                  "source_sha256": hashlib.sha256(bytes(source_host)).hexdigest(),
                  "destination_sha256": hashlib.sha256(actual).hexdigest(), "destination_prefix_hex": actual[:32].hex()}
        args.output.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2), flush=True)
        if not result["data_equal"]:
            raise SystemExit(1)
    finally:
        check(cuda.cudaFree(destination), "free destination")
finally:
    check(cuda.cudaSetDevice(0), "select source for cleanup")
    check(cuda.cudaFree(source), "free source")
