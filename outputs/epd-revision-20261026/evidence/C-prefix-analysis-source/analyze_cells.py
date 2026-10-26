"""Audit fixed B/C cells before computing six-block intervals; never grants a gate."""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path

from block_statistics import contrast, equivalent, paired

HOST_ROOT = '/var/tmp/boyjiang-epd-revision-20261026'
CODE_SHA256 = '9bb1a92b9864bb9ccd837a9258d7079f0dc98d559ab305c906d4bed6d27d4bbd'
LOADS = {'A': (1, 128, 1), 'B': (4, 128, 8), 'C': (1, 128, 8),
         'D': (8, 128, 8), 'E': (8, 32, 8)}
METRICS = ('latency_s', 'ttft_s', 'tpot_s')
DEVICES = (4, 5, 6)  # Physical indices; each CUDA-visible service still uses logical 0..2.
UUIDS = ['GPU-79214c80-7778-37d9-282b-89228debbb69', 'GPU-c883a2aa-a00c-c302-c3ad-12421ef80a71', 'GPU-5123aa0b-e69a-7246-26f1-446b3469f2eb']
# Frozen before any new measurements: sampler target is 0.1s; larger gaps are incomplete evidence.
MAX_SAMPLE_GAP_S = 2.0
MAX_SAMPLE_EDGE_S = 1.0


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values) - 1) * fraction
    low = int(position)
    return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (position - low)


def close(actual, expected):
    if not isinstance(actual, (int, float)) or not math.isfinite(actual) or not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError(f'metric differs: {actual!r} vs {expected!r}')


def validate_schedule(rows, phase):
    loads = {'low': (1, 128, 1), 'high': (4, 128, 8)} if phase == 'overhead' else LOADS
    modes = ('off', 'lite') if phase == 'overhead' else ('off',)
    expected = {(block, load, system, mode) for block in range(6) for load in loads
                for system in ('epd', 'baseline-epd') for mode in modes}
    keys = [(r['block'], r['load'], r['system'], r['mode']) for r in rows]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError('schedule has missing/duplicate/unknown block cells')
    for row in rows:
        if (row['images'], row['tokens'], row['concurrency']) != loads[row['load']] or row['warmup'] != 20 or row['formal'] != 100:
            raise ValueError('schedule differs from frozen protocol')


def audit_runtime(folder, endpoints, read):
    runtime = read(folder / 'runtime.json')
    if not runtime['boot_id'] or runtime['python_prefix'] != HOST_ROOT + '/envs/epd':
        raise ValueError('runtime boot/environment missing or wrong')
    workers = runtime['workers']
    if len(workers) != 3 or {w['gpu_uuid'] for w in workers} != set(UUIDS) or len({w['pid'] for w in workers}) != 3:
        raise ValueError('runtime worker/GPU budget mismatch')
    if not runtime['loaded_cublas_sha256'] or any(not p.startswith(HOST_ROOT + '/') or len(h) != 64 for p, h in runtime['loaded_cublas_sha256'].items()):
        raise ValueError('unbound actual cuBLAS libraries')
    captured = datetime.datetime.fromisoformat(runtime['captured_utc'])
    if captured.tzinfo is None:
        raise ValueError('runtime capture time lacks timezone')
    model_pids = []
    api_pids = []
    for index in range(len(endpoints)):
        model = read(folder / f'model-runtime-{index}.json')
        if model['operation'] != 'runtime' or not model['results']:
            raise ValueError('model placement evidence missing')
        api_pids.append(model['pid'])
        for item in model['results']:
            if not item['parameters_by_device'] or not item['parameters_by_dtype'] or not item['parameters_by_component']:
                raise ValueError('model placement metadata empty')
            model_pids.append(item['pid'])
    worker_pids = {w['pid'] for w in workers}
    if len(model_pids) != 3 or set(model_pids) != worker_pids:
        raise ValueError('model placement does not match actual GPU workers')
    rgb = [read(folder / f'rgb-{when}.json') for when in ('before', 'after')]
    for report in rgb:
        if report.get('passed') is not True or report['inference_requests'] != 0 or len(report['records']) != len(endpoints):
            raise ValueError('RGB cache verification missing/failed')
        for index, record in enumerate(report['records']):
            if record['url'] != endpoints[index] or record['pid'] != api_pids[index] or len(record['images']) != 20:
                raise ValueError('RGB endpoint/image identity mismatch')
            if record['images'] != report['records'][0]['images'] or record['manifest_sha256'] != report['records'][0]['manifest_sha256']:
                raise ValueError('RGB contents differ across replicas')
    if rgb[0]['records'] != rgb[1]['records']:
        raise ValueError('RGB cache changed across measurement')
    return runtime, worker_pids, api_pids, rgb[0]['records']


def audit_lite(folder, endpoints, workers, api_pids, warmup_end, start, end, read):
    controls = read(folder / 'measurement/capture-control.json')
    expected = [(op, url) for op in ('reset', 'export') for url in endpoints]
    if [(c['operation'], c['endpoint']) for c in controls] != expected:
        raise ValueError('lite reset/export endpoint coverage missing')
    exports = {}
    run_ids = set()
    for control in controls:
        if not math.isfinite(control['start']) or not math.isfinite(control['end']) or control['start'] > control['end']:
            raise ValueError('invalid lite control clock')
        if (control['operation'] == 'reset' and (control['start'] < warmup_end or control['end'] > start)) or (control['operation'] == 'export' and control['start'] < end):
            raise ValueError('lite control overlaps formal measurement')
        state = control['state']
        if state['operation'] != control['operation'] or state['pid'] != api_pids[endpoints.index(control['endpoint'])]:
            raise ValueError('lite control process identity mismatch')
        if control['operation'] != 'export':
            continue
        for item in state['results']:
            pid = item['pid']
            expected_path = f'{HOST_ROOT}/results/{folder.parent.name}/{folder.name}/lite/process-{pid}.json'
            if item.get('overflow') is not False or item['path'] != expected_path or pid in exports:
                raise ValueError('lite overflow/duplicate/export path mismatch')
            payload = read(folder / 'lite' / f'process-{pid}.json')
            if payload['pid'] != pid or payload.get('overflow') is not False or len(payload['events']) != item['events'] or len(payload['gpu_stream_windows']) != item['gpu_windows']:
                raise ValueError('lite export count/identity mismatch')
            if pid in workers and not payload['gpu_stream_windows']:
                raise ValueError('GPU worker has no exported stream windows')
            exports[pid] = payload
            run_ids.add(payload['run_id'])
    if set(exports) != workers | set(api_pids) or len(run_ids) != 1 or not next(iter(run_ids)).startswith(HOST_ROOT + ':' + folder.name + ':'):
        raise ValueError('lite process/run coverage mismatch')


def audit_host_snapshots(folder, start, end, read):
    snapshots = {when: read(folder / f'host-{when}.json') for when in ('before', 'after')}
    for when, state in snapshots.items():
        if (not all(type(state[key]) is int and state[key] > 0 for key in ('host_ns', 'utc_ns', 'finished_utc_ns'))
                or state['finished_utc_ns'] < state['utc_ns']):
            raise ValueError('invalid shared-host snapshot timestamps')
        if len(state['load_average']) != 3 or any(not math.isfinite(x) or x < 0 for x in state['load_average']):
            raise ValueError('invalid shared-host load context')
        if not isinstance(state['compute_processes'], str):
            raise ValueError('missing shared-host compute context')
        memory = dict(line.split(':', 1) for line in state['meminfo'].splitlines())
        if not {'MemAvailable', 'SwapTotal', 'SwapFree'} <= memory.keys():
            raise ValueError('missing shared-host available memory/swap context')
        gpus = [[value.strip() for value in line.split(',')] for line in state['gpus'].splitlines()]
        if len(gpus) != 8 or any(len(gpu) != 4 for gpu in gpus) or {int(gpu[0]) for gpu in gpus} != set(range(8)):
            raise ValueError('incomplete shared-host GPU context')
        if any(next(gpu[1] for gpu in gpus if int(gpu[0]) == device) != expected for device, expected in zip(DEVICES, UUIDS)):
            raise ValueError('shared-host GPU identity differs')
        if any(not math.isfinite(float(value)) or float(value) < 0 for gpu in gpus for value in gpu[2:]):
            raise ValueError('invalid shared-host GPU occupancy')
    # Before completion uses wall-clock duration with the same-host monotonic start.
    # This checks recording order; it does not establish absence of transient contention.
    before = snapshots['before']
    before_finish = (before['host_ns'] + before['finished_utc_ns'] - before['utc_ns']) / 1e9
    if before_finish >= start or snapshots['after']['host_ns'] / 1e9 <= end:
        raise ValueError('shared-host snapshots overlap formal timing')
    return snapshots


def audit_cell(folder, row, dataset, references, read, protocol=None):
    if read(folder / 'COMPLETED') != row:
        raise ValueError('completion row differs from schedule')
    config = read(folder / 'measurement/config.json')
    expected = {'images': row['images'], 'tokens': row['tokens'], 'concurrency': row['concurrency'],
                'warmup': 20, 'requests': 100, 'repetitions': 1, 'lite': row['mode'] == 'lite',
                'model': HOST_ROOT + '/models/MiniCPM-V-2_6', 'dataset': HOST_ROOT + '/dataset'}
    if any(config.get(key) != value for key, value in expected.items()):
        raise ValueError('actual configuration differs from frozen protocol')
    if protocol is not None:
        load_name = next(name for name, spec in LOADS.items() if spec == (row['images'], row['tokens'], row['concurrency']))
        frozen = protocol['loads'][load_name]
        if config.get('prompt') != frozen['prompt'] or hashlib.sha256(frozen['prompt'].encode()).hexdigest() != frozen['prompt_sha256']:
            raise ValueError('actual prompt differs from premeasurement freeze')
    endpoints = ['http://127.0.0.1:19810'] if row['system'] == 'epd' else [f'http://127.0.0.1:{19800+i}' for i in range(3)]
    if config['urls'] != endpoints:
        raise ValueError('endpoint budget/routing differs')
    raw = read(folder / 'measurement/requests.jsonl', lines=True)
    expected_keys = {(True, -1, i) for i in range(20)} | {(False, 0, i) for i in range(100)}
    keys = [(r['warmup'], r['repetition'], r['index']) for r in raw]
    if len(raw) != 120 or set(keys) != expected_keys:
        raise ValueError('missing/duplicate/wrongly classified request rows')
    reference_name = 'coco8-t128' if row['images'] == 8 else 'coco-' + str(row['images'])
    expected_ids = references[reference_name]['response']['processed_prompt_token_ids']
    if not expected_ids:
        raise ValueError('empty reference input IDs')
    for item in raw:
        index = item['index']
        paths = [HOST_ROOT + '/dataset/' + dataset['images'][(index * row['images'] + j) % 20]['file'] for j in range(row['images'])]
        if protocol is not None:
            request = frozen['requests'][index if item['warmup'] else 20+index]
            if request['index'] != index or request['warmup'] != item['warmup'] or [HOST_ROOT+'/dataset/'+image['file'] for image in request['images']] != paths:
                raise ValueError('actual sequence differs from frozen requests')
        response = item.get('response', {})
        stamps = response.get('timestamps', [])
        if (item.get('success') is not True or item['images'] != paths or
                item['endpoint'] != endpoints[index % len(endpoints)] or
                item.get('visual_tokens') != 64 * row['images'] or
                item.get('output_tokens') != row['tokens'] or
                response.get('processed_prompt_token_ids') != expected_ids or
                len(response.get('output_token_ids', [])) != row['tokens'] or len(stamps) != row['tokens']):
            raise ValueError('request failed or input/length/routing mismatch')
        if any(not math.isfinite(x) for x in stamps) or stamps != sorted(stamps):
            raise ValueError('nonfinite/nonmonotonic token timestamps')
        submit = item['submission_perf_counter']
        end = submit + item['latency_s']
        if not submit <= stamps[0] <= stamps[-1] <= end:
            raise ValueError('token timestamp domain mismatch')
        close(item['ttft_s'], stamps[0] - submit)
        close(item['tpot_s'], (stamps[-1] - stamps[0]) / (row['tokens'] - 1))
        for metric in METRICS:
            if not math.isfinite(item[metric]) or item[metric] <= 0:
                raise ValueError('nonpositive/nonfinite latency')
    summaries = read(folder / 'measurement/summary.json')
    if len(summaries) != 1:
        raise ValueError('wrong repetition count')
    summary = summaries[0]
    formal = [r for r in raw if not r['warmup']]
    start, end = summary['start_perf_counter'], summary['end_perf_counter']
    if not math.isfinite(start) or not math.isfinite(end) or end <= start:
        raise ValueError('invalid formal timing window')
    host_context = audit_host_snapshots(folder, start, end, read)
    if any(r['submission_perf_counter'] < start or r['submission_perf_counter'] + r['latency_s'] > end + 1e-8 for r in formal):
        raise ValueError('request outside formal window')
    for key, expected_value in [('requests', 100), ('successes', 100), ('repetition', 0), ('failure_rate', 0)]:
        close(summary[key], expected_value)
    close(summary['duration_s'], end - start)
    close(summary['requests_per_s'], 100 / (end - start))
    close(summary['output_tokens_per_s'], 100 * row['tokens'] / (end - start))
    for metric in METRICS:
        for quantile, fraction in [('p50', .5), ('p95', .95)]:
            close(summary[metric][quantile], percentile([r[metric] for r in formal], fraction))
    runtime, worker_pids, api_pids, rgb_records = audit_runtime(folder, endpoints, read)
    if protocol is not None:
        expected_rgb = [{'file':image['file'], 'mode':'RGB', 'size':image['size'], 'rgb_sha256':image['rgb_sha256']} for image in protocol['images']]
        if any(r['images'] != expected_rgb or r['manifest_sha256'] != protocol['dataset_manifest_sha256'] for r in rgb_records):
            raise ValueError('actual cached RGB differs from premeasurement freeze')
    if row['mode'] == 'lite':
        warmup_end = max(r['submission_perf_counter'] + r['latency_s'] for r in raw if r['warmup'])
        audit_lite(folder, endpoints, worker_pids, api_pids, warmup_end, start, end, read)
    samples = read(folder / 'gpu-memory.jsonl', lines=True)
    if not samples:
        raise ValueError('no GPU monitoring samples')
    times = [s['perf_counter'] for s in samples]
    if any(not math.isfinite(t) for t in times) or any(b <= a or b - a > MAX_SAMPLE_GAP_S for a, b in zip(times, times[1:])):
        raise ValueError('nonmonotonic/missing GPU sampling intervals')
    if times[0] > start + MAX_SAMPLE_EDGE_S or times[-1] < end - MAX_SAMPLE_EDGE_S:
        raise ValueError('GPU samples do not cover formal window edges')
    for sample in samples:
        if len(sample['gpus']) != 3 or {g['device'] for g in sample['gpus']} != set(DEVICES) or any(g['foreign_compute_pids'] for g in sample['gpus']):
            raise ValueError('wrong monitored GPU budget or foreign process')
        for gpu in sample['gpus']:
            allocations = gpu['owned_processes']
            pids = [p['pid'] for p in allocations]
            expected_pid = next(w['pid'] for w in runtime['workers'] if w['gpu_uuid'] == UUIDS[DEVICES.index(gpu['device'])])
            if len(pids) != len(set(pids)) or not set(pids) <= {expected_pid} or any(type(p['used_bytes']) is not int or p['used_bytes'] < 0 for p in allocations):
                raise ValueError('GPU attribution PID/bytes invalid')
            if gpu['owned_process_sum_bytes'] != sum(p['used_bytes'] for p in allocations):
                raise ValueError('GPU attribution sum missing/incorrect')
    measured = [s for s in samples if start <= s['perf_counter'] <= end]
    if not measured:
        raise ValueError('no memory samples within formal timing')
    if any({p['pid'] for g in s['gpus'] for p in g['owned_processes']} != worker_pids for s in measured):
        raise ValueError('GPU worker memory coverage incomplete')
    totals = [sum(g['owned_process_sum_bytes'] for g in s['gpus']) for s in measured
              if all(g['owned_process_sum_bytes'] is not None for g in s['gpus'])]
    return {**summary, 'pooled_source_rows': formal, 'shared_host_context': host_context,
            'boot_id': runtime['boot_id'], 'runtime_captured_utc': runtime['captured_utc'],
            'library_identity': runtime['loaded_cublas_sha256'], 'rgb_identity': {k: v for k, v in rgb_records[0].items() if k not in ('pid', 'url')},
            'sampled_peak_owned_bytes': max(totals) if len(totals) == len(measured) else None,
            'memory_sample_count': len(measured)}


def analyze(root, phase):
    root = root.resolve()
    sources = {}

    def read(path, lines=False):
        if not path.resolve().is_relative_to(root):
            raise ValueError('evidence path escaped experiment root')
        payload = path.read_bytes()
        sources[path.relative_to(root).as_posix()] = hashlib.sha256(payload).hexdigest()
        return [json.loads(line) for line in payload.decode().splitlines()] if lines else json.loads(payload)

    schedule_path = root / 'configs' / ('B-schedule.json' if phase == 'overhead' else 'C-schedule.json')
    schedule = read(schedule_path)
    manifest_path = root / 'configs/code-manifest.json'
    manifest = read(manifest_path)
    if sources['configs/code-manifest.json'] != CODE_SHA256:
        raise ValueError('code manifest is not the reviewed version')
    if next(item['sha256'] for item in manifest if item['path'] == schedule_path.relative_to(root).as_posix()) != sources[schedule_path.relative_to(root).as_posix()]:
        raise ValueError('schedule hash differs from reviewed code manifest')
    rows = schedule['rows']
    validate_schedule(rows, phase)
    dataset = read(root / 'dataset/manifest.json')
    if len(dataset['images']) != 20:
        raise ValueError('expected frozen 20-image dataset')
    protocol = read(root / 'evidence/frozen-request-protocol.json')
    if protocol.get('inference_requests') != 0 or protocol['dataset_manifest_sha256'] != sources['dataset/manifest.json']:
        raise ValueError('request freeze dataset identity mismatch')
    reference = read(root / 'results/preflight-models/reference.json')
    references = {r['case']['name']: r for r in reference['cases']}
    gate = read(root / 'evidence/G3_MODELS_APPROVED.json')
    if gate.get('passed') is not True or gate.get('code_manifest_sha256') != CODE_SHA256 or gate.get('gpu_uuids') != UUIDS or not gate.get('bound_files'):
        raise ValueError('model G3 binding missing')
    if not any(item['path'] == 'evidence/frozen-request-protocol.json' for item in gate['bound_files']):
        raise ValueError('G3 does not bind the premeasurement request freeze')
    frozen_at = datetime.datetime.fromisoformat(protocol['frozen_at_utc'])
    if frozen_at.tzinfo is None or protocol['boot_id'] != gate['boot_id'] or not math.isfinite(protocol['freeze_perf_counter']):
        raise ValueError('request freeze lacks same-boot timestamp binding')
    for item in gate['bound_files']:
        path = root / item['path']
        if not path.resolve().is_relative_to(root):
            raise ValueError('gate evidence path escaped experiment root')
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        sources[path.relative_to(root).as_posix()] = digest
        if digest != item['sha256']:
            raise ValueError('model G3 bound evidence changed')
    cells, outcomes = {}, []
    destination = root / 'results' / phase
    expected_folders = set()
    for index, row in enumerate(rows):
        name = f'{index:03d}-b{row["block"]}-{row["load"]}-{row["system"]}-{row["mode"]}'
        expected_folders.add(name)
        folder = destination / name
        outcome = {'schedule_index': index, **row}
        try:
            raw = read(folder / 'measurement/requests.jsonl', lines=True)
            outcome['raw_inventory'] = {'rows': len(raw),
                'warmup_rows': sum(r.get('warmup') is True for r in raw),
                'formal_rows': sum(r.get('warmup') is False for r in raw),
                'recorded_failures': sum(r.get('success') is False for r in raw),
                'recorded_successes': sum(r.get('success') is True for r in raw)}
        except (OSError, ValueError, TypeError, AttributeError) as error:
            outcome['raw_inventory'] = {'unreadable_or_missing': str(error)}
        try:
            metrics = audit_cell(folder, row, dataset, references, read, protocol)
            if metrics['start_perf_counter'] <= protocol['freeze_perf_counter'] or datetime.datetime.fromisoformat(metrics['runtime_captured_utc']) <= frozen_at:
                raise ValueError('request protocol was not frozen before this run')
            cells[(row['block'], row['load'], row['system'], row['mode'])] = metrics
            outcome.update(status='valid', metrics={k: v for k, v in metrics.items() if k != 'pooled_source_rows'})
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            outcome.update(status='missing' if not folder.exists() else 'invalid_or_incomplete', error=str(error))
        outcomes.append(outcome)
    unexpected = sorted(p.name for p in destination.iterdir() if p.is_dir() and p.name not in expected_folders) if destination.exists() else []
    marker_error = None
    try:
        marker = read(destination / 'COMPLETED')
        if marker['schedule_sha256'] != sources[schedule_path.relative_to(root).as_posix()] or marker['code_manifest_sha256'] != sources['configs/code-manifest.json']:
            raise ValueError('phase completion binding mismatch')
    except (OSError, ValueError, KeyError) as error:
        marker_error = str(error)
    complete = len(cells) == len(rows) and not unexpected and marker_error is None
    chronology_errors = []
    if len(cells) == len(rows):
        ordered = [cells[(r['block'], r['load'], r['system'], r['mode'])] for r in rows]
        for before, after in zip(ordered, ordered[1:]):
            if before['end_perf_counter'] >= after['start_perf_counter'] or datetime.datetime.fromisoformat(before['runtime_captured_utc']) >= datetime.datetime.fromisoformat(after['runtime_captured_utc']):
                chronology_errors.append('overlapping/out-of-order actual cells')
        if {c['boot_id'] for c in ordered} != {gate['boot_id']}:
            chronology_errors.append('host boot differs across blocks')
        if any(c['library_identity'] != ordered[0]['library_identity'] or c['rgb_identity'] != ordered[0]['rgb_identity'] for c in ordered):
            chronology_errors.append('actual libraries or RGB inputs differ across cells')
        if len({sources[f'results/{phase}/{index:03d}-b{r["block"]}-{r["load"]}-{r["system"]}-{r["mode"]}/runtime.json'] for index, r in enumerate(rows)}) != len(rows):
            chronology_errors.append('duplicated runtime evidence')
    complete = complete and not chronology_errors
    result = {'phase': phase, 'complete': complete, 'cells': outcomes, 'unexpected_directories': unexpected,
              'execution_scope': gate.get('scope'), 'lite_observation_approved': gate.get('lite_observation_approved'),
              'phase_marker_error': marker_error, 'intervals': {}, 'grants_no_gate': True,
              'chronology_errors': chronology_errors,
              'sampling_quality_frozen': {'max_gap_s': MAX_SAMPLE_GAP_S, 'max_edge_s': MAX_SAMPLE_EDGE_S, 'missing_attribution': 'incomplete, not zero'},
              'limitations': 'Six blocks; t intervals assume approximate normality of paired log differences. Fixed-concurrency evidence, not arrival-rate SLO; no internal-stage causality.'}
    if complete:
        loads = list(dict.fromkeys(row['load'] for row in rows))
        result['pooled_descriptive_latency'] = {}
        for load, system, mode in sorted({(r['load'], r['system'], r['mode']) for r in rows}):
            pooled = [request for block in range(6) for request in cells[(block, load, system, mode)]['pooled_source_rows']]
            result['pooled_descriptive_latency'][f'{load}/{system}/{mode}'] = {
                'formal_requests': len(pooled),
                **{metric: {'p50': percentile([r[metric] for r in pooled], .5), 'p95': percentile([r[metric] for r in pooled], .95)} for metric in METRICS},
                'interpretation': 'Pooled description only; requests are not independent block repetitions.'}

        def series(load, system, mode, metric):
            return [cells[(block, load, system, mode)]['requests_per_s'] if metric == 'throughput' else
                    cells[(block, load, system, mode)][metric]['p50'] for block in range(6)]

        if phase == 'overhead':
            for load in loads:
                for system in ('epd', 'baseline-epd'):
                    for metric, margins in [('throughput', (.98, 1.02)), ('ttft_s', (.97, 1.03)), ('tpot_s', (.97, 1.03))]:
                        result['intervals'][f'{load}/{system}/{metric}'] = equivalent(series(load, system, 'lite', metric), series(load, system, 'off', metric), *margins)
            result['all_metric_equivalence_demonstrated'] = all(x['equivalence_demonstrated'] for x in result['intervals'].values())
            result['requires_independent_coverage_and_correctness_review'] = True
        else:
            for load in loads:
                result['intervals'][load] = paired(series(load, 'epd', 'off', 'throughput'), series(load, 'baseline-epd', 'off', 'throughput'))
            result['exploratory_contrasts'] = {f'{a}/{b}': contrast(series(a, 'epd', 'off', 'throughput'), series(a, 'baseline-epd', 'off', 'throughput'), series(b, 'epd', 'off', 'throughput'), series(b, 'baseline-epd', 'off', 'throughput')) for a, b in [('D', 'C'), ('E', 'D')]}
    result['source_sha256'] = sources
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--phase', choices=('overhead', 'performance'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.root.resolve(), args.phase)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'complete': result['complete'], 'valid_cells': sum(c['status'] == 'valid' for c in result['cells'])}))
