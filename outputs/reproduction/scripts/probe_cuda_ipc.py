"""Check IPC pointer import and D2H reads; this does NOT validate peer D2D DMA."""
import argparse
import ctypes as C
import json
import os
import subprocess
import sys


class Handle(C.Structure):
    _fields_ = [("reserved", C.c_ubyte * 64)]


cuda = C.CDLL("/usr/local/cuda/lib64/libcudart.so")
cuda.cudaGetErrorString.restype = C.c_char_p


def check(code, operation):
    if code:
        raise RuntimeError(f"{operation}: {code}: {cuda.cudaGetErrorString(code).decode()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--child-handle")
    parser.add_argument("--child-device", type=int, default=1)
    args = parser.parse_args()
    size = 65536
    if args.child_handle:
        check(cuda.cudaSetDevice(args.child_device), "set child device")
        handle = Handle.from_buffer_copy(bytes.fromhex(args.child_handle))
        pointer = C.c_void_p()
        check(cuda.cudaIpcOpenMemHandle(C.byref(pointer), handle, 1), "cudaIpcOpenMemHandle")
        try:
            output = (C.c_ubyte * size)()
            check(cuda.cudaMemcpy(output, pointer, C.c_size_t(size), 2), "cudaMemcpy device to host")
            assert all(value == 0x5A for value in output), "IPC data mismatch"
            print(json.dumps({"ipc_open": True, "bytes_verified": size, "data_equal": True}))
        finally:
            check(cuda.cudaIpcCloseMemHandle(pointer), "cudaIpcCloseMemHandle")
        return
    check(cuda.cudaSetDevice(0), "set parent device")
    peer = C.c_int()
    check(cuda.cudaDeviceCanAccessPeer(C.byref(peer), 1, 0), "cudaDeviceCanAccessPeer")
    pointer = C.c_void_p()
    check(cuda.cudaMalloc(C.byref(pointer), C.c_size_t(size)), "cudaMalloc")
    try:
        check(cuda.cudaMemset(pointer, 0x5A, C.c_size_t(size)), "cudaMemset")
        check(cuda.cudaDeviceSynchronize(), "cudaDeviceSynchronize")
        handle = Handle()
        check(cuda.cudaIpcGetMemHandle(C.byref(handle), pointer), "cudaIpcGetMemHandle")
        child = subprocess.run([sys.executable, __file__, "--child-handle", bytes(handle).hex(),
                                "--child-device", str(args.child_device)],
                               capture_output=True, text=True, timeout=60)
        result = {"cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                  "peer_access": bool(peer.value), "child_returncode": child.returncode,
                  "stdout": child.stdout, "stderr": child.stderr}
        print(json.dumps(result, indent=2), flush=True)
        if child.returncode:
            raise SystemExit(child.returncode)
    finally:
        check(cuda.cudaFree(pointer), "cudaFree")


if __name__ == "__main__":
    main()
