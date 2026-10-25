"""Associate real CUDA activity with NVTX worker calls, retaining batch sharing."""
import argparse
import bisect
from collections import Counter, defaultdict
import json
from pathlib import Path
import platform
import sqlite3

from aggregate import digest, stats, validate_runtime

WORKERS = {'step_encoding', 'step_llm', 'baseline.execute_model', 'migrate_blocks_encoding', 'migrate_blocks_context'}


def merge(intervals):
    result = []
    for start, end in sorted(intervals):
        if end <= start:
            raise RuntimeError('invalid CUDA interval')
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


def stage(label):
    if label['name'] == 'step_encoding':
        return 'E'
    if label['name'] == 'step_llm':
        value = label['stage'].lower()
        if value not in {'context', 'decoding'}:
            raise RuntimeError('unknown EPD worker stage')
        return {'context': 'P', 'decoding': 'D'}[value]
    if label['name'] == 'baseline.execute_model':
        if any(label['prompt']) and not all(label['prompt']):
            raise RuntimeError('mixed prompt/decode batch needs separate attribution')
        return 'baseline.prefill' if any(label['prompt']) else 'baseline.decode'
    return label['name']


def activity_summary(intervals):
    united = merge(intervals)
    if not united:
        raise RuntimeError('required stage has no associated kernels')
    return {'kernels': len(intervals), 'first_ns': united[0][0], 'last_ns': united[-1][1],
            'span_ms': (united[-1][1] - united[0][0]) / 1e6,
            'kernel_union_ms': sum(end - start for start, end in united) / 1e6}


def inspect_trace(path, selected):
    before = digest(path)
    connection = sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    strings = dict(connection.execute('select id,value from StringIds'))
    ranges = defaultdict(list)
    output = defaultdict(list)
    captures, anchors, offsets = [], [], []
    for event in connection.execute('select start,end,globalTid,text,textId from NVTX_EVENTS'):
        text = event['text'] or strings.get(event['textId'], '')
        if text == 'repro_capture':
            captures.append((event['start'], event['end']))
        if not text.startswith('{'):
            continue
        label = json.loads(text)
        if 'name' not in label:
            continue
        offsets.append(label['perf_ns'] - event['start'])
        if label['name'] == 'capture.anchor':
            anchors.append(label)
        if label['name'] == 'api.output':
            output[str(label['rid'])].append(label)
        if label['name'] in WORKERS and event['end'] is not None:
            ranges[event['globalTid']].append((event['start'], event['end'], label))
    if len(captures) != 1 or captures[0][1] is None or len(anchors) != 1:
        raise RuntimeError('capture/anchor not unique and complete')
    capture_start, capture_end = captures[0]
    if capture_end <= capture_start:
        raise RuntimeError('invalid capture bounds')
    for items in ranges.values():
        items.sort(key=lambda item: item[0])
    starts = {thread: [item[0] for item in items] for thread, items in ranges.items()}
    calls = {}
    for call in connection.execute('select start,end,globalTid,correlationId from CUPTI_ACTIVITY_KIND_RUNTIME'):
        key = (call['globalTid'] & ~0xffffff, call['correlationId'])
        if key in calls:
            raise RuntimeError('ambiguous same-process CUDA correlation ID')
        calls[key] = call
    by_request = defaultdict(lambda: defaultdict(list))
    all_kernels, linked_counts, migration = Counter(), Counter(), defaultdict(list)
    skipped, local_devices = Counter(), defaultdict(set)
    api_pid = anchors[0]['pid']
    requested = {str(row['response']['repro_request_id']): row for row in selected}
    for table in ['CUPTI_ACTIVITY_KIND_KERNEL', 'CUPTI_ACTIVITY_KIND_MEMCPY']:
        for activity in connection.execute('select * from ' + table):
            if table.endswith('_KERNEL'):
                all_kernels[(activity['globalPid'] >> 24) & 0xffffff] += 1
                local_devices[(activity['globalPid'] >> 24) & 0xffffff].add(activity['deviceId'])
            call = calls.get((activity['globalPid'], activity['correlationId']))
            if call is None:
                skipped[table + ':no_runtime'] += 1
                continue
            if call['globalTid'] not in ranges:
                skipped[table + ':no_worker_thread'] += 1
                continue
            position = bisect.bisect_right(starts[call['globalTid']], call['start']) - 1
            if position < 0:
                skipped[table + ':before_first_worker_range'] += 1
                continue
            begin, end, label = ranges[call['globalTid']][position]
            if not begin <= call['start'] <= call['end'] <= end:
                skipped[table + ':not_wholly_inside_worker_range'] += 1
                continue
            name = stage(label)
            linked_counts[table + ':' + name] += 1
            if table.endswith('_MEMCPY'):
                if name.startswith('migrate_blocks_'):
                    migration[name].append({'start': activity['start'], 'end': activity['end'], 'bytes': activity['bytes']})
                continue
            for rid in label.get('request_ids', label.get('ids', [])):
                rid = str(rid)
                if rid in requested:
                    if not capture_start <= begin <= call['end'] <= capture_end or not capture_start <= activity['start'] < activity['end'] <= capture_end:
                        raise RuntimeError('selected CUDA stage crosses capture boundary')
                    by_request[rid][name].append((activity['start'], activity['end']))
    connection.close()
    records = []
    for rid, row in requested.items():
        events = sorted(output[rid], key=lambda label: label['token'])
        if [event['token'] for event in events] != list(range(1, 129)) or any(abs(event['api_stamp'] - stamp) > 1e-8 for event, stamp in zip(events, row['response']['timestamps'])):
            raise RuntimeError('selected API output coverage/identity differs: ' + rid)
        expected = ['E', 'P', 'D'] if any('E' in stages for stages in by_request.values()) else ['baseline.prefill', 'baseline.decode']
        stages = {name: activity_summary(by_request[rid][name]) for name in expected}
        record = {'rid': rid, 'index': row['index'], 'endpoint': row['endpoint'], 'api_pid': api_pid, 'stages': stages}
        if expected == ['E', 'P', 'D']:
            record['E_last_to_P_first_ms'] = (stages['P']['first_ns'] - stages['E']['last_ns']) / 1e6
            record['P_last_to_D_first_ms'] = (stages['D']['first_ns'] - stages['P']['last_ns']) / 1e6
        records.append(record)
    if digest(path) != before:
        raise RuntimeError('SQLite changed during read-only analysis')
    return {'file': str(path), 'sha256': before, 'capture_ns': [capture_start, capture_end], 'api_pid': api_pid,
            'selected_requests': records, 'kernels_by_pid': dict(all_kernels), 'launch_association_counts': dict(linked_counts),
            'skipped_activity_counts': dict(skipped), 'process_local_kernel_device_ids': {pid: sorted(values) for pid, values in local_devices.items()},
            'observed_output_request_ids': sorted(output), 'selected_request_ids': sorted(requested),
            'extra_boundary_request_ids': sorted(set(output) - set(requested)),
            'perf_ns_minus_trace_ns_range': [min(offsets), max(offsets)],
            'migration_whole_capture': {name: {'copies': len(items), 'recorded_copy_bytes': sum(item['bytes'] for item in items),
                    'copy_union_ms': sum(end - start for start, end in merge([(item['start'], item['end']) for item in items])) / 1e6}
                for name, items in migration.items()}}


def run(root):
    results = []
    for role in ['epd', 'baseline-epd']:
        for images, concurrency in [(1, 1), (4, 8)]:
            case = root / 'results/formal' / f'on-{role}-images{images}-c{concurrency}'
            runtime = json.loads((case / 'runtime.json').read_text())
            expected_workers = set(validate_runtime(runtime).values())
            raw = [json.loads(line) for line in (case / 'measurement/requests.jsonl').read_text().splitlines()]
            selected = [row for row in raw if not row['warmup'] and row['repetition'] == 2 and 84 <= row['index'] < 100]
            api_endpoints = {item['pid']: item['url'] for item in json.loads((case / 'rgb-before.json').read_text())['records']}
            traces = []
            for path in sorted((case / 'traces').glob('*.sqlite')):
                # The anchor source is API-local; baseline request IDs have independent endpoint namespaces.
                connection = sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True)
                labels = [json.loads(row[0]) for row in connection.execute("select text from NVTX_EVENTS where text like '%capture.anchor%'")]
                connection.close()
                if len(labels) != 1 or labels[0]['pid'] not in api_endpoints:
                    raise RuntimeError('trace API identity differs from actual RGB endpoint PID')
                endpoint = api_endpoints[labels[0]['pid']]
                traces.append(inspect_trace(path, [row for row in selected if row['endpoint'] == endpoint]))
            if len(traces) != (1 if role == 'epd' else 3) or {int(pid) for trace in traces for pid in trace['kernels_by_pid']} != expected_workers:
                raise RuntimeError('physical worker coverage differs')
            records = [row for trace in traces for row in trace['selected_requests']]
            if sorted(row['index'] for row in records) != list(range(84, 100)):
                raise RuntimeError('selected request coverage differs')
            keys = list(records[0]['stages'])
            summaries = {name: {metric: stats([row['stages'][name][metric] for row in records]) for metric in ['span_ms', 'kernel_union_ms']} for name in keys}
            gaps = {name: stats([row[name] for row in records]) for name in ['E_last_to_P_first_ms', 'P_last_to_D_first_ms']} if role == 'epd' else {}
            results.append({'system': role, 'images': images, 'concurrency': concurrency, 'selected_request_count': 16,
                            'actual_worker_pid_to_physical_gpu_uuid': {str(worker['pid']): worker['gpu_uuid'] for worker in runtime['workers']},
                            'physical_identity_rule': 'runtime nvidia-smi PID to UUID pin, then exact trace worker PID coverage; CUPTI deviceId is process-local',
                            'stage_summaries': summaries, 'handoff_gap_summaries': gaps, 'traces': traces})
    result = {'passed': True, 'measurement_host': 'qjh003', 'analysis_host': platform.node(), 'cases': results,
              'association_rule': 'same process/correlationId; launch API on same thread wholly inside synchronous worker NVTX range',
              'limitations': ['Selected 16 requests only; C8 captures also contain earlier in-flight boundary requests.',
                'Per-request stage kernels include shared batch kernels: exposure, not exclusive compute cost; never sum these per-request values as GPU totals.',
                'Baseline prefill contains vision processing; no independent baseline E stage is inferred.',
                'GPU handoff gaps include communication and waiting/scheduling; they are not pure communication time.',
                'Migration copy bytes/counts cover entire capture and cannot be assigned to individual request IDs from blocks-only worker labels.',
                'CPU lifetime await/API notification times are not used as GPU execution durations.',
                'This analysis observes profiled runs and does not establish unprofiled causal bottlenecks or bandwidth.']}
    (root / 'report/cuda-analysis.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'passed': True, 'cases': 4, 'selected_requests': 64, 'sqlite_traces': 8}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    run(parser.parse_args().root.resolve())
