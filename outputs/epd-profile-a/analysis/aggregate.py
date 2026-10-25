"""Recompute the fixed 2400-request experiment and its observation perturbation."""
import argparse
import csv
import hashlib
import json
import math
import platform
from pathlib import Path
import statistics
import zipfile

FROZEN_ZIP_SHA = '3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38'
MEASUREMENT_BOOT = '1702fb5b-4b05-4070-bff9-8defb7af0c1d'
# Actual qjh003 physical mapping independently accepted at G3; not Nsight local deviceId.
GPU_UUIDS = {0: 'GPU-dd8ab4ed-e34e-4141-ced9-271897da8282', 1: 'GPU-c717f7e6-dc4f-3796-2994-e28b60448538', 2: 'GPU-c005197e-747d-2dc8-b77b-b123b41efd75'}
BLAS_ROOT = '/local/boyjiang/spaceserve-epd-qjh003-20261023/envs/epd/lib/python3.10/site-packages/nvidia/cublas/lib/'


def digest(path):
    with path.open('rb') as stream:
        value = hashlib.sha256()
        while data := stream.read(8 * 1024**2):
            value.update(data)
        return value.hexdigest()


def validate_runtime(runtime):
    if runtime['packages'] != {'torch': '2.4.0', 'vllm': '0.6.1.post2', 'transformers': '4.44.2', 'nvidia-cublas-cu12': '12.4.5.8'} or runtime['boot_id'] != MEASUREMENT_BOOT:
        raise RuntimeError('runtime/measurement boot differs from qjh003 G3 pin')
    workers = runtime['workers']
    if len(workers) != 3 or len({row['pid'] for row in workers}) != 3 or {row['gpu_uuid'] for row in workers} != set(GPU_UUIDS.values()):
        raise RuntimeError('three unique physical GPUs/workers required')
    expected_libraries = {BLAS_ROOT + 'libcublas.so.12', BLAS_ROOT + 'libcublasLt.so.12'}
    for worker in workers:
        if not isinstance(worker['pid'], int) or worker['pid'] <= 0 or set(worker['loaded_cublas_libraries']) != expected_libraries:
            raise RuntimeError('worker PID or loaded cuBLAS paths differ')
    return {index: next(row['pid'] for row in workers if row['gpu_uuid'] == uuid) for index, uuid in GPU_UUIDS.items()}


def validate_interval(summary, rows, repetition):
    begin, end, duration = summary['start_perf_counter'], summary['end_perf_counter'], summary['duration_s']
    if summary['repetition'] != repetition or not all(math.isfinite(value) for value in [begin, end, duration]) or duration <= 0 or not math.isclose(end - begin, duration, abs_tol=1e-8):
        raise RuntimeError('summary timing identity differs')
    first = min(row['submission_perf_counter'] for row in rows)
    last = max(row['submission_perf_counter'] + row['latency_s'] for row in rows)
    if first < begin - 1e-8 or last > end + 1e-8:
        raise RuntimeError('requests outside repetition interval')
    # The original gather includes task scheduling and final JSON/flush bookkeeping.
    # One second is an explicit audit ceiling; report the actual overhead, not an adjusted duration.
    if first - begin > 1 or end - last > 1:
        raise RuntimeError('repetition bookkeeping overhead exceeds one-second audit ceiling')
    return {'leading_client_scheduling_s': first - begin, 'trailing_record_io_s': end - last}


def validate_memory(samples, expected):
    if len(samples) < 2:
        raise RuntimeError('GPU sampling missing')
    for row in samples:
        if len(row['gpus']) != 3 or {gpu['device'] for gpu in row['gpus']} != {0, 1, 2}:
            raise RuntimeError('sample must contain three unique physical device indices')
        for gpu in row['gpus']:
            processes = gpu['owned_processes']
            if len(processes) != 1 or processes[0]['pid'] != expected[gpu['device']]:
                raise RuntimeError('sample GPU PID differs from actual runtime mapping')
            if not isinstance(processes[0]['used_bytes'], int) or not 0 <= processes[0]['used_bytes'] <= gpu['physical_used_bytes'] <= 97871 * 1024**2 or gpu['owned_process_sum_bytes'] != processes[0]['used_bytes']:
                raise RuntimeError('sample memory fields/sum invalid')


def validate_request_ids(rows, urls):
    identities = []
    for row in rows:
        rid = row.get('response', {}).get('repro_request_id')
        if row['endpoint'] not in urls or not isinstance(rid, str) or not rid:
            raise RuntimeError('request endpoint or response request ID missing')
        identities.append((row['endpoint'], rid))
    if len(set(identities)) != len(identities):
        raise RuntimeError('duplicate response request ID in endpoint namespace')


def validate_controls(controls, urls, api_pids, summaries, selected):
    if set(api_pids) != set(urls) or len(set(api_pids.values())) != len(urls):
        raise RuntimeError('API identities differ from actual RGB endpoint records')
    if len(controls) != 2 * len(urls) or [item['operation'] for item in controls] != ['start'] * len(urls) + ['stop'] * len(urls):
        raise RuntimeError('capture operation order/count differs')
    for operation in ['start', 'stop']:
        own = [item for item in controls if item['operation'] == operation]
        if {item['endpoint'] for item in own} != set(urls):
            raise RuntimeError('capture control endpoint coverage differs')
    for item in controls:
        state = item['state']
        if not all(math.isfinite(item[key]) for key in ['start', 'end']) or item['end'] < item['start'] or state['enabled'] is not True or state['capturing'] is not (item['operation'] == 'start') or state['pid'] != api_pids[item['endpoint']]:
            raise RuntimeError('capture control state/time/PID invalid')
    if any(a['end'] > b['start'] for a, b in zip(controls, controls[1:])):
        raise RuntimeError('capture controls not sequential')
    last_start = max(item['end'] for item in controls if item['operation'] == 'start')
    if min(item['start'] for item in controls) < summaries[2]['start_perf_counter'] or any(row['submission_perf_counter'] < last_start for row in selected):
        raise RuntimeError('capture barrier or repetition violated')
    if min(item['start'] for item in controls if item['operation'] == 'stop') < summaries[2]['end_perf_counter']:
        raise RuntimeError('capture stopped before formal timing ended')


def stats(values):
    values = sorted(values)
    if not values:
        raise RuntimeError('empty metric')
    result = {'n': len(values), 'mean': statistics.mean(values), 'sd': statistics.stdev(values) if len(values) > 1 else 0, 'max': values[-1]}
    for name, fraction in [('p50', .5), ('p95', .95), ('p99', .99)]:
        position = (len(values) - 1) * fraction
        low = int(position)
        result[name] = values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (position - low)
    return result


def indexed(rows):
    formal = [row for row in rows if not row['warmup']]
    result = {(row['repetition'], row['index']): row for row in formal}
    if len(formal) != 300 or len(result) != 300:
        raise RuntimeError('duplicate or missing formal requests')
    return result


def compare(first, second):
    first, second = indexed(first), indexed(second)
    if set(first) != set(second):
        raise RuntimeError('request identity sets differ')
    inputs, outputs = 0, 0
    for key in first:
        a, b = first[key], second[key]
        if [Path(name).name for name in a['images']] != [Path(name).name for name in b['images']]:
            raise RuntimeError('image order differs')
        inputs += a['response']['processed_prompt_token_ids'] == b['response']['processed_prompt_token_ids']
        outputs += a['response']['output_token_ids'] == b['response']['output_token_ids']
    if inputs != 300:
        raise RuntimeError('processed inputs differ')
    return {'pairs': 300, 'processed_input_ids_equal': inputs, 'output_ids_equal': outputs,
            'output_ids_different': 300 - outputs, 'scope': 'token equality; differing valid outputs are retained'}


def metric_rows(rows):
    return {name: stats([row[field] * 1000 for row in rows]) for name, field in [('e2e_ms', 'latency_s'), ('ttft_ms', 'ttft_s'), ('tpot_ms', 'tpot_s')]}


def collect(case, mode, role, images, concurrency):
    if not (case / 'COMPLETED').exists():
        raise RuntimeError('case completion absent')
    configuration = json.loads((case / 'measurement/config.json').read_text())
    if (configuration['images'], configuration['concurrency'], configuration['tokens'], configuration['warmup'], configuration['requests'], configuration['repetitions'], configuration['observe']) != (images, concurrency, 128, 20, 100, 3, mode == 'on'):
        raise RuntimeError('unexpected configuration')
    if Path(configuration['model']).name != 'MiniCPM-V-2_6' or len(configuration['urls']) != (1 if role == 'epd' else 3):
        raise RuntimeError('unexpected model or replica count')
    rows = [json.loads(line) for line in (case / 'measurement/requests.jsonl').read_text().splitlines()]
    warm, formal = [row for row in rows if row['warmup']], [row for row in rows if not row['warmup']]
    if len(rows) != 320 or sorted(row['index'] for row in warm) != list(range(20)) or len(formal) != 300:
        raise RuntimeError('request count mismatch')
    validate_request_ids(rows, configuration['urls'])
    for row in rows:
        response = row.get('response', {})
        stamps = response.get('timestamps', [])
        if not row['success'] or row['output_tokens'] != 128 or len(stamps) != 128 or len(response['output_token_ids']) != 128 or row['visual_tokens'] != 64 * images:
            raise RuntimeError('failed request or fixed token length mismatch')
        start = row['submission_perf_counter']
        if not all(math.isfinite(value) for value in [start, row['latency_s'], *stamps]) or not start <= stamps[0] <= stamps[-1] <= start + row['latency_s'] or any(a > b for a, b in zip(stamps, stamps[1:])):
            raise RuntimeError('invalid timestamp domain/order')
        if not math.isclose(row['ttft_s'], stamps[0] - start, abs_tol=1e-9) or not math.isclose(row['tpot_s'], (stamps[-1] - stamps[0]) / 127, abs_tol=1e-9):
            raise RuntimeError('metrics differ from raw timestamps')
    runtime = json.loads((case / 'runtime.json').read_text())
    expected_memory = validate_runtime(runtime)
    rgb_before, rgb_after = [json.loads((case / name).read_text()) for name in ['rgb-before.json', 'rgb-after.json']]
    if not rgb_before['passed'] or not rgb_after['passed'] or rgb_before['records'] != rgb_after['records']:
        raise RuntimeError('RGB buffer cache differs')
    summaries = json.loads((case / 'measurement/summary.json').read_text())
    if len(summaries) != 3 or [item['repetition'] for item in summaries] != [0, 1, 2] or any(a['end_perf_counter'] > b['start_perf_counter'] for a, b in zip(summaries, summaries[1:])):
        raise RuntimeError('repetition identities/order differ')
    memory = [json.loads(line) for line in (case / 'gpu-memory.jsonl').read_text().splitlines()]
    repeats = []
    for repetition in range(3):
        own = [row for row in formal if row['repetition'] == repetition]
        if sorted(row['index'] for row in own) != list(range(100)):
            raise RuntimeError('formal index mismatch')
        summary = summaries[repetition]
        overhead = validate_interval(summary, own, repetition)
        duration = summary['end_perf_counter'] - summary['start_perf_counter']
        if not math.isclose(duration, summary['duration_s'], abs_tol=1e-8) or summary['requests'] != 100 or summary['successes'] != 100 or summary['failure_rate'] != 0:
            raise RuntimeError('summary interval or success count mismatch')
        measured = metric_rows(own)
        for name, field in [('e2e_ms', 'latency_s'), ('ttft_ms', 'ttft_s'), ('tpot_ms', 'tpot_s')]:
            for percentile in ['p50', 'p95']:
                if not math.isclose(measured[name][percentile], summary[field][percentile] * 1000, abs_tol=1e-6):
                    raise RuntimeError('independent latency quantile differs')
        if not math.isclose(summary['requests_per_s'], 100 / duration) or not math.isclose(summary['output_tokens_per_s'], 12800 / duration):
            raise RuntimeError('throughput summary differs')
        samples = [row for row in memory if summary['start_perf_counter'] <= row['perf_counter'] <= summary['end_perf_counter']]
        validate_memory(samples, expected_memory)
        owned = [sum(gpu['owned_process_sum_bytes'] for gpu in row['gpus']) for row in samples]
        physical = [sum(gpu['physical_used_bytes'] for gpu in row['gpus']) for row in samples]
        repeats.append({'repetition': repetition, 'requests_per_s': 100 / duration, 'output_tokens_per_s': 12800 / duration,
                        'duration_s': duration, 'metrics': measured, 'timing_bookkeeping': overhead, 'sampled_owned_peak_gib': max(owned) / 2**30,
                        'sampled_physical_peak_gib': max(physical) / 2**30, 'memory_samples': len(samples),
                        'memory_max_gap_s': max(b['perf_counter'] - a['perf_counter'] for a, b in zip(samples, samples[1:]))})
    controls = []
    selected = [row for row in formal if row['repetition'] == 2 and row['index'] >= 84]
    if mode == 'on':
        controls = json.loads((case / 'measurement/capture-control.json').read_text())
        api_pids = {item['url']: item['pid'] for item in rgb_before['records']}
        validate_controls(controls, configuration['urls'], api_pids, summaries, selected)
    record = {'case': case.name, 'mode': mode, 'system': role, 'images': images, 'concurrency': concurrency,
              'formal_requests': 300, 'warmup_requests': 20, 'failure_rate': 0, 'runtime': runtime,
              'metrics': metric_rows(formal), 'repetitions': repeats,
              'requests_per_s': stats([row['requests_per_s'] for row in repeats]),
              'output_tokens_per_s': stats([row['output_tokens_per_s'] for row in repeats]),
              'capture_selected_16': metric_rows(selected), 'capture_controls': controls,
              'capture_start_total_s': sum(item['end'] - item['start'] for item in controls if item['operation'] == 'start'),
              'capture_stop_total_s': sum(item['end'] - item['start'] for item in controls if item['operation'] == 'stop'),
              'sampled_owned_peak_gib': max(row['sampled_owned_peak_gib'] for row in repeats),
              'sampled_physical_peak_gib': max(row['sampled_physical_peak_gib'] for row in repeats)}
    return record, rows


def run(root, frozen):
    archive = frozen.parent / 'reproduction-h20.zip'
    if digest(archive) != FROZEN_ZIP_SHA:
        raise RuntimeError('frozen source archive differs')
    manifest = (frozen / 'SHA256SUMS').read_bytes()
    with zipfile.ZipFile(archive) as bundle:
        if bundle.read('reproduction/SHA256SUMS') != manifest:
            raise RuntimeError('frozen directory manifest differs from archive')
    entries = dict((name, sha) for sha, name in (line.split('  ', 1) for line in manifest.decode().splitlines()))
    old_sources = {}
    def old_read(name):
        path = frozen / name
        if digest(path) != entries[name]:
            raise RuntimeError('frozen source differs: ' + name)
        old_sources[name] = entries[name]
        return path.read_text(encoding='utf-8')
    old_summary = json.loads(old_read('report/summary.json'))
    records, raw, comparisons, old_comparisons = [], {}, [], []
    for mode in ['off', 'on']:
        for role in ['epd', 'baseline-epd']:
            for images, concurrency in [(1, 1), (4, 8)]:
                case = root / 'results/formal' / f'{mode}-{role}-images{images}-c{concurrency}'
                record, rows = collect(case, mode, role, images, concurrency)
                records.append(record)
                raw[(mode, role, images, concurrency)] = rows
    for role in ['epd', 'baseline-epd']:
        for images, concurrency in [(1, 1), (4, 8)]:
            off, on = [next(row for row in records if (row['mode'], row['system'], row['images'], row['concurrency']) == (mode, role, images, concurrency)) for mode in ['off', 'on']]
            delta_throughput = (on['requests_per_s']['mean'] / off['requests_per_s']['mean'] - 1) * 100
            delta_e2e = (on['metrics']['e2e_ms']['p50'] / off['metrics']['e2e_ms']['p50'] - 1) * 100
            comparisons.append({'system': role, 'images': images, 'concurrency': concurrency,
                                'on_vs_off_throughput_pct': delta_throughput, 'on_vs_off_e2e_p50_pct': delta_e2e,
                                'observation_perturbation_exceeds_5pct': abs(delta_throughput) > 5 or abs(delta_e2e) > 5,
                                'input_output_comparison': compare(raw[('off', role, images, concurrency)], raw[('on', role, images, concurrency)])})
            old_role = 'epd-h20' if role == 'epd' else 'baseline-epd-h20'
            old = next(row for row in old_summary if (row['role'], row['images'], row['concurrency']) == (old_role, images, concurrency))
            if old['result_validity'] != 'measurement_valid':
                raise RuntimeError('frozen comparison source is not measurement-valid')
            old_rows = [json.loads(line) for line in old_read(old['source_case'] + '/requests.jsonl').splitlines()]
            delta = (off['requests_per_s']['mean'] / old['request_throughput_mean'] - 1) * 100
            old_comparisons.append({'system': role, 'images': images, 'concurrency': concurrency,
                                    'off_vs_frozen_throughput_pct': delta, 'environment_diagnostic_threshold_exceeded': abs(delta) > 5,
                                    'frozen_source': old['source_case'], 'input_output_comparison': compare(old_rows, raw[('off', role, images, concurrency)])})
    paired = []
    for mode in ['off', 'on']:
        for images, concurrency in [(1, 1), (4, 8)]:
            a, b = [next(row for row in records if (row['mode'], row['system'], row['images'], row['concurrency']) == (mode, role, images, concurrency)) for role in ['epd', 'baseline-epd']]
            paired.append({'mode': mode, 'images': images, 'concurrency': concurrency,
                           'epd_vs_three_replicas_throughput_ratio': a['requests_per_s']['mean'] / b['requests_per_s']['mean'],
                           'input_output_comparison': compare(raw[(mode, 'epd', images, concurrency)], raw[(mode, 'baseline-epd', images, concurrency)])})
    for name, expected in old_sources.items():
        if digest(frozen / name) != expected:
            raise RuntimeError('frozen input changed during analysis')
    result = {'technical_audit_passed': True, 'formal_requests': 2400, 'warmup_requests': 160,
              'measurement_host': 'qjh003', 'analysis_host': platform.node(),
              'scope': 'fixed-concurrency latency/throughput and sampled aggregate memory; no SLO or GPU causality claim',
              'perturbation_threshold_note': '5% is a prespecified diagnostic threshold, not a statistical significance test; on results never replace off performance',
              'cases': records, 'on_off_comparisons': comparisons, 'off_frozen_comparisons': old_comparisons, 'same_budget_comparisons': paired,
              'frozen_archive_sha256': FROZEN_ZIP_SHA, 'verified_unchanged_frozen_sources': old_sources}
    out = root / 'report'
    out.mkdir(exist_ok=True)
    (out / 'performance.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with (out / 'performance.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=['mode', 'system', 'images', 'concurrency', 'requests_per_s_mean', 'requests_per_s_sd', 'output_tokens_per_s_mean', 'ttft_p50_ms', 'ttft_p95_ms', 'tpot_p50_ms', 'tpot_p95_ms', 'e2e_p50_ms', 'e2e_p95_ms', 'sampled_owned_peak_gib', 'failure_rate'])
        writer.writeheader()
        for row in records:
            writer.writerow({**{key: row[key] for key in ['mode', 'system', 'images', 'concurrency', 'sampled_owned_peak_gib', 'failure_rate']},
                             'requests_per_s_mean': row['requests_per_s']['mean'], 'requests_per_s_sd': row['requests_per_s']['sd'],
                             'output_tokens_per_s_mean': row['output_tokens_per_s']['mean'],
                             **{metric + '_' + label + '_ms': row['metrics'][metric + '_ms'][label] for metric in ['ttft', 'tpot', 'e2e'] for label in ['p50', 'p95']}})
    print(json.dumps({'formal_requests': 2400, 'warmup_requests': 160, 'cases': 8, 'technical_audit_passed': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--frozen', type=Path, default=Path(__file__).resolve().parents[2] / 'reproduction')
    args = parser.parse_args()
    run(args.root.resolve(), args.frozen.resolve())
