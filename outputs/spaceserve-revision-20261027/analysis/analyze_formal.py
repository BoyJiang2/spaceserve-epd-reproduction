"""Read-only whole-schedule analysis. No Gate is granted by this program."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

from audit_cell import audit, ROOT
from block_statistics import paired

FORMAL = 'a1f79489ec38e14b76f2ae53b6ac6ba9e1f9ac14d33dbb397dbcfa05efca92eb'
MODEL = '6782b5a1578c9d890f03bcc2368a36c3ab69663d7479f7b55b5af0c6f03141a5'
NUMERIC = '13a5539d1947c82c468372c193fc12b10eb8ac984513fbb3256e80e751c4795b'
SCHEDULE = '7248d8829180d3df25f04204cd7e1e89b7b7462ea5f39651986f118418c0d8d3'
UUID = 'GPU-79214c80-7778-37d9-282b-89228debbb69'
SM_LIBRARY = '529e2502f633b0d7ef07db2848c64e42154cea73992a794c27a31d0361e5e7c5'
CPU_RECEIPT = '6218df252d938b50d3ac5621bda92424094e8e35013de18c19d4a19f975114d8'
START_RECEIPT = 'db3714e64c3c1371162b3edc73f420567966dd89db67ad40f6dec67ee9500772'
G3_CONSUMER = '6364e303220705f7635dee4630607213b33bf4fa64b20d77d2bd4028bba1f222'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def member(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
        raise ValueError('unsafe evidence path')
    path = root.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError('evidence escaped local batch')
    return path


def verify_rows(root, rows):
    if len({row['path'] for row in rows}) != len(rows):
        raise ValueError('duplicate evidence binding')
    for row in rows:
        path = member(root, row['path'])
        if path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            raise ValueError('bound evidence changed: ' + row['path'])


def verify_consumer(root):
    path = root / 'evidence/G3_MODEL_FORMAL_CONSUMER.json'
    if sha(path) != G3_CONSUMER:
        raise ValueError('approved G3 consumer original changed')
    gate = read(path)
    if (not gate['passed'] or gate['scope'] != 'Space-model-preflight-for-formal'
            or gate['producer_sha256'] != MODEL or gate['formal_data_approved'] is not False
            or gate['gpu_uuids'] != [UUID] or len(gate['bound_files']) != 347):
        raise ValueError('wrong actual model preflight consumer')
    verify_rows(root, gate['bound_files'])
    return gate


def verify_inputs(root):
    for name, expected in [('evidence/formal-target-CPU.json', CPU_RECEIPT),
                           ('evidence/FORMAL_STARTED.json', START_RECEIPT)]:
        if sha(root / name) != expected:
            raise ValueError('actual initial-controller receipt changed: ' + name)
    for name, expected in [('formal-code-manifest.json', FORMAL),
                           ('model-code-manifest-attempt1.json', MODEL),
                           ('numeric-code-manifest-v2.json', NUMERIC)]:
        path = root / 'configs' / name
        if sha(path) != expected:
            raise ValueError('producer manifest changed: ' + name)
        verify_rows(root, read(path))
    # Formal producer15 also binds this original; retain an explicit trust-boundary check.
    gate = verify_consumer(root)
    dataset_rows = [row for row in read(root / 'configs/relocated-inputs.json') if row['path'].startswith('dataset/')]
    if len(dataset_rows) != 26:
        raise ValueError('actual staged dataset inventory differs')
    verify_rows(root, dataset_rows)
    if sha(root / 'configs/schedule-v2.json') != SCHEDULE:
        raise ValueError('schedule differs from frozen 54-cell plan')
    return gate


def device_identity(case, planned):
    folder = case / 'device-records'
    imported = read(folder / 'imports.json')
    workers = [read(path) for path in folder.glob('worker-*.json')]
    role = planned['role']
    expected_prefix = ROOT / ('envs/space/lib/python3.10/site-packages/vllm'
                              if role == 'baseline-space' else 'src/SpaceServe/vllm')
    if (len(workers) != (1 if role == 'baseline-space' else 2)
            or list(folder.glob('sm-stream-*.jsonl')) or imported['profiler_directory']
            or imported['SM_diagnostics'] or imported['role'] != role
            or not PurePosixPath(imported['vllm_file']).is_relative_to(expected_prefix)
            or not PurePosixPath(imported['engine_class_file']).is_relative_to(expected_prefix)):
        raise ValueError('wrong implementation, worker count or diagnostics active')
    expected_options = {'model': str(ROOT / 'models/Qwen2-VL-7B-Instruct'),
                        'dtype': 'float16', 'tensor_parallel_size': 1, 'enforce_eager': True, 'trust_remote_code': True,
                        'seed': 0, 'max_model_len': 4096, 'max_num_seqs': 8,
                        'max_num_batched_tokens': 4096, 'enable_prefix_caching': False,
                        'disable_mm_preprocessor_cache': True, 'gpu_memory_utilization': .65,
                        'limit_mm_per_prompt': {'image': 4},
                        'mm_processor_kwargs': {'min_pixels': 200704, 'max_pixels': 200704}}
    options = read(folder / 'engine-args.json')
    if any(options.get(key) != value for key, value in expected_options.items()):
        raise ValueError('engine options differ across roles or preflight')
    if len({worker['pid'] for worker in workers}) != len(workers):
        raise ValueError('duplicate worker identity')
    for worker in workers:
        encoder = worker['only_vision_encoder']
        components = {'visual': 675759104} if encoder else {'visual': 675759104, 'language_model': 7615616512}
        if (worker['system'] != role or worker['cuda_visible_devices'] != UUID
                or worker['cuda_device_uuid'] != UUID.removeprefix('GPU-')
                or worker['parameters_by_component'] != components
                or worker['parameters_by_device'] != {'cuda:0': sum(components.values())}
                or worker['parameters_by_dtype'] != {'torch.float16': sum(components.values())}
                or worker['mps_pipe'] != str(ROOT / 'tmp/mps')
                or worker['mps_active_thread_percentage'] != '100'):
            raise ValueError('actual worker model/device/precision/MPS differs')
        full_library = {str(ROOT / 'build/libsmctrl.so'): SM_LIBRARY}
        allowed_libraries = [full_library] if role == 'space-mask' and encoder else ([{}, full_library] if role == 'space-mask' else [{}])
        if worker['loaded_smctrl_sha256'] not in allowed_libraries:
            raise ValueError('actual encoder mask library differs')
    if sum(worker['only_vision_encoder'] for worker in workers) != (0 if role == 'baseline-space' else 1):
        raise ValueError('encoder/decoder roles differ')
    return mps_identity(case, {row['pid'] for row in workers})


def mps_identity(case, worker_pids):
    identities = []
    for suffix in ('before', 'after'):
        boundary = read(case / ('mps-' + suffix + '.json'))
        clients, physical = boundary['clients'], boundary['physical_gpu_processes']
        if (not boundary['passed'] or len(clients) != len(worker_pids)
                or {row['pid'] for row in clients} != worker_pids):
            raise ValueError('private MPS boundary client set differs')
        servers = {row['server_pid'] for row in clients}
        if (len(servers) != 1 or any(type(pid) is not int or pid <= 0 for pid in servers | worker_pids)
                or servers & worker_pids
                or any(row['device_partial_uuid'] != 'GPU-79214c80-7778-37d9' for row in clients)):
            raise ValueError('MPS server or client GPU identity differs')
        server = next(iter(servers))
        allowed = worker_pids | servers
        if (len(physical) != len(allowed) or {row['pid'] for row in physical} != allowed
                or any(row['uuid'] != UUID or row['private_mps_server'] is not (row['pid'] == server) for row in physical)):
            raise ValueError('MPS physical GPU process identity differs')
        identities.append(allowed)
    if identities[0] != identities[1]:
        raise ValueError('MPS server changed across measurement')
    return identities[0]


def memory_peak(samples, start, end, allowed_pids):
    peaks = []
    for sample in samples:
        if not start <= sample['perf_counter'] <= end:
            continue
        if len(sample['gpus']) != 1 or sample['gpus'][0]['device'] != 4 or sample['gpus'][0]['foreign_compute_pids']:
            raise ValueError('wrong target GPU or foreign memory process')
        gpu = sample['gpus'][0]
        processes = gpu['owned_processes']
        pids = [row['pid'] for row in processes]
        physical = gpu['physical_used_bytes']
        if (len(set(pids)) != len(pids) or not pids or not set(pids) <= allowed_pids
                or any(type(pid) is not int or pid <= 0 for pid in pids)
                or type(physical) is not int or physical < 0
                or any(type(row['used_bytes']) is not int or not 0 <= row['used_bytes'] <= physical for row in processes)
                or type(gpu['owned_process_sum_bytes']) is not int
                or gpu['owned_process_sum_bytes'] != sum(row['used_bytes'] for row in processes)):
            raise ValueError('GPU memory samples do not belong to this cell or contain invalid bytes')
        peaks.append(gpu['owned_process_sum_bytes'])
    if not peaks:
        raise ValueError('no attributed memory samples in formal window')
    # MPS process sums may include shared allocations; this is not physical capacity usage.
    return max(peaks)


def rgb_identity(case, root, api_pid):
    reference = read(root / 'results/preflight-models-attempt1/cold-baseline-space/rgb-before.json')['records'][0]
    manifest = sha(root / 'dataset/manifest.json')
    if reference['manifest_sha256'] != manifest or len(reference['images']) != 20:
        raise ValueError('RGB reference differs from actual staged manifest')
    for suffix in ('before', 'after'):
        snapshot = read(case / ('rgb-' + suffix + '.json'))
        if not snapshot['passed'] or snapshot['inference_requests'] != 0 or len(snapshot['records']) != 1:
            raise ValueError('RGB boundary missing or generated extra inference requests')
        record = snapshot['records'][0]
        if (record['pid'] != api_pid or record['url'] != 'http://127.0.0.1:19770'
                or record['manifest_sha256'] != manifest or record['images'] != reference['images']):
            raise ValueError('RGB cached images or boundary API identity differ')


def describe(case, planned, root):
    marker = read(case / 'COMPLETED.json')
    if marker != {'formal_code_manifest_sha256': FORMAL, 'schedule_index': planned['index'],
                  'formal_requests': 100, 'warmup_requests': 20}:
        raise ValueError('cell completion identity differs')
    check = audit(case, planned, root)
    allowed_pids = device_identity(case, planned)
    launch = read(case / 'launch.json')
    runtime = read(case / 'runtime.json')
    if (len(runtime['servers']) != 1 or runtime['devices'] != '4'
            or runtime['servers'][0]['pid'] != launch['api_pid']
            or runtime['servers'][0]['created_epoch_seconds'] != launch['api_created']
            or not launch['run_id'].startswith(str(ROOT) + ':service:')
            or runtime['packages'] != {'vllm': '0.7.2', 'torch': '2.5.1', 'transformers': '4.49.0'}):
        raise ValueError('runtime service identity or dependencies differ')
    rgb_identity(case, root, launch['api_pid'])
    summary = read(case / 'measurement/summary.json')[0]
    before, after = read(case / 'host-before.json'), read(case / 'host-after.json')
    start, end = summary['start_perf_counter'], summary['end_perf_counter']
    if not before['host_ns'] <= before['finished_host_ns'] <= start * 1e9 <= end * 1e9 <= after['host_ns'] <= after['finished_host_ns']:
        raise ValueError('host snapshots overlap or fail to surround formal window')
    if not before['utc_ns'] <= before['finished_utc_ns'] <= after['utc_ns'] <= after['finished_utc_ns']:
        raise ValueError('invalid host wall-clock chronology')
    samples = [json.loads(line) for line in (case / 'gpu-memory.jsonl').read_text().splitlines()]
    peak = memory_peak(samples, start, end, allowed_pids)
    if not math.isfinite(peak) or peak < 0:
        raise ValueError('invalid sampled attributed GPU memory')
    return {'technical_audit': check, 'metrics': summary, 'sampled_peak_bytes': peak,
            'service_identity': launch['run_id'], 'api_identity': [launch['api_pid'], launch['api_created']],
            'start': start, 'end': end, 'host_before_utc_ns': before['utc_ns'],
            'host_after_utc_ns': after['finished_utc_ns']}


def comparisons(cells, complete, global_errors):
    lookup = {(row['block'], row['images'], row['concurrency'], row['role']): row for row in cells}
    pairs = []
    intervals = []
    for images in (1, 4):
        for concurrency in (1, 4, 8):
            for role, baseline_role in (('space', 'baseline-space'), ('space-mask', 'baseline-space'), ('space-mask', 'space')):
                values, baseline = {}, {}
                for block in range(3):
                    a = lookup[(block, images, concurrency, role)]
                    b = lookup[(block, images, concurrency, baseline_role)]
                    valid = a['status'] == b['status'] == 'valid' and not global_errors
                    pairs.append({'block': block, 'images': images, 'concurrency': concurrency,
                                  'role': role, 'baseline_role': baseline_role,
                                  'target_status': a['status'], 'baseline_status': b['status'],
                                  'throughput_ratio': a['metrics']['requests_per_s'] / b['metrics']['requests_per_s'] if valid else None})
                    if valid:
                        values[block] = a['metrics']['requests_per_s']
                        baseline[block] = b['metrics']['requests_per_s']
                if complete and not global_errors:
                    intervals.append({'images': images, 'concurrency': concurrency, 'role': role, 'baseline_role': baseline_role,
                                      'throughput': paired(values, baseline),
                                      'metrics': {metric: paired(
                                          {block: run_metrics(lookup[(block, images, concurrency, role)])[metric] for block in range(3)},
                                          {block: run_metrics(lookup[(block, images, concurrency, baseline_role)])[metric] for block in range(3)})
                                          for metric in run_metrics(lookup[(0, images, concurrency, role)])}})
    return pairs, intervals


def run_metrics(cell):
    summary = cell['metrics']
    values = {'requests_per_s': summary['requests_per_s'],
              'output_tokens_per_s': summary['output_tokens_per_s'],
              'sampled_peak_bytes': cell['sampled_peak_bytes']}
    values.update({metric + '_' + quantile: summary[metric][quantile]
                   for metric in ('latency_s', 'ttft_s', 'tpot_s') for quantile in ('p50', 'p95')})
    return values


def raw_inventory(case):
    path = case / 'measurement/requests.jsonl'
    if not path.exists():
        return None
    try:
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        return {'rows': len(rows), 'formal_rows': sum(row.get('warmup') is False for row in rows),
                'warmup_rows': sum(row.get('warmup') is True for row in rows),
                'recorded_failures': sum(row.get('success') is False for row in rows)}
    except (ValueError, OSError, AttributeError) as error:
        return {'unreadable': str(error)}


def analyze(root):
    verify_inputs(root)
    schedule = read(root / 'configs/schedule-v2.json')['cells']
    cells, errors = [], []
    names = {f'{row["index"]:03d}-b{row["block"]}-i{row["images"]}-c{row["concurrency"]}-{row["role"]}' for row in schedule}
    formal = root / 'results/formal'
    if formal.exists() and any(path.is_dir() and path.name not in names for path in formal.iterdir()):
        errors.append('unexpected cell directory; no ratios or intervals permitted')
    previous = None
    previous_utc = None
    services, apis = set(), set()
    booking = read(root / 'evidence/formal-final-booking-state.json')['booking']
    if (booking['resource_id'] != 'h20/qjh000' or booking['node'] != 'qjh000'
            or booking['user'] != 'boyjiang' or booking['kind'] != 'gpu'
            or booking['start_ms'] != 1793019600000 or booking['end_ms'] > 1793062800000):
        errors.append('booking owner, lane or authorized overnight window differs')
    for planned in schedule:
        case = formal / f'{planned["index"]:03d}-b{planned["block"]}-i{planned["images"]}-c{planned["concurrency"]}-{planned["role"]}'
        row = {**planned, 'status': 'missing', 'raw_inventory': raw_inventory(case)}
        if case.exists():
            try:
                row.update(describe(case, planned, root))
                row['status'] = 'valid'
                if (row['host_before_utc_ns'] < booking['start_ms'] * 1000000
                        or row['host_after_utc_ns'] > (booking['end_ms'] - 120000) * 1000000):
                    errors.append('cell boundary outside actual booking or cleanup reserve')
                if previous is not None and row['start'] <= previous:
                    errors.append('formal windows out of frozen order or overlapping')
                if previous_utc is not None and row['host_before_utc_ns'] <= previous_utc:
                    errors.append('host wall-clock windows out of frozen order')
                if row['service_identity'] in services or tuple(row['api_identity']) in apis:
                    errors.append('service identity reused across fresh cells')
                services.add(row['service_identity'])
                apis.add(tuple(row['api_identity']))
                previous = row['end']
                previous_utc = row['host_after_utc_ns']
            except (OSError, ValueError, KeyError, TypeError, StopIteration, RuntimeError) as error:
                row.update(status='invalid_or_partial', error=str(error))
        cells.append(row)
    exit_path = root / 'evidence/formal-exit.json'
    terminal = read(exit_path) if exit_path.exists() else None
    started = read(root / 'evidence/FORMAL_STARTED.json')
    if terminal and any(terminal.get(key) != started[key] for key in ('controller_id', 'pid', 'process_created', 'started_unix')):
        errors.append('terminal receipt belongs to a different controller')
    complete = all(row['status'] == 'valid' for row in cells) and not errors and terminal is not None and terminal.get('exit_code') == 0
    marker = formal / 'COMPLETED.json'
    if complete and (not marker.exists() or read(marker) != {'formal_code_manifest_sha256': FORMAL, 'schedule_sha256': SCHEDULE, 'formal_requests': 5400, 'warmup_requests': 1080}):
        errors.append('missing or wrong whole-matrix completion marker')
        complete = False
    pairs, intervals = comparisons(cells, complete, errors)
    sources = {path.relative_to(root).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path)}
               for path in formal.rglob('*') if path.is_file()} if formal.exists() else {}
    inputs = {name: sha(root / name) for name in ('evidence/formal-target-CPU.json',
              'evidence/FORMAL_STARTED.json', 'evidence/formal-final-booking-state.json',
              'evidence/formal-terminal.json', 'evidence/formal-final-mps-owner.json', 'evidence/formal-files.json',
              'evidence/formal-exit.json', 'evidence/formal-controller.log', 'evidence/formal-launcher-stdout.log',
              'evidence/G3_MODEL_FORMAL_CONSUMER.json', 'configs/schedule-v2.json',
              'dataset/manifest.json', 'evidence/MODEL_INPUTS_VERIFIED-attempt1.json',
              'results/preflight-models-attempt1/reference.json') if (root / name).exists()}
    return {'candidate_only': True, 'grants_no_gate': True, 'complete': complete,
            'valid_cells': sum(row['status'] == 'valid' for row in cells), 'planned_cells': 54,
            'cells': cells, 'all_planned_pairs': pairs, 'intervals': intervals,
            'global_errors': errors, 'terminal_controller': terminal, 'raw_sources': sources, 'input_sources': inputs,
            'limits': ['Shared host; boundary snapshots cannot exclude transient interference.',
                       'Encoder-stream mask only; no decoder mutual exclusion or GPU-share claim.',
                       'Pixel kwargs ignored by vLLM; actual inputs 448x448 and 256 visual tokens/image.',
                       'Decoder retains visual and language parameters plus a separate visual encoder.',
                       'No diagnostic trace is interpreted as the formal off critical path.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.root)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2, allow_nan=False)
