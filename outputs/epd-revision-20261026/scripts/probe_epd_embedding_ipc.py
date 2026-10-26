"""Validate EPD's unmodified embedding IPC operator for eight MiniCPM images."""
import argparse
import json
import multiprocessing as mp
import os
import pathlib
import subprocess
import time


def produce(pipe, device, library):
    os.environ['CUDA_VISIBLE_DEVICES'] = str(device)
    import torch
    torch.ops.load_library(library)
    cache = torch.zeros((32, 64, 3584), dtype=torch.float16, device='cuda')
    expected = torch.arange(1, 9, dtype=torch.float16, device='cuda')[:, None, None]
    cache[:8].copy_(expected)
    torch.cuda.synchronize()
    assert bool(torch.all(cache[:8] == expected).item())
    pipe.send({'handle': torch.ops.block_migration_ops.get_ipc_mem_handle(cache), 'source_validated': True})
    assert pipe.poll(120), 'consumer did not finish'
    pipe.recv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=int, default=0)
    parser.add_argument('--destination', type=int, default=1)
    parser.add_argument('--library', required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    assert args.source != args.destination
    assert not subprocess.check_output(['nvidia-smi', f'--id={args.source},{args.destination}', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip()
    context = mp.get_context('spawn')
    parent, child = context.Pipe()
    source = context.Process(target=produce, args=(child, args.source, args.library))
    source.start()
    try:
        os.environ['CUDA_VISIBLE_DEVICES'] = str(args.destination)
        import torch
        torch.ops.load_library(args.library)
        cache = torch.full((32, 64, 3584), -1, dtype=torch.float16, device='cuda')
        expected = torch.arange(1, 9, dtype=torch.float16, device='cuda')[:, None, None]
        assert parent.poll(60), 'producer timed out'
        message = parent.recv()
        parallel = [1, 0, 1, 0, 1, 0]
        torch.ops.block_migration_ops.register_ipc_mem_handle_encoding(message['handle'], parallel, parallel)
        torch.cuda.synchronize()
        records = []
        for repetition in range(3):
            first = repetition * 8
            started, ended = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
            started.record()
            begin = time.perf_counter()
            torch.ops.block_migration_ops.migrate_blocks_encoding(1, 1, 0, list(range(8)), 1, 1, 0, 0, list(range(first, first + 8)), cache)
            ended.record()
            ended.synchronize()
            completed = time.perf_counter()
            equal = bool(torch.all(cache[first:first + 8] == expected).item())
            records.append({'repetition': repetition, 'data_equal': equal, 'complete_ms': (completed - begin) * 1000, 'gpu_ms': started.elapsed_time(ended)})
            assert equal, records[-1]
        result = {'source_gpu': args.source, 'destination_gpu': args.destination, 'cache_shape': list(cache.shape), 'source_validated': message['source_validated'], 'bytes_per_copy': 8 * 64 * 3584 * 2, 'records': records}
        args.output.write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    finally:
        parent.send('done')
        source.join(10)
        if source.is_alive():
            source.terminate()
            source.join()


if __name__ == '__main__':
    main()
