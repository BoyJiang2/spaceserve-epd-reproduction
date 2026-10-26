"""Wait for complete gzip exports before stopping asynchronous profiler workers."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time


def wait(directory, pids, timeout=300, interval=1):
    deadline = time.monotonic() + timeout
    sizes, complete = {}, {}
    while time.monotonic() < deadline:
        for pid in pids:
            if pid in complete:
                continue
            paths = list(directory.glob(f'*_{pid}.*.pt.trace.json.gz'))
            if len(paths) > 1:
                raise RuntimeError(f'multiple profiler exports for worker {pid}')
            if not paths:
                continue
            path = paths[0]
            size = path.stat().st_size
            if not size or sizes.get(pid) != size:
                sizes[pid] = size
                continue
            try:
                uncompressed = 0
                with gzip.open(path, 'rb') as stream:
                    while block := stream.read(1024**2):
                        uncompressed += len(block)
            except (EOFError, gzip.BadGzipFile):
                continue
            value = hashlib.sha256()
            with path.open('rb') as stream:
                while block := stream.read(1024**2):
                    value.update(block)
            complete[pid] = {'file': str(path), 'compressed_bytes': size, 'uncompressed_bytes': uncompressed,
                             'gzip_complete_crc_checked': True, 'sha256': value.hexdigest()}
        if len(complete) == len(pids):
            for pid, record in complete.items():
                paths = list(directory.glob(f'*_{pid}.*.pt.trace.json.gz'))
                if len(paths) != 1 or str(paths[0]) != record['file'] or paths[0].stat().st_size != record['compressed_bytes']:
                    raise RuntimeError('profiler exports changed while waiting for other workers')
            return complete
        time.sleep(interval)
    raise RuntimeError('profiler export incomplete for worker PIDs: ' + str(sorted(set(pids) - set(complete))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--device-records', type=Path, required=True)
    parser.add_argument('--workers', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pids = {json.loads(path.read_text())['pid'] for path in args.device_records.glob('worker-*.json')}
    if len(pids) != args.workers:
        raise RuntimeError('actual loaded-worker count differs from expected role')
    result = wait(args.directory, pids)
    args.output.write_text(json.dumps({'passed': True, 'workers': result}, indent=2))
