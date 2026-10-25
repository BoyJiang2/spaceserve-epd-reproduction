"""Audit captured CPU/GPU launch associations and actual pilot correctness."""
import bisect
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

root = Path(sys.argv[1]).resolve()
if root.name != 'epd-profile-a-20261023':
    raise RuntimeError('unexpected pilot workspace')
worker_names = {'step_encoding', 'step_llm', 'migrate_blocks_context', 'migrate_blocks_encoding', 'baseline.execute_model'}


def stage(label):
    if label['name'] == 'step_encoding':
        return 'E'
    if label['name'] == 'step_llm':
        if 'CONTEXT' in label['stage'].upper():
            return 'P'
        if 'DECODING' in label['stage'].upper():
            return 'D'
        raise RuntimeError('unknown LLM stage')
    if label['name'] == 'baseline.execute_model':
        return 'baseline.prefill' if any(label['prompt']) else 'baseline.decode'
    return label['name']


def trace_record(path):
    connection = sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    strings = dict(connection.execute('select id,value from StringIds'))
    ranges = defaultdict(list)
    labels = Counter()
    events = []
    capture = []
    for event in connection.execute('select start,end,eventType,globalTid,text,textId from NVTX_EVENTS'):
        text = event['text'] or strings.get(event['textId'], '')
        if text == 'repro_capture':
            capture.append({'start': event['start'], 'end': event['end']})
        if not text.startswith('{'):
            continue
        label = json.loads(text)
        if 'name' not in label:
            continue
        labels[label['name']] += 1
        events.append({'start': event['start'], 'end': event['end'], 'label': label})
        if label['name'] in worker_names and event['end'] is not None:
            ranges[event['globalTid']].append((event['start'], event['end'], label))
    for items in ranges.values():
        items.sort(key=lambda item: item[0])
    starts = {thread: [item[0] for item in items] for thread, items in ranges.items()}
    runtime = {}
    for row in connection.execute('select start,end,globalTid,correlationId,nameId from CUPTI_ACTIVITY_KIND_RUNTIME'):
        runtime[(row['globalTid'] & ~0xffffff, row['correlationId'])] = row
    linked = Counter()
    workers = Counter()
    copy_linked = Counter()
    samples = {}
    request_stages = defaultdict(set)
    for table, counts in [('CUPTI_ACTIVITY_KIND_KERNEL', linked), ('CUPTI_ACTIVITY_KIND_MEMCPY', copy_linked)]:
        for activity in connection.execute('select * from ' + table):
            if table.endswith('_KERNEL'):
                workers[(activity['globalPid'] >> 24) & 0xffffff] += 1
            call = runtime.get((activity['globalPid'], activity['correlationId']))
            if call is None or call['globalTid'] not in ranges:
                continue
            position = bisect.bisect_right(starts[call['globalTid']], call['start']) - 1
            if position < 0:
                continue
            begin, end, label = ranges[call['globalTid']][position]
            if not (begin <= call['start'] <= call['end'] <= end):
                continue
            name = stage(label)
            counts[name] += 1
            for rid in label.get('request_ids', label.get('ids', [])):
                request_stages[str(rid)].add(name)
            key = table + ':' + name
            if key not in samples:
                samples[key] = {'label': label, 'nvtx_start': begin, 'nvtx_end': end,
                                'api': strings[call['nameId']], 'api_start': call['start'], 'api_end': call['end'],
                                'gpu_start': activity['start'], 'gpu_end': activity['end'],
                                'correlation_id': activity['correlationId'], 'global_pid': activity['globalPid']}
    connection.close()
    if len(capture) != 1 or capture[0]['end'] is None or capture[0]['end'] <= capture[0]['start']:
        raise RuntimeError('capture range not complete')
    if not all(labels[key] for key in ['capture.anchor', 'api.output']):
        raise RuntimeError('capture/API anchors missing')
    return {'file': str(path), 'capture': capture, 'kernels_by_pid': dict(workers),
            'worker_kernel_launch_links': dict(linked), 'worker_memcpy_launch_links': dict(copy_linked),
            'nvtx_name_counts': dict(labels), 'association_samples': samples,
            'request_stage_samples': {key: sorted(value) for key, value in list(request_stages.items())[:8]},
            'lifetime_samples': [event for event in events if event['label']['name'] == 'lifetime'][:12],
            'api_samples': [event for event in events if event['label']['name'] == 'api.output'][:4]}


result = {'passed': False, 'trials': [], 'association_rule': 'same process and correlationId; CUDA runtime API on same thread wholly inside synchronous worker NVTX range; GPU activity may finish after CPU range'}
for trial in ['pilot-metadata', 'pilot-metadata-restart']:
    trial_root = root / 'results' / trial
    if not (trial_root / 'COMPLETED').exists():
        raise RuntimeError('pilot did not finish: ' + trial)
    for role, expected in [('epd', 15), ('baseline-epd', 45)]:
        case = trial_root / ('on-' + role + '-images4-c8')
        runtime = json.loads((case / 'runtime.json').read_text())
        correctness = []
        for path in sorted(case.glob('correctness-*-*.json')):
            rows = json.loads(path.read_text())
            for row in rows:
                if row['exact_token_ids_equal'] is not True or row.get('routing_passed') is False:
                    raise RuntimeError('correctness failed: ' + str(path))
            correctness.extend(rows)
        if len(correctness) != expected:
            raise RuntimeError('missing correctness cases')
        for name in ['rgb-before.json', 'rgb-after.json']:
            if not json.loads((case / name).read_text())['passed']:
                raise RuntimeError('RGB cache check failed')
        traces = [trace_record(path) for path in sorted((case / 'traces').glob('*.sqlite'))]
        actual_pids = {int(pid) for trace in traces for pid in trace['kernels_by_pid']}
        expected_pids = {worker['pid'] for worker in runtime['workers']}
        if actual_pids != expected_pids or len(expected_pids) != 3:
            raise RuntimeError(f'GPU workers differ: {actual_pids} != {expected_pids}')
        if role == 'epd':
            if len(traces) != 1 or any(not traces[0]['worker_kernel_launch_links'].get(name) for name in ['E', 'P', 'D']):
                raise RuntimeError('missing causally linked E/P/D kernels')
            if any(not traces[0]['worker_memcpy_launch_links'].get(name) for name in ['migrate_blocks_context', 'migrate_blocks_encoding']):
                raise RuntimeError('missing CUDA memcpy migration links')
        elif len(traces) != 3 or any(not trace['worker_kernel_launch_links'].get(name) for trace in traces for name in ['baseline.prefill', 'baseline.decode']):
            raise RuntimeError('missing baseline prefill/decode links')
        result['trials'].append({'trial': trial, 'system': role, 'correctness_cases': len(correctness), 'runtime': runtime, 'traces': traces})
result['passed'] = True
destination = root / 'evidence/g3-pilot-acceptance.json'
destination.write_text(json.dumps(result, indent=2))
print(json.dumps({'passed': True, 'trials': len(result['trials']), 'correctness_cases': sum(item['correctness_cases'] for item in result['trials'])}))
