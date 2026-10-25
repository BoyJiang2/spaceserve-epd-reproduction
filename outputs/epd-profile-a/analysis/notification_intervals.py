"""Read-only notification/worker-step alignment; no causal GPU-idle inference."""
import argparse
import bisect
from collections import Counter, defaultdict
import json
from pathlib import Path
import platform
import sqlite3

from aggregate import digest, stats
from trace_analysis import WORKERS, merge, stage


def duration(intervals):
    return sum(end - begin for begin, end in merge(intervals))


def clip(intervals, begin, end):
    return [(max(left, begin), min(right, end)) for left, right in intervals if max(left, begin) < min(right, end)]


def partition(begin, end, gpu, api):
    if end <= begin:
        raise RuntimeError('nonpositive notification interval')
    gpu, api = clip(gpu, begin, end), clip(api, begin, end)
    gpu_ns, api_ns = duration(gpu), duration(api)
    union = duration(gpu + api)
    return {'duration_ms': (end - begin) / 1e6, 'recorded_cuda_union_ms': gpu_ns / 1e6,
            'no_recorded_cuda_ms': (end - begin - gpu_ns) / 1e6,
            'api_disconnect_union_ms': api_ns / 1e6,
            'api_disconnect_outside_cuda_ms': (union - gpu_ns) / 1e6,
            'unexplained_ms': (end - begin - union) / 1e6}


def read_trace(path):
    before = digest(path)
    db = sqlite3.connect('file:' + path.as_posix() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    strings = dict(db.execute('select id,value from StringIds'))
    workers, outputs, disconnect = defaultdict(list), defaultdict(list), defaultdict(list)
    captures, anchors = [], []
    for event in db.execute('select start,end,globalTid,text,textId from NVTX_EVENTS'):
        text = event['text'] or strings.get(event['textId'], '')
        if text == 'repro_capture':
            captures.append([event['start'], event['end']])
        if not text.startswith('{'):
            continue
        label = json.loads(text)
        name = label.get('name')
        if name == 'capture.anchor':
            anchors.append(label)
        if name in WORKERS and event['end'] is not None:
            workers[event['globalTid']].append({'begin': event['start'], 'end': event['end'], 'label': label,
                                               'stage': stage(label), 'gpu': [], 'kernel_count': 0})
        elif name == 'api.output':
            outputs[str(label['rid'])].append({'time': event['start'], **label})
        elif name == 'api.disconnect' and event['end'] is not None:
            disconnect[str(label['rid'])].append([event['start'], event['end']])
    if len(captures) != 1 or captures[0][1] is None or len(anchors) != 1:
        raise RuntimeError('capture identity/boundary missing')
    for items in workers.values():
        items.sort(key=lambda item: item['begin'])
    starts = {thread: [row['begin'] for row in items] for thread, items in workers.items()}
    calls = {}
    for call in db.execute('select start,end,globalTid,correlationId from CUPTI_ACTIVITY_KIND_RUNTIME'):
        key = (call['globalTid'] & ~0xffffff, call['correlationId'])
        if key in calls:
            raise RuntimeError('ambiguous process/correlation')
        calls[key] = call
    tables = {row[0] for row in db.execute("select name from sqlite_master where type='table'")}
    all_gpu, copies, linked, skipped = [], [], Counter(), Counter()
    for table in ['CUPTI_ACTIVITY_KIND_KERNEL', 'CUPTI_ACTIVITY_KIND_MEMCPY', 'CUPTI_ACTIVITY_KIND_MEMSET']:
        if table not in tables:
            continue
        for activity in db.execute('select * from ' + table):
            interval = [activity['start'], activity['end']]
            all_gpu.append(interval)
            call = calls.get((activity['globalPid'], activity['correlationId']))
            position = bisect.bisect_right(starts.get(call['globalTid'], []), call['start']) - 1 if call else -1
            if position < 0:
                skipped[table] += 1
                continue
            worker = workers[call['globalTid']][position]
            if not worker['begin'] <= call['start'] <= call['end'] <= worker['end']:
                skipped[table] += 1
                continue
            worker['gpu'].append(interval)
            worker['kernel_count'] += int(table.endswith('_KERNEL'))
            linked[table] += 1
            if table.endswith('_MEMCPY') and worker['stage'].startswith('migrate_blocks_'):
                copies.append({'interval': interval, 'stage': worker['stage'], 'bytes': activity['bytes']})
    db.close()
    if digest(path) != before:
        raise RuntimeError('SQLite changed')
    return {'workers': [row for items in workers.values() for row in items], 'outputs': outputs,
            'disconnect': disconnect, 'all_gpu': merge(all_gpu), 'copies': copies, 'capture': captures[0],
            'api_pid': anchors[0]['pid'], 'sha256': before, 'linked': dict(linked), 'skipped': dict(skipped)}


def match_request(row, trace, epd):
    rid = str(row['response']['repro_request_id'])
    events = sorted(trace['outputs'][rid], key=lambda item: item['token'])
    steps = sorted([worker for worker in trace['workers'] if worker['stage'] in
                    ({'P', 'D'} if epd else {'baseline.prefill', 'baseline.decode'}) and
                    rid in list(map(str, worker['label'].get('request_ids', worker['label'].get('ids', []))))],
                   key=lambda worker: worker['begin'])
    if len(steps) != 128 or [event['token'] for event in events] != list(range(1, 129)):
        return [], 'worker/output count differs from128'
    expected = (['P'] + ['D'] * 127) if epd else (['baseline.prefill'] + ['baseline.decode'] * 127)
    if [worker['stage'] for worker in steps] != expected:
        return [], 'worker stage sequence differs'
    for step, event, stamp in zip(steps, events, row['response']['timestamps']):
        if abs(event['api_stamp'] - stamp) > 1e-8 or not step['gpu'] or step['kernel_count'] == 0:
            return [], 'output identity or worker CUDA missing'
        if step['end'] > event['time'] or max(end for _, end in step['gpu']) > event['time']:
            return [], 'worker/GPU completion after output marker'
    records = []
    for index in range(1, 128):
        previous, current, step = events[index - 1], events[index], steps[index]
        begin, end = previous['time'], current['time']
        if not trace['capture'][0] <= begin < end <= trace['capture'][1]:
            return [], 'notification window crosses capture'
        parts = partition(begin, end, trace['all_gpu'], trace['disconnect'][rid])
        prefill_workers = [worker for worker in trace['workers'] if worker['stage'] == 'baseline.prefill' and
                           rid not in list(map(str, worker['label'].get('ids', [])))]
        prefill_candidates = [worker for worker in prefill_workers if worker['begin'] < end and worker['end'] > begin]
        other_prefill = [worker for worker in prefill_workers if clip(worker['gpu'], begin, end)]
        categories = ['first_to_second_notification' if epd and index == 1 else 'steady_decode']
        if other_prefill:
            categories.append('baseline_other_request_prefill')
        record = {'rid': rid, 'request_index': row['index'], 'to_token': index + 1,
                  'categories': categories, 'window_ns': [begin, end], 'worker_cpu_ns': [step['begin'], step['end']],
                  'worker_pid': step['label']['pid'], 'worker_stage': step['stage'],
                  'worker_batch_ids': step['label'].get('request_ids', step['label'].get('ids', [])),
                  **parts, 'matched_step_cuda_union_ms': duration(clip(step['gpu'], begin, end)) / 1e6,
                  'worker_cpu_overlap_ms': duration(clip([[step['begin'], step['end']]], begin, end)) / 1e6,
                  'worker_cpu_end_to_api_marker_ms': (end - step['end']) / 1e6,
                  'api_stamp_interval_ms': (current['api_stamp'] - previous['api_stamp']) * 1000,
                  'nvtx_vs_api_interval_difference_us': ((end - begin) / 1e9 - current['api_stamp'] + previous['api_stamp']) * 1e6,
                  'other_prefill_batch_ids': [worker['label']['ids'] for worker in other_prefill],
                  'cpu_prefill_candidate_batch_ids': [worker['label']['ids'] for worker in prefill_candidates],
                  'other_prefill_cuda_union_ms': duration(clip([value for worker in other_prefill for value in worker['gpu']], begin, end)) / 1e6}
        if 'callback_stamp' in current:
            record['callback_to_api_ms'] = (current['api_stamp'] - current['callback_stamp']) * 1000
        if epd and index == 1:
            context_gpu = steps[0]['gpu']
            handoff_begin = min(left for left, _ in context_gpu)
            handoff_end = max(right for _, right in step['gpu'])
            if not trace['capture'][0] <= handoff_begin < handoff_end <= trace['capture'][1]:
                return [], 'full P/first-D window crosses capture'
            record['P_to_first_D'] = {'window_ns': [handoff_begin, handoff_end],
                'P_gpu_first_ns': handoff_begin, 'P_gpu_last_ns': max(right for _, right in context_gpu),
                'first_D_gpu_first_ns': min(left for left, _ in step['gpu']), 'first_D_gpu_last_ns': handoff_end,
                'partition': partition(handoff_begin, handoff_end, trace['all_gpu'], trace['disconnect'][rid]),
                'migration_copies': [copy for copy in trace['copies'] if clip([copy['interval']], handoff_begin, handoff_end)]}
            record['copy_scope'] = 'temporal overlap with blocks-only migration labels; not a proved per-rid copy dependency'
        records.append(record)
    return records, None


def run(root):
    accepted = json.loads((root / 'report/cuda-analysis.json').read_text())
    result, rows = [], []
    for role, images, concurrency in [('epd', 1, 1), ('baseline-epd', 1, 1), ('baseline-epd', 4, 8)]:
        case = root / 'results/formal' / f'on-{role}-images{images}-c{concurrency}'
        selected = [json.loads(line) for line in (case / 'measurement/requests.jsonl').read_text().splitlines()]
        selected = [row for row in selected if not row['warmup'] and row['repetition'] == 2 and 84 <= row['index'] < 100]
        endpoints = {item['pid']: item['url'] for item in json.loads((case / 'rgb-before.json').read_text())['records']}
        records, unmatched, traces = [], [], []
        seen = set()
        if len(selected) != 16 or sorted(row['index'] for row in selected) != list(range(84, 100)):
            raise RuntimeError('selected16 request/index coverage differs')
        for path in sorted((case / 'traces').glob('*.sqlite')):
            trace = read_trace(path)
            accepted_case = next(row for row in accepted['cases'] if row['system'] == role and row['images'] == images)
            accepted_trace = next(row for row in accepted_case['traces'] if Path(row['file']).name == path.name)
            if trace['sha256'] != accepted_trace['sha256'] or trace['api_pid'] != accepted_trace['api_pid']:
                raise RuntimeError('trace differs from independently accepted G4 source')
            if trace['api_pid'] not in endpoints:
                raise RuntimeError('unrecognized actual API endpoint PID')
            for row in selected:
                if row['endpoint'] != endpoints[trace['api_pid']]:
                    continue
                if row['index'] in seen:
                    raise RuntimeError('duplicate API trace/request association')
                seen.add(row['index'])
                matched, reason = match_request(row, trace, role == 'epd')
                records.extend(matched)
                if reason:
                    unmatched.append({'index': row['index'], 'rid': row['response']['repro_request_id'], 'reason': reason})
            traces.append({'file': str(path), 'sha256': trace['sha256'], 'api_pid': trace['api_pid'],
                           'launch_associated': trace['linked'], 'launch_unassociated': trace['skipped']})
        for row in selected:
            if row['index'] not in seen:
                unmatched.append({'index': row['index'], 'rid': row['response']['repro_request_id'], 'reason': 'endpoint trace missing'})
        for record in records:
            record.update(system=role, images=images, concurrency=concurrency)
        rows.extend(records)
        summaries = {}
        for category in ['steady_decode', 'first_to_second_notification', 'baseline_other_request_prefill']:
            subset = [row for row in records if category in row['categories']]
            if subset:
                metrics = ['duration_ms', 'recorded_cuda_union_ms', 'no_recorded_cuda_ms', 'api_disconnect_union_ms',
                           'api_disconnect_outside_cuda_ms', 'unexplained_ms', 'matched_step_cuda_union_ms',
                           'other_prefill_cuda_union_ms', 'nvtx_vs_api_interval_difference_us']
                summaries[category] = {'count': len(subset), 'metrics': {key: stats([row[key] for row in subset]) for key in metrics}}
        result.append({'system': role, 'images': images, 'concurrency': concurrency, 'expected_requests': 16,
                       'expected_intervals': 16 * 127, 'matched_intervals': len(records),
                       'matched_fraction': len(records) / (16 * 127), 'unmatched_requests': unmatched,
                       'categories': summaries, 'traces': traces})
    out = root / 'report'
    with (out / 'notification-intervals.jsonl').open('w', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    summary = {'measurement_host': 'qjh003', 'analysis_host': platform.node(), 'cases': result,
               'excluded': [{'system': 'epd', 'images': 4, 'concurrency': 8, 'reason': 'observation exceeds5%; path existence only; no quantitative interval attribution'}],
               'scope': 'NVTX output-marker intervals; API timestamp interval discrepancy is reported; ordered same-rid128 worker steps matched to128 API outputs with stage/CUDA completion checks',
               'partition': 'recorded CUDA union + API disconnect outside CUDA + unexplained = marker interval; no_recorded_cuda is its complement; CPU worker/API ranges may overlap and are not CPU service time',
               'limitations': ['Kernel/copy/memset temporal union is activity exposure, not dependency critical path or exclusive cost.',
                 'No recorded CUDA activity is not proof of physical GPU idle or CPU causality.',
                 'Other-request prefill overlap is a temporal observation, not proof of why decoding paused.',
                 'Blocks-only migration labels do not prove individual request copy dependencies.',
                 'No new GPU collection; high EPD shorter-window recollection remains unperformed.']}
    (out / 'notification-analysis.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({'cases': len(result), 'matched': len(rows), 'expected': 48 * 127}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    run(parser.parse_args().root.resolve())
