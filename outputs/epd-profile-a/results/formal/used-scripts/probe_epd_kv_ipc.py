"""Time and validate EPD's original KV copy with its actual MiniCPM cache shape."""
import argparse
import json
import math
import multiprocessing as mp
import os
import pathlib
import subprocess
import time
import traceback


def source_process(connection, device, library, cache_blocks, transfer_blocks):
    try:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(device)
        import torch
        torch.ops.load_library(library)
        cache = torch.empty((28, 2, cache_blocks, 16, 4, 128), dtype=torch.float16, device="cuda")
        values = torch.arange(1, transfer_blocks + 1, dtype=torch.float16, device="cuda")
        cache[:, :, :transfer_blocks].copy_(values[None, None, :, None, None, None])
        torch.cuda.synchronize()
        expected = values[None, None, :, None, None, None]
        assert bool(torch.all(cache[:, :, :transfer_blocks] == expected).item())
        connection.send({"handle": torch.ops.block_migration_ops.get_ipc_mem_handle(cache), "pointer": hex(cache.data_ptr()), "source_validated": True})
        if connection.poll(240):
            connection.recv()
    except Exception:
        connection.send({"error": traceback.format_exc()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=int, required=True)
    parser.add_argument("--destination", type=int, required=True)
    parser.add_argument("--library", required=True)
    parser.add_argument("--cache-blocks", type=int, default=24728)
    parser.add_argument("--transfer-blocks", type=int, default=18)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    assert args.source != args.destination and args.transfer_blocks * args.repetitions <= args.cache_blocks
    apps = subprocess.check_output(["nvidia-smi", f"--id={args.source},{args.destination}",
                                    "--query-compute-apps=pid", "--format=csv,noheader"], text=True).strip()
    assert not apps, f"GPU processes already present: {apps}"
    context = mp.get_context("spawn")
    parent, child = context.Pipe()
    source = context.Process(target=source_process, args=(child, args.source, args.library, args.cache_blocks, args.transfer_blocks))
    source.start()
    try:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args.destination)
        import torch
        torch.ops.load_library(args.library)
        cache = torch.empty((28, 2, args.cache_blocks, 16, 4, 128), dtype=torch.float16, device="cuda")
        assert parent.poll(60), "source initialization timed out"
        message = parent.recv()
        assert "error" not in message, message
        parallel = [1, 0, 1, 0, 1, 0]
        torch.ops.block_migration_ops.register_ipc_mem_handle_context(message["handle"], 28, 4, parallel, parallel)
        torch.cuda.synchronize()
        records = []
        for repetition in range(args.repetitions):
            source_blocks = list(range(args.transfer_blocks))
            target_blocks = list(range(repetition * args.transfer_blocks, (repetition + 1) * args.transfer_blocks))
            started = torch.cuda.Event(enable_timing=True)
            ended = torch.cuda.Event(enable_timing=True)
            started.record()
            cpu_started = time.perf_counter()
            torch.ops.block_migration_ops.migrate_blocks_context(1, 1, 0, source_blocks, 1, 1, 0, 0, target_blocks, cache)
            enqueued = time.perf_counter()
            ended.record()
            ended.synchronize()
            completed = time.perf_counter()
            expected = torch.arange(1, args.transfer_blocks + 1, dtype=torch.float16, device="cuda")[None, None, :, None, None, None]
            actual = cache[:, :, target_blocks[0]:target_blocks[-1] + 1]
            equal = bool(torch.all(actual == expected).item())
            record = {"repetition": repetition, "enqueue_ms": (enqueued - cpu_started) * 1000,
                      "complete_ms": (completed - cpu_started) * 1000, "gpu_ms": started.elapsed_time(ended), "data_equal": equal,
                      "samples": [[[value if math.isfinite(value) else str(value) for value in group]
                                   for group in layer] for layer in actual[:, :, :3, 0, 0, 0].tolist()]}
            records.append(record)
            print(json.dumps(record), flush=True)
            if not equal:
                break
        torch.ops.block_migration_ops.unregister_ipc_mem_handle_context(28, 4, parallel, parallel)
        result = {"source_gpu": args.source, "destination_gpu": args.destination, "cache_shape": list(cache.shape),
                  "source_validation": message, "destination_pointer": hex(cache.data_ptr()),
                  "bytes_copied_per_repetition": 28 * 2 * args.transfer_blocks * 16 * 4 * 128 * 2, "records": records}
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False))
    finally:
        parent.send("done")
        source.join(10)
        if source.is_alive():
            source.terminate()
            source.join()
    if any(not record["data_equal"] for record in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
