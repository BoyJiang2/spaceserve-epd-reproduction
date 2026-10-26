"""Run only gate-approved cells in fixed order with exact owned-process cleanup."""
import argparse
import asyncio
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

from correctness_suite import run as check_suite
from owned_processes import stop
from resource_guard import ROOT, UUIDS, DEVICES, exclusive, gate, idle, sha, code_identity
from booking_window import require as booking_required

PYTHON = str(ROOT / 'envs/epd/bin/python')


def post(url, operation):
    data = json.dumps({'operation': operation}).encode()
    request = urllib.request.Request(url + '/repro/observe', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=65) as response:
        return json.load(response)


@contextlib.contextmanager
def services(system, mode, destination):
    booking_required()
    idle()
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'logs').mkdir()
    identity = str(ROOT) + ':' + destination.name + ':' + uuid.uuid4().hex
    env = dict(os.environ, REPRO_RUN_ID=identity, REPRO_OBSERVE='1' if mode == 'lite' else '0',
               REPRO_LITE_OUTPUT=str(destination / 'lite'))
    env.pop('PYTHONPATH', None)
    processes, logs, urls = [], [], []
    selections = [(','.join(map(str, DEVICES)), 19810)] if system == 'epd' else [(str(device), 19800 + i) for i, device in enumerate(DEVICES)]
    try:
        for devices, port in selections:
            log = (destination / 'logs' / f'server-{port}.log').open('w')
            logs.append(log)
            process = subprocess.Popen(['bash', str(ROOT / 'scripts/start_server.sh'), system, devices, str(port)], env=env, stdout=log, stderr=subprocess.STDOUT)
            processes.append(process)
            url = f'http://127.0.0.1:{port}'
            deadline = time.monotonic() + 500
            while True:
                if process.poll() is not None:
                    raise RuntimeError('server exited before readiness')
                try:
                    with urllib.request.urlopen(url + '/repro/rgb-cache', timeout=1):
                        break
                except (urllib.error.URLError, TimeoutError):
                    if time.monotonic() > deadline:
                        raise RuntimeError('server readiness timed out')
                    time.sleep(1)
            urls.append(url)
        subprocess.run([PYTHON, '-B', str(ROOT / 'scripts/check_rgb_cache.py'), '--dataset', str(ROOT / 'dataset'), '--urls', *urls, '--output', str(destination / 'rgb-before.json')], env=env, check=True, timeout=120)
        subprocess.run([PYTHON, '-B', str(ROOT / 'scripts/capture_h20_runtime.py'), str(ROOT), '--output', str(destination / 'runtime.json')], env=env, check=True, timeout=120)
        for index, url in enumerate(urls):
            (destination / f'model-runtime-{index}.json').write_text(json.dumps(post(url, 'runtime'), indent=2))
        yield urls, env, processes
    finally:
        stop(identity)
        for process in processes:
            process.wait(timeout=15)
        for log in logs:
            log.close()
        idle()


def host_snapshot(path):
    """Collect shared-host context outside the benchmark timing window."""
    snapshot = {'utc_ns': time.time_ns(), 'host_ns': time.perf_counter_ns(),
                'load_average': list(os.getloadavg()),
                'meminfo': Path('/proc/meminfo').read_text()}
    for name, fields in [('gpus', 'index,uuid,memory.used,utilization.gpu'),
                         ('compute_processes', 'pid,gpu_uuid,used_memory')]:
        query = '--query-gpu=' if name == 'gpus' else '--query-compute-apps='
        snapshot[name] = subprocess.check_output(
            ['nvidia-smi', query + fields, '--format=csv,noheader,nounits'],
            text=True, timeout=15)
    snapshot['finished_utc_ns'] = time.time_ns()
    with path.open('x') as output:
        json.dump(snapshot, output, indent=2)


def benchmark(destination, row, urls, env, servers):
    host_snapshot(destination / 'host-before.json')
    log = (destination / 'logs/benchmark.log').open('w')
    memory = (destination / 'gpu-memory.jsonl').open('w')
    monitor = subprocess.Popen([PYTHON, '-B', str(ROOT / 'scripts/monitor_gpu.py'), '--devices', ','.join(map(str, DEVICES)), '--server-pids', ','.join(str(process.pid) for process in servers)], env=env, stdout=memory, stderr=subprocess.STDOUT)
    command = [PYTHON, '-B', str(ROOT / 'scripts/benchmark.py'), '--urls', *urls, '--model', str(ROOT / 'models/MiniCPM-V-2_6'), '--dataset', str(ROOT / 'dataset'), '--output', str(destination / 'measurement'), '--images', str(row['images']), '--concurrency', str(row['concurrency']), '--tokens', str(row['tokens']), '--warmup', '20', '--requests', '100', '--repetitions', '1']
    if row['mode'] == 'lite':
        command.append('--lite')
    process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    deadline = time.monotonic() + 900
    try:
        while process.poll() is None:
            if monitor.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('monitor failed or benchmark exceeded fixed cell deadline')
            time.sleep(.2)
        if process.returncode:
            raise RuntimeError('benchmark failed')
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        monitor.terminate()
        monitor.wait(timeout=15)
        log.close()
        memory.close()
        host_snapshot(destination / 'host-after.json')
    raw = [json.loads(line) for line in (destination / 'measurement/requests.jsonl').read_text().splitlines()]
    reference = json.loads((ROOT / 'results/preflight-models/reference.json').read_text())
    reference_name = 'coco8-t128' if row['images'] == 8 else 'coco-' + str(row['images'])
    expected_ids = next(item['response']['processed_prompt_token_ids'] for item in reference['cases'] if item['case']['name'] == reference_name)
    if len(raw) != 120 or any(not item['success'] or item.get('visual_tokens') != row['images'] * 64 or item['response'].get('processed_prompt_token_ids') != expected_ids for item in raw):
        raise RuntimeError('cell inputs differ from frozen new-host reference')
    summary = json.loads((destination / 'measurement/summary.json').read_text())
    if len(summary) != 1 or summary[0]['successes'] != 100:
        raise RuntimeError('incomplete cell')
    subprocess.run([PYTHON, '-B', str(ROOT / 'scripts/check_rgb_cache.py'), '--dataset', str(ROOT / 'dataset'), '--urls', *urls, '--output', str(destination / 'rgb-after.json')], env=env, check=True, timeout=120)
    (destination / 'COMPLETED').write_text(json.dumps(row))


def preflight(code):
    gate('G3_NUMERICAL_APPROVED.json', code)
    destination = ROOT / 'results/preflight-models'
    destination.mkdir(parents=True, exist_ok=False)
    reference = None
    for launch in ('cold', 'restart'):
        for mode in ('off', 'lite'):
            for system in ('baseline-epd', 'epd'):
                folder = destination / f'{launch}-{mode}-{system}'
                with services(system, mode, folder) as (urls, env, servers):
                    if reference is None:
                        reference = asyncio.run(check_suite(urls[0], str(ROOT / 'models/MiniCPM-V-2_6'), ROOT / 'dataset', destination / 'reference.json'))
                    for index, url in enumerate(urls):
                        if mode == 'lite':
                            post(url, 'reset')
                        asyncio.run(check_suite(url, str(ROOT / 'models/MiniCPM-V-2_6'), ROOT / 'dataset', folder / f'correctness-{index}.json', reference))
                        if mode == 'lite':
                            (folder / f'export-{index}.json').write_text(json.dumps(post(url, 'export'), indent=2))
                    subprocess.run([PYTHON, '-B', str(ROOT / 'scripts/check_rgb_cache.py'), '--dataset', str(ROOT / 'dataset'), '--urls', *urls, '--output', str(folder / 'rgb-after.json')], env=env, check=True, timeout=120)
                (folder / 'COMPLETED').write_text('17 cases per endpoint, input/routing/length checked')
    if code_identity() != code:
        raise RuntimeError('code changed during correctness preflight')
    (destination / 'result.json').write_text(json.dumps({'passed': True, 'requires_independent_G3': True, 'code_manifest_sha256': code,
        'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'gpu_uuids': UUIDS, 'target_requests': 272, 'reference_requests': 17}, indent=2))


def main(action):
    with exclusive(action) as code:
        if action == 'preflight':
            preflight(code)
            return
        model_gate = gate('G3_MODELS_APPROVED.json', code)
        if action == 'overhead' and not model_gate.get('lite_observation_approved', False):
            raise RuntimeError('complete lite observation G3 has not passed')
        if action == 'performance':
            scope = gate('C_SCOPE_APPROVED.json', code)
            if scope.get('scope') != 'C-off-only' or scope.get('lite_observation_approved') is not False:
                raise RuntimeError('C-off fallback scope is not explicitly approved')
        schedule_path = ROOT / 'configs' / ('B-schedule.json' if action == 'overhead' else 'C-schedule.json')
        schedule = json.loads(schedule_path.read_text())
        destination = ROOT / 'results' / action
        destination.mkdir(parents=True, exist_ok=False)
        for index, row in enumerate(schedule['rows']):
            folder = destination / f'{index:03d}-b{row["block"]}-{row["load"]}-{row["system"]}-{row["mode"]}'
            print(json.dumps({'starting': str(folder), 'row': row}), flush=True)
            with services(row['system'], row['mode'], folder) as (urls, env, servers):
                benchmark(folder, row, urls, env, servers)
        if code_identity() != code:
            raise RuntimeError('code changed during fixed schedule')
        (destination / 'COMPLETED').write_text(json.dumps({'code_manifest_sha256': code, 'schedule_sha256': sha(schedule_path)}))


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('optimized runner refused')
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('preflight', 'overhead', 'performance'))
    main(parser.parse_args().action)
