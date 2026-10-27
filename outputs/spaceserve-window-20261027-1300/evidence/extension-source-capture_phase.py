"""Post-exit numeric/model evidence only; no inference, signals or cleanup."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

from phase_identity import validate_terminal

ROOT = Path('/var/tmp/boyjiang-spaceserve-window-20261027-1300')
UUID = 'GPU-79214c80-7778-37d9-282b-89228debbb69'
PHASES = {
    'numeric': ('NUMERIC_STARTED.json', 'numeric-exit.json', 'numeric-controller.log',
                'results/numeric', 'numeric-resource-status.json', 'numeric-files.json'),
    'model': ('MODELS_ATTEMPT1_STARTED.json', 'models-attempt1-exit.json', 'models-attempt1-controller.log',
              'results/preflight-models-attempt1', 'model-attempt1-terminal.json', 'model-attempt1-files.json')}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024**2):
            digest.update(block)
    return digest.hexdigest()


def selected_files(root, phase):
    marker, exit_name, log_name, result_dir, _, _ = PHASES[phase]
    selected = {root/'evidence'/name for name in (marker, exit_name, log_name)}
    directories = [root/result_dir, root/'logs/mps']
    if phase == 'model':
        directories += [root/'results/runtime-devices'/('preflight-'+trial+'-'+role)
                        for trial in ('cold', 'restart') for role in ('baseline-space', 'space', 'space-mask')]
        selected.update((root/'evidence').glob('mps-start-intent-model-*.json'))
        selected.update((root/'evidence').glob('models-attempt1-launcher*.log'))
        selected.update((root/'evidence').glob('model-attempt1-launcher*.log'))
    else:
        selected.update((root/'evidence').glob('mps-start-intent-*.json'))
        selected.update((root/'evidence').glob('numeric-launcher*.log'))
    for directory in directories:
        if directory.exists():
            selected.update(path for path in directory.rglob('*') if path.is_file())
    return selected


def phase_code(phase):
    from resource_guard import code_identity
    numeric = code_identity(None if phase == 'model' else 'numeric')
    if phase == 'model':
        from model_guard import model_code
        return numeric, model_code()
    return numeric, numeric


def main(phase, expected_start, expected_producer):
    if not __debug__ or socket.gethostname() != 'qjh000' or os.getuid() != 2147:
        raise RuntimeError('capture host/UID/debug differs')
    if not all(re.fullmatch('[a-f0-9]{64}', value) for value in (expected_start, expected_producer)):
        raise RuntimeError('actual observed launch and producer SHA required')
    marker, exit_name, log_name, result_dir, status_name, inventory_name = PHASES[phase]
    outputs = [ROOT/'evidence'/name for name in (status_name, inventory_name,
               phase+'-final-owner.json', phase+'-booking-at-capture.json')]
    if any(path.exists() or path.is_symlink() for path in outputs):
        raise RuntimeError('refuse capture evidence overwrite')
    started_path = ROOT/'evidence'/marker
    if sha(started_path) != expected_start:
        raise RuntimeError('launch differs from independently observed start')
    started = json.loads(started_path.read_text())
    terminal = json.loads((ROOT/'evidence'/exit_name).read_text())
    validate_terminal(started, terminal)
    sys.path.insert(0, str(ROOT/'scripts'))
    from resource_guard import remaining_owned
    numeric, code = phase_code(phase)
    if code != expected_producer:
        raise RuntimeError('actual phase producer differs')
    owned = remaining_owned()
    if owned:
        raise RuntimeError('owned/unconfirmed processes remain; no bulk capture: '+str(owned))
    gpu = subprocess.check_output(['nvidia-smi', '--id=4',
        '--query-gpu=index,uuid,memory.used,utilization.gpu', '--format=csv,noheader,nounits'], text=True, timeout=20)
    compute = subprocess.check_output(['nvidia-smi', '--id=4', '--query-compute-apps=pid,gpu_uuid',
        '--format=csv,noheader'], text=True, timeout=20)
    owner_path = ROOT/'evidence/mps-owner.json'
    owner_bytes = owner_path.read_bytes(); owner = json.loads(owner_bytes)
    fields = [part.strip() for part in gpu.strip().split(',')]
    if (len(fields) != 4 or fields[:2] != ['4', UUID] or int(fields[2]) != 0 or compute.strip()
            or owner.get('state') != 'stopped' or owner.get('uuid') != UUID
            or owner.get('pipe') != str(ROOT/'tmp/mps')
            or owner.get('active_thread_percentage') != 100
            or not owner.get('token', '').startswith(str(ROOT)+':mps:')):
        raise RuntimeError('correct GPU/private MPS release not confirmed; no bulk capture')
    booking_bytes = (ROOT/'evidence/BOOKING_VERIFIED.json').read_bytes()
    selected = selected_files(ROOT, phase)
    files = []
    for path in sorted(selected):
        if not path.resolve(strict=True).is_relative_to(ROOT):
            raise RuntimeError('capture member escapes root')
        for part in (path, *path.parents):
            if part.is_symlink():
                raise RuntimeError('capture refuses linked member or ancestor')
            if part == ROOT:
                break
        before = path.stat()
        digest = sha(path)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError('capture source changed during hashing')
        files.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': after.st_size, 'sha256': digest})
    state = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'phase': phase,
             'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
             'code_manifest_sha256': code, 'numeric_code_manifest_sha256': numeric,
             'gpus': gpu, 'compute': compute, 'owned_processes': owned,
             'same_controller_live': False, 'same_child_live': False, 'exit': terminal,
             'MPS': owner, 'released': True, 'new_inference_requests': 0,
             'grants_no_G3': True,
             'capture_helper_sha256': sha(Path(__file__)),
             'identity_helper_sha256': sha(Path(__file__).with_name('phase_identity.py'))}
    if phase == 'model':
        state['model_code_manifest_sha256'] = code
    with outputs[0].open('x') as output:
        json.dump(state, output, indent=2)
    with outputs[1].open('x') as output:
        json.dump({'phase': phase, 'producer_sha256': code, 'code_manifest_sha256': code, 'files': files}, output, indent=2)
    with outputs[2].open('xb') as output:
        output.write(owner_bytes)
    with outputs[3].open('xb') as output:
        output.write(booking_bytes)
    print(json.dumps({'phase': phase, 'released': True, 'actual_exit': terminal['exit_code'], 'files': len(files)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=PHASES)
    parser.add_argument('--start-sha', required=True)
    parser.add_argument('--producer-sha', required=True)
    args = parser.parse_args()
    main(args.phase, args.start_sha, args.producer_sha)
