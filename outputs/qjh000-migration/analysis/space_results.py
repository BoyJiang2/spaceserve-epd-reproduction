"""Audit and summarize the fixed single-H20 SpaceServe experiment, phase by phase."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import platform
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_formal_case import audit

GPU = 'GPU-d1b595ce-0b57-cdee-c1c0-9b1051aaa07e'
REMOTE = '/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023'
LIBRARY = REMOTE + '/build/libsmctrl.so'
LIB_SHA = '529e2502f633b0d7ef07db2848c64e42154cea73992a794c27a31d0361e5e7c5'
PACKAGES = {'vllm': '0.7.2', 'torch': '2.5.1', 'transformers': '4.49.0'}


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1024**2):
            value.update(block)
    return value.hexdigest()


def stats(values):
    values = sorted(values)
    if not values or any(not math.isfinite(value) for value in values):
        raise RuntimeError('empty or nonfinite metric')
    result = {'n': len(values), 'mean': statistics.mean(values), 'sd': statistics.stdev(values) if len(values) > 1 else 0}
    for name, fraction in [('p50', .5), ('p95', .95)]:
        position = (len(values) - 1) * fraction
        low = int(position)
        result[name] = values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (position - low)
    return result


def validate_points_manifest(folder, phase):
    outer = (folder / 'points-manifest.sha256').read_bytes()
    expected, filename = outer.decode().strip().split('  ', 1)
    inner = folder / 'points.sha256'
    if filename != REMOTE + '/results/formal/points.sha256' or digest(inner) != expected:
        raise RuntimeError('points manifest differs from the frozen outer digest')
    if phase == 'all' and (folder / 'G4_POINTS_APPROVED').read_bytes() != outer:
        raise RuntimeError('full matrix lacks matching G4 points approval')
    count = 0
    for line in inner.read_text().splitlines():
        expected, filename = line.split('  ', 1)
        relative = PurePosixPath(filename).relative_to(REMOTE + '/results/formal')
        if relative.parts[0] != 'points' or '..' in relative.parts or digest(folder.joinpath(*relative.parts)) != expected:
            raise RuntimeError('frozen point payload differs')
        count += 1
    if count == 0:
        raise RuntimeError('empty points manifest')
    return {'outer_sha256': digest(folder / 'points-manifest.sha256'), 'inner_sha256': digest(inner), 'bound_files': count}


def validate_role(folder, role):
    if not (folder / 'COMPLETED').is_file():
        raise RuntimeError('role incomplete')
    runtime = json.loads((folder / 'runtime.json').read_text())
    if runtime['packages'] != PACKAGES or runtime['devices'] != '0' or len(runtime['servers']) != 1:
        raise RuntimeError('runtime package or device budget mismatch')
    env = runtime['servers'][0]['environment']
    expected_library = LIBRARY if role == 'space-mask' else None
    if env['CUDA_VISIBLE_DEVICES'] != GPU or env['CUDA_MPS_PIPE_DIRECTORY'] != REMOTE + '/tmp/mps' or env['VLLM_USE_V1'] != '1' or env['VLLM_LIBSMCTRL_PATH'] != expected_library:
        raise RuntimeError('actual server GPU/MPS/library identity differs')
    records = [json.loads(path.read_text()) for path in (folder / 'device-records').glob('worker-*.json')]
    expected_count = 1 if role == 'baseline-space' else 2
    if len(records) != expected_count or len({row['pid'] for row in records}) != expected_count:
        raise RuntimeError('actual worker count differs')
    if sum(row['only_vision_encoder'] for row in records) != expected_count - 1:
        raise RuntimeError('actual encoder/LM placement differs')
    for row in records:
        libraries = {LIBRARY: LIB_SHA} if role == 'space-mask' else {}
        if set(row['parameters_by_device']) != {'cuda:0'} or set(row['parameters_by_dtype']) != {'torch.float16'} or row['cuda_visible_devices'] != GPU or row['loaded_smctrl_sha256'] != libraries:
            raise RuntimeError('loaded model dtype/GPU/library differs')
        components = {'visual': 675759104} if row['only_vision_encoder'] else {'visual': 675759104, 'language_model': 7615616512}
        count = sum(components.values())
        if row['parameters_by_component'] != components or row['parameters_by_device']['cuda:0'] != count or row['parameters_by_dtype']['torch.float16'] != count:
            raise RuntimeError('actual encoder/LM parameter components differ')
        if row['mps_pipe'] != REMOTE + '/tmp/mps' or row['mps_active_thread_percentage'] != '100' or row['logical_device'] != 'cuda:0' or row['cuda_device_uuid'].removeprefix('GPU-') != GPU.removeprefix('GPU-'):
            raise RuntimeError('actual worker MPS/physical GPU identity differs')
    boundary = json.loads((folder / 'mps-identity.json').read_text())
    worker_pids = {row['pid'] for row in records}
    physical = boundary['physical_gpu_processes']
    physical_pids = {row['pid'] for row in physical}
    private_servers = {row['pid'] for row in physical if row['private_mps_server']}
    client_servers = {row['server_pid'] for row in boundary['clients']}
    api_pid = runtime['servers'][0]['pid']
    if not boundary['passed'] or worker_pids != {row['pid'] for row in boundary['clients']} or len(boundary['clients']) != expected_count or not physical or len(physical_pids) != len(physical) or len(private_servers) != 1 or private_servers != client_servers or not worker_pids <= physical_pids <= worker_pids | private_servers | {api_pid} or any(row['uuid'] != GPU for row in physical):
        raise RuntimeError('worker/MPS/NVML boundary mismatch')
    if any(not row['device_partial_uuid'].startswith('GPU-') or not GPU.startswith(row['device_partial_uuid']) for row in boundary['clients']):
        raise RuntimeError('MPS client physical GPU differs')
    command = runtime['servers'][0]['command']
    if '--port' not in command or command[command.index('--port') + 1] != '19770':
        raise RuntimeError('actual API port differs')
    options = json.loads((folder / 'device-records/engine-args.json').read_text())
    required = {'model': REMOTE + '/models/Qwen2-VL-7B-Instruct', 'dtype': 'float16', 'tensor_parallel_size': 1,
                'enforce_eager': True, 'max_model_len': 4096, 'max_num_seqs': 8, 'max_num_batched_tokens': 4096,
                'enable_prefix_caching': False, 'disable_mm_preprocessor_cache': True, 'gpu_memory_utilization': .65,
                'limit_mm_per_prompt': {'image': 4}, 'mm_processor_kwargs': {'min_pixels': 200704, 'max_pixels': 200704}}
    if any(options.get(key) != value for key, value in required.items()):
        raise RuntimeError('actual engine options differ from the fixed protocol')
    return {'model_parameters': [{'pid': row['pid'], 'class': row['model_class'], 'components': row['parameters_by_component']} for row in records],
            'engine_args': options, 'mps_server_pids': sorted({row['server_pid'] for row in boundary['clients']}),
            'api_pid': api_pid, 'api_url': 'http://127.0.0.1:19770',
            'allowed_gpu_pids': sorted(worker_pids | private_servers | {api_pid}), 'required_gpu_pids': sorted(physical_pids)}


def validate_memory(samples, identity, capacity):
    if not samples:
        raise RuntimeError('memory samples missing')
    previous = -math.inf
    for sample in samples:
        stamp = sample['perf_counter']
        if not math.isfinite(stamp) or stamp <= previous:
            raise RuntimeError('memory sample time is not strictly increasing')
        previous = stamp
        if len(sample['gpus']) != 1 or sample['gpus'][0]['device'] != 0:
            raise RuntimeError('memory must sample exactly GPU0')
        gpu = sample['gpus'][0]
        processes = gpu['owned_processes']
        pids = [row['pid'] for row in processes]
        if any(not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 for pid in pids) or len(set(pids)) != len(pids) or not set(identity['required_gpu_pids']) <= set(pids) <= set(identity['allowed_gpu_pids']) or gpu['foreign_compute_pids']:
            raise RuntimeError('memory PID identity differs from actual worker/MPS boundary')
        values = [row.get('used_bytes') for row in processes] + [gpu.get('owned_process_sum_bytes'), gpu.get('physical_used_bytes')]
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
            raise RuntimeError('invalid process memory bytes')
        if sum(row['used_bytes'] for row in processes) != gpu['owned_process_sum_bytes'] or not 0 <= gpu['owned_process_sum_bytes'] <= gpu['physical_used_bytes'] <= capacity:
            raise RuntimeError('memory byte sum or physical capacity differs')


def collect(folder, role, images, concurrency, identity, capacity):
    if not (folder / 'COMPLETED').is_file():
        raise RuntimeError('case incomplete: ' + str(folder))
    checked = audit(folder)
    rows = [json.loads(line) for line in (folder / 'measurement/requests.jsonl').read_text().splitlines()]
    config = json.loads((folder / 'measurement/config.json').read_text())
    summaries = json.loads((folder / 'measurement/summary.json').read_text())
    if (config['images'], config['concurrency']) != (images, concurrency):
        raise RuntimeError('directory/config load differs')
    rgb = [json.loads((folder / ('rgb-' + when + '.json')).read_text()) for when in ['before', 'after']]
    if not all(value['passed'] and len(value['records']) == 1 and value['records'][0]['pid'] == identity['api_pid'] for value in rgb) or rgb[0]['records'][0]['images'] != rgb[1]['records'][0]['images'] or len(rgb[0]['records'][0]['images']) != 20:
        raise RuntimeError('RGB inputs changed')
    if config['urls'] != [identity['api_url']] or any(value['records'][0]['url'] != identity['api_url'] for value in rgb) or any(row['endpoint'] != identity['api_url'] for row in rows):
        raise RuntimeError('request/config/RGB endpoint differs from actual API')
    formal = [row for row in rows if not row['warmup']]
    bookkeeping = []
    peaks = []
    memory = [json.loads(line) for line in (folder / 'gpu-memory.jsonl').read_text().splitlines()]
    validate_memory(memory, identity, capacity)
    for repetition, summary in enumerate(summaries):
        group = [row for row in formal if row['repetition'] == repetition]
        begin, end = summary['start_perf_counter'], summary['end_perf_counter']
        first = min(row['submission_perf_counter'] for row in group)
        last = max(row['submission_perf_counter'] + row['latency_s'] for row in group)
        if first < begin - 1e-8 or last > end + 1e-8 or first - begin > 1 or end - last > 1:
            raise RuntimeError('requests/repetition timing window differs')
        bookkeeping.append({'repetition': repetition, 'leading_schedule_s': first - begin, 'trailing_io_s': end - last})
        samples = [gpu for sample in memory if begin <= sample['perf_counter'] <= end for gpu in sample['gpus']]
        if any(gpu['device'] != 0 for gpu in samples):
            raise RuntimeError('memory sampled a different GPU')
        peaks.append(max(gpu['owned_process_sum_bytes'] for gpu in samples) / 1024**3)
    indexed = {(row['warmup'], row['repetition'], row['index']): row for row in rows}
    if len(indexed) != 320:
        raise RuntimeError('request keys not unique')
    record = {'role': role, 'images': images, 'concurrency': concurrency, 'formal_requests': 300, 'warmup_requests': 20,
              'failure_rate': 0, 'requests_per_s': stats([item['requests_per_s'] for item in summaries]),
              'output_tokens_per_s': stats([item['output_tokens_per_s'] for item in summaries]),
              'metrics_ms': {name: stats([row[field] * 1000 for row in formal]) for name, field in [('ttft', 'ttft_s'), ('tpot', 'tpot_s'), ('e2e', 'latency_s')]},
              'per_repetition': summaries, 'sampled_owned_peak_gib': max(peaks), 'sampled_peak_gib_by_repetition': peaks,
              'memory_coverage': checked['memory_coverage'], 'bookkeeping': bookkeeping,
              'request_source_sha256': digest(folder / 'measurement/requests.jsonl'),
              'rgb_manifest_sha256': rgb[0]['records'][0]['manifest_sha256']}
    return record, indexed, config, rgb[0]['records'][0]['images']


def run(root, phase, output):
    formal_root = root / 'results/formal'
    frozen_points = validate_points_manifest(formal_root, phase)
    capacity = json.loads((root / 'evidence/gpu-memory-capacity.json').read_text())
    if capacity['host'] != 'qjh000' or capacity['gpu_uuid'] != GPU or capacity['device'] != 0 or capacity['boot_id'] != 'a9617eaa-1638-45fc-8997-a62b528e8f30' or capacity['total_bytes'] <= 0:
        raise RuntimeError('physical memory capacity source differs')
    roles = (formal_root / 'points/roles.txt').read_text().splitlines()
    if roles not in [['baseline-space', 'space'], ['baseline-space', 'space', 'space-mask']]:
        raise RuntimeError('unexpected accepted role set')
    mps = json.loads((formal_root / 'mps-start.json').read_text())
    if mps['state'] != 'running' or mps['uuid'] != GPU or mps['active_thread_percentage'] != 100:
        raise RuntimeError('formal private MPS budget differs')
    cases, identities, comparisons, data = [], [], [], {}
    expected_options, expected_rgb, expected_mps_server = None, None, None
    expected_configs = {}
    phases = ['points'] if phase == 'points' else ['points', 'rest']
    for current in phases:
        loads = [(1, 1), (4, 8)] if current == 'points' else [(1, 4), (1, 8), (4, 1), (4, 4)]
        for role in roles:
            folder = formal_root / current / role
            identity = validate_role(folder, role)
            if expected_options is None:
                expected_options = identity['engine_args']
            if identity['engine_args'] != expected_options:
                raise RuntimeError('actual engine options differ across groups/phases')
            if expected_mps_server is None:
                expected_mps_server = identity['mps_server_pids']
            if len(identity['mps_server_pids']) != 1 or identity['mps_server_pids'] != expected_mps_server:
                raise RuntimeError('private MPS server differs across groups/phases')
            identities.append({'phase': current, 'role': role, **identity})
            for images, concurrency in loads:
                case, rows, config, rgb = collect(folder / f'images{images}-c{concurrency}', role, images, concurrency, identity, capacity['total_bytes'])
                comparable_config = {key: value for key, value in config.items() if key != 'output'}
                load = (images, concurrency)
                if load not in expected_configs:
                    expected_configs[load] = comparable_config
                if comparable_config != expected_configs[load]:
                    raise RuntimeError('benchmark request protocol differs between groups')
                if expected_rgb is None:
                    expected_rgb = rgb
                if rgb != expected_rgb:
                    raise RuntimeError('RGB differs between groups')
                cases.append(case)
                data[(role, images, concurrency)] = rows
    for experiment in roles[1:]:
        for baseline in [row for row in cases if row['role'] == 'baseline-space']:
            images, concurrency = baseline['images'], baseline['concurrency']
            tested = next(row for row in cases if (row['role'], row['images'], row['concurrency']) == (experiment, images, concurrency))
            left, right = data[('baseline-space', images, concurrency)], data[(experiment, images, concurrency)]
            input_diffs, output_diffs = [], []
            for key in left:
                a, b = left[key], right[key]
                if a['images'] != b['images'] or a['response']['processed_prompt_token_ids'] != b['response']['processed_prompt_token_ids']:
                    input_diffs.append(list(key))
                if a['response']['output_token_ids'] != b['response']['output_token_ids']:
                    output_diffs.append(list(key))
            if input_diffs:
                raise RuntimeError('input sequence differs between groups')
            comparisons.append({'experiment': experiment, 'images': images, 'concurrency': concurrency,
                'request_throughput_ratio': tested['requests_per_s']['mean'] / baseline['requests_per_s']['mean'],
                'compared_requests_including_warmup': 320, 'input_differences': input_diffs, 'output_token_differences': output_diffs})
    result = {'passed': True, 'phase': phase, 'measurement_host': 'qjh000', 'analysis_host': platform.node(),
              'model': 'Qwen/Qwen2-VL-7B-Instruct', 'gpu_uuid': GPU, 'roles': roles,
              'formal_requests': len(cases) * 300, 'warmup_requests': len(cases) * 20, 'cases': cases,
              'identities': identities, 'comparisons': comparisons, 'analysis_code_sha256': digest(Path(__file__)),
              'frozen_points': frozen_points, 'physical_memory_capacity': capacity,
              'audit_dependency_sha256': digest(Path(__file__).resolve().parents[1] / 'scripts/audit_formal_case.py'),
              'limitations': ['Fixed-concurrency measurements; no arrival-rate SLO claim.',
                'Latency percentiles pool300 requests; throughput mean/SD uses three measured repetition windows.',
                'All-process memory is a sampled sum, not an exact instantaneous peak.',
                'Fork LM still retains visual weights; parameter components and aggregate memory are reported.',
                'SM restriction applies to encoder stream only; no mutual decoder partition or full paper SIS claim.',
                'Boundary MPS identities do not exclude every transient process; within-run GPU sampling is also audited.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'phase': phase, 'formal_requests': result['formal_requests'], 'roles': roles}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--phase', choices=['points', 'all'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.root.resolve(), args.phase, args.output.resolve())
