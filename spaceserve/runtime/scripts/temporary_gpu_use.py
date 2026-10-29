"""Direct, conditional user grant for one idle GPU; never a booking or formal grant."""
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import threading
import time


UUID = 'GPU-c005197e-747d-2dc8-b77b-b123b41efd75'
BOOT = '65f52a67-afe4-4919-8646-4694255b48ee'
QUOTE = '如果gpu暂时没人用 你可以先暂时用一下'


def scope(config, phase):
    grant = config.get('temporary_gpu_use')
    if (config.get('project') != 'spaceserve' or phase not in ('numeric', 'model')
            or config.get('booking') is not None
            or not isinstance(grant, dict)
            or set(grant) != {'schema', 'start_ms', 'end_ms', 'boot_id', 'user_sha256'}
            or grant['schema'] != 'temporary-idle-single-gpu-v1'
            or grant['boot_id'] != BOOT or config.get('host') != 'qjh003'
            or config.get('uid') != 2147 or config.get('gpu_devices') != [2]
            or config.get('gpu_uuids') != [UUID]
            or config.get('workload_cpu_affinity') != list(range(90))
            or any(type(cpu) is not int for cpu in config['workload_cpu_affinity'])
            or config.get('workload_numa_node') != 0
            or any(type(grant[k]) is not int for k in ('start_ms', 'end_ms'))
            or not 0 < grant['end_ms'] - grant['start_ms'] <= 3600000
            or not isinstance(grant['user_sha256'], str)
            or len(grant['user_sha256']) != 64):
        raise ValueError('Exact conditional single-GPU2 numeric/model scope required')
    return grant


def original(root, name):
    path = root/'evidence'/name
    if path.is_symlink() or path.stat().st_uid != os.getuid() or not path.is_file():
        raise ValueError('Owned regular temporary-use evidence required')
    return path.read_bytes()


def process_rows():
    try:
        raw = subprocess.check_output(['nvidia-smi', '--id=2', '--query-compute-apps=pid,gpu_uuid',
                                       '--format=csv,noheader,nounits'], text=True, timeout=.5)
    except (subprocess.SubprocessError, OSError) as error:
        partial = getattr(error, 'output', '') or ''
        if isinstance(partial, bytes): partial = partial.decode('utf8', errors='replace')
        return {'raw': partial, 'processes': [], 'query_error': repr(error)}
    rows = []
    for line in raw.splitlines():
        values = [part.strip() for part in line.split(',')]
        if len(values) != 2 or not values[0].isdigit() or values[1] != UUID:
            return {'raw': raw, 'processes': rows, 'query_error': 'Unresolved selected-GPU process record'}
        rows.append({'pid': int(values[0]), 'gpu_uuid': values[1]})
    return {'raw': raw, 'processes': rows}


def owned_process(row, root):
    import psutil
    process = psutil.Process(row['pid'])
    created = process.create_time()
    environment = process.environ()
    if (process.uids().real != os.getuid() or environment.get('EXP_ROOT') != str(root)
            or not environment.get('REPRO_RUN_ID', '').startswith(str(root) + ':')):
        raise RuntimeError('Foreign or unknown selected-GPU process')
    if process.name().startswith('nvidia-cuda-mps'):
        state = json.loads(original(root, 'mps-owner.json'))
        pipe = root/'tmp/mps'
        if (environment.get('CUDA_MPS_PIPE_DIRECTORY') != str(root/'tmp/mps')
                or environment.get('REPRO_MPS_OWNER') != state.get('token')
                or state.get('state') != 'running' or state.get('uuid') != UUID
                or state.get('pipe') != str(pipe) or type(state.get('pid')) is not int
                or state['pid'] <= 0 or type(state.get('created')) not in (int, float)
                or not math.isfinite(state['created']) or type(state.get('control_inode')) is not int
                or (pipe/'control').is_symlink() or (pipe/'control').stat().st_ino != state['control_inode']):
            raise RuntimeError('Unknown MPS process/pipe ownership')
        daemon = psutil.Process(state['pid'])
        daemon_environment = daemon.environ()
        if (daemon.uids().real != os.getuid() or daemon.create_time() != state['created']
                or not daemon.name().startswith('nvidia-cuda-mps-control')
                or daemon_environment.get('EXP_ROOT') != str(root)
                or not daemon_environment.get('REPRO_RUN_ID', '').startswith(str(root)+':')
                or daemon_environment.get('CUDA_MPS_PIPE_DIRECTORY') != str(pipe)
                or daemon_environment.get('REPRO_MPS_OWNER') != state['token']
                or daemon_environment.get('CUDA_VISIBLE_DEVICES') != UUID
                or not any(parent.pid == state['pid'] and parent.create_time() == state['created']
                           for parent in [process, *process.parents()])
                or psutil.Process(state['pid']).create_time() != state['created']):
            raise RuntimeError('MPS server is not bound to the exact owned daemon')
    elif not Path(process.cwd()).is_relative_to(root):
        raise RuntimeError('Selected-GPU process cwd is outside this run')
    if psutil.Process(row['pid']).create_time() != created:
        raise RuntimeError('Selected-GPU PID identity changed')
    return {'pid': process.pid, 'created_epoch': created, 'uid': os.getuid(),
            'root': str(root), 'run_id': environment['REPRO_RUN_ID']}


def remaining(config, root, phase, *, fresh=False, wall=time.time, clock=time.monotonic):
    grant = scope(config, phase)
    if socket.gethostname() != config['host'] or os.getuid() != config['uid']:
        raise ValueError('Actual temporary-use host/UID differs')
    now = int(wall() * 1000)
    if not grant['start_ms'] <= now < grant['end_ms'] - 120000:
        raise TimeoutError('Outside the fixed temporary-use work window')
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != BOOT:
        raise ValueError('Temporary-use boot changed')
    user = original(root, 'TEMPORARY_GPU_USE_USER.txt')
    if hashlib.sha256(user).hexdigest() != grant['user_sha256'] or QUOTE not in user.decode('utf8'):
        raise ValueError('Original direct user authorization is missing or changed')
    approved = json.loads(original(root, 'TEMPORARY_GPU_USE_APPROVED.json'))
    configuration_sha = hashlib.sha256((root/'configs/project.json').read_bytes()).hexdigest()
    if (approved.get('passed') is not True or approved.get('scope') != 'temporary-idle-GPU2-preflight-only'
            or approved.get('project_config_sha256') != configuration_sha
            or approved.get('source_commit') != config['source_commit']
            or approved.get('source_manifest_sha256') != config['source_manifest_sha256']
            or approved.get('user_sha256') != grant['user_sha256']
            or approved.get('allowed_actions') != ['numeric', 'model']):
        raise ValueError('Independent approval does not bind this temporary source/config/grant')
    for gate in ('G1', 'G2'):
        review = original(root, 'TEMPORARY_GPU_USE_' + gate + '.md')
        if hashlib.sha256(review).hexdigest() != approved.get(gate + '_review_sha256'):
            raise ValueError('Original independent temporary-use review changed')
    marker = root/'evidence/TEMPORARY_GPU_USE_STARTED.json'
    identity = {'project_config_sha256': configuration_sha, 'boot_id': BOOT,
                'start_ms': grant['start_ms'], 'end_ms': grant['end_ms']}
    if not marker.exists():
        if not fresh:
            raise ValueError('Temporary batch has not been started under a fresh idle check')
        with marker.open('x') as output:
            anchor = clock()
            json.dump({**identity, 'anchor_monotonic': anchor, 'anchor_wall_ms': now,
                       'deadline_monotonic': anchor + (grant['end_ms'] - now)/1000}, output)
    started = json.loads(original(root, marker.name))
    if any(started.get(k) != v for k, v in identity.items()):
        raise ValueError('Temporary batch anchor changed; no automatic extension')
    if (any(type(started.get(k)) not in (int, float) or not math.isfinite(started[k])
            for k in ('anchor_monotonic', 'anchor_wall_ms', 'deadline_monotonic'))
            or not grant['start_ms'] <= started['anchor_wall_ms'] < grant['end_ms']
            or clock() < started['anchor_monotonic']
            or started['deadline_monotonic'] != started['anchor_monotonic'] + (grant['end_ms'] - started['anchor_wall_ms'])/1000):
        raise ValueError('Invalid temporary monotonic deadline anchor')
    seconds = min((grant['end_ms'] - now)/1000, started['deadline_monotonic'] - clock()) - 120
    if seconds <= 0:
        raise TimeoutError('Temporary batch cleanup reserve reached')
    if fresh:
        raw = subprocess.check_output(['nvidia-smi', '--id=2', '--query-gpu=uuid,memory.used,utilization.gpu',
                                       '--format=csv,noheader,nounits'], text=True, timeout=.5)
        fields = [part.strip() for part in raw.strip().split(',')]
        processes = process_rows()
        evidence = {'origin': 'direct_user_conditional_idle_use', 'booking_claimed': False,
                    'observed_ms': now, 'phase': phase, 'gpu_raw': raw, **processes}
        with (root/'evidence'/('TEMPORARY_GPU_USE_IDLE-' + phase + '.json')).open('x') as output:
            json.dump(evidence, output, indent=2)
        if processes.get('query_error') or len(fields) != 3 or fields[0] != UUID or int(fields[1]) > 100 or int(fields[2]) != 0 or processes['processes']:
            raise RuntimeError('Temporary selected GPU is no longer idle')
    return seconds


@contextlib.contextmanager
def supervise(config, root, phase):
    if not config.get('temporary_gpu_use'):
        yield
        return
    remaining(config, root, phase)
    own_pid = os.getpid()
    stop = threading.Event()
    failure = []
    log = (root/'evidence'/('TEMPORARY_GPU_USE_MONITOR-' + phase + '.jsonl')).open('x')

    def sample():
        while not stop.is_set():
            row = {'monotonic': time.monotonic(), 'observed_ms': int(time.time()*1000)}
            try:
                remaining(config, root, phase)
                row.update(process_rows())
                if row.get('query_error'):
                    raise RuntimeError(row['query_error'])
                row['owned'] = [owned_process(item, root) for item in row['processes']]
            except BaseException as error:
                row['error'] = type(error).__name__ + ': ' + str(error)
                failure.append(row)
            try:
                log.write(json.dumps(row) + '\n'); log.flush()
            except BaseException as error:
                failure.append({'journal_error': repr(error)})
            if failure:
                # Signal only this already-bound controller; never a PID from the GPU query.
                os.kill(own_pid, signal.SIGTERM)
                return
            stop.wait(.5)

    monitor = threading.Thread(target=sample, daemon=True)
    monitor.start()
    try:
        yield
    finally:
        stop.set(); monitor.join(timeout=2)
        if not monitor.is_alive():
            log.close()
        if monitor.is_alive() or failure:
            raise RuntimeError('Temporary-use monitoring stopped this phase; retain triggering evidence')
