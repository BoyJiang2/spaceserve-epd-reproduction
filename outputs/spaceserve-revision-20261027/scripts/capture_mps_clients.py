"""Check private MPS client identity and target-GPU processes at a run boundary.

Legacy MPS ps columns: https://docs.nvidia.com/deploy/mps/mpsv2-interface.html
"""
import argparse
import json
import os
from pathlib import Path
import subprocess


def parse_clients(text, allow_no_server=False):
    # Driver 535 reports this before the first CUDA client creates a server.
    if allow_no_server and text.strip() == 'Server not found':
        return []
    clients, header = [], False
    for line in text.splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[:5] == ['PID', 'ID', 'SERVER', 'DEVICE', 'NAMESPACE']:
            header = True
        elif header:
            if len(fields) < 6 or not all(fields[index].isdigit() for index in (0, 1, 2, 4)) or not fields[3].startswith('GPU-'):
                raise RuntimeError('unrecognized MPS client row')
            clients.append({'pid': int(fields[0]), 'server_pid': int(fields[2]), 'device_partial_uuid': fields[3]})
        elif not (len(fields) == 1 and fields[0].isdigit()):
            raise RuntimeError('unrecognized MPS status response')
    server_pids_only = bool(text.strip()) and all(line.strip().isdigit() for line in text.splitlines() if line.strip())
    if text.strip() and not header and not (allow_no_server and server_pids_only):
        raise RuntimeError('MPS client header missing')
    return clients


if __name__ == '__main__':
    import psutil
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-pid', type=int)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(os.environ['EXP_ROOT']).resolve()
    if str(root) != '/var/tmp/boyjiang-spaceserve-revision-20261027':
        raise RuntimeError('unexpected SpaceServe root')
    pipe = str(root / 'tmp/mps')
    owner = json.loads((root / 'evidence/mps-owner.json').read_text())
    text = subprocess.check_output(['bash', str(root / 'scripts/mps_control.sh'), 'status'], text=True)
    args.output.with_suffix('.status.txt').write_text(text)
    clients = parse_clients(text, allow_no_server=args.api_pid is None)
    expected = set()
    if args.api_pid is not None:
        api = psutil.Process(args.api_pid)
        expected = {api.pid, *(process.pid for process in api.children(recursive=True))}
    for item in clients:
        process = psutil.Process(item['pid'])
        environment = process.environ()
        if item['pid'] not in expected or process.uids().real != os.getuid() or environment.get('EXP_ROOT') != str(root) or environment.get('CUDA_MPS_PIPE_DIRECTORY') != pipe or environment.get('REPRO_RUN_ID') != os.environ['REPRO_RUN_ID']:
            raise RuntimeError('unexpected private MPS client; preserve and stop without killing it')
        if not owner['uuid'].startswith(item['device_partial_uuid']):
            raise RuntimeError('MPS client GPU differs from reserved GPU')
    raw = subprocess.check_output(['nvidia-smi', '--id=4', '--query-compute-apps=pid,gpu_uuid', '--format=csv,noheader'], text=True)
    physical = []
    for line in raw.splitlines():
        pid_text, uuid = line.split(',')
        process = psutil.Process(int(pid_text))
        environment = process.environ()
        private_server = process.name().startswith('nvidia-cuda-mps') and environment.get('REPRO_MPS_OWNER') == owner['token']
        if process.uids().real != os.getuid() or environment.get('CUDA_MPS_PIPE_DIRECTORY') != pipe or not (process.pid in expected or private_server) or uuid.strip() != owner['uuid']:
            raise RuntimeError('unexpected target-GPU process; do not terminate it')
        physical.append({'pid': process.pid, 'uuid': uuid.strip(), 'private_mps_server': private_server})
    if args.api_pid is not None and not clients:
        raise RuntimeError('no actual MPS client after model loading')
    args.output.write_text(json.dumps({'passed': True, 'clients': clients, 'physical_gpu_processes': physical,
                                      'scope': 'boundary snapshots; not continuous exclusion of transient clients'}, indent=2))
