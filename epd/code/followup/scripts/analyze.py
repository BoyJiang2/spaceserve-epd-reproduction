"""Read frozen H20 responses; measure observable intervals, never GPU durations."""
import argparse
import bisect
import collections
import csv
import hashlib
import json
import math
import pathlib
import statistics
import zipfile

ARCHIVE_SHA256 = '3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38'


def stats(values):
    values = sorted(values)
    if not values:
        return {'n': 0}
    if all(isinstance(value, bool) for value in values):
        return {'n': len(values), 'n_true': sum(values), 'fraction_true': sum(values) / len(values)}
    result = {'n': len(values), 'mean': statistics.mean(values), 'max': values[-1]}
    for label, fraction in [('p50', .5), ('p95', .95), ('p99', .99)]:
        index = (len(values) - 1) * fraction
        low = int(index)
        result[label] = values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (index - low)
    return result


def measure(row):
    stamps = row['response']['timestamps']
    start = row['submission_perf_counter']
    assert row['success'] and len(stamps) == row['output_tokens'] == 128
    assert all(math.isfinite(value) for value in [start, row['latency_s'], *stamps])
    assert start <= stamps[0] <= stamps[-1] <= start + row['latency_s']
    gaps = [(second - first) * 1000 for first, second in zip(stamps, stamps[1:])]
    assert min(gaps) >= 0
    result = {'ttft_ms': (stamps[0] - start) * 1000,
              'decode_window_ms': (stamps[-1] - stamps[0]) * 1000,
              'first_gap_ms': gaps[0], 'later_window_ms': sum(gaps[1:]),
              'later_gap_mean_ms': statistics.mean(gaps[1:]),
              'later_gap_max_ms': max(gaps[1:]), 'later_zero_gaps': gaps[1:].count(0),
              'http_tail_ms': (start + row['latency_s'] - stamps[-1]) * 1000,
              'e2e_ms': row['latency_s'] * 1000}
    assert math.isclose(result['ttft_ms'], row['ttft_s'] * 1000, abs_tol=1e-6)
    assert math.isclose(result['decode_window_ms'] / 127, row['tpot_s'] * 1000, abs_tol=1e-6)
    assert math.isclose(sum(result[key] for key in ('ttft_ms', 'first_gap_ms', 'later_window_ms', 'http_tail_ms')), result['e2e_ms'], abs_tol=1e-5)
    events = row['response'].get('lifetime_events', [])
    assert len({event['event_type'] for event in events}) == len(events), 'unexpected duplicate serialized events'
    event = {item['event_type']: item['timestamp'] for item in events}
    assert all(math.isfinite(value) for value in event.values())
    for name, begin, end in [('encoding', 'encoding_begin', 'encoding_end'),
                             ('embedding_call', 'encoding_migration_begin', 'encoding_migration_end'),
                             ('prefill_call', 'context_begin', 'context_end'),
                             ('kv_call', 'migration_begin', 'migration_end'),
                             ('reported_decode', 'decoding_begin', 'decoding_end')]:
        if begin in event and end in event:
            result[name + '_ordered'] = event[end] >= event[begin]
            if result[name + '_ordered']:
                result[name + '_ms'] = (event[end] - event[begin]) * 1000
    chain = ['issued', 'preprocessed', 'encoding_begin', 'encoding_end',
             'encoding_migration_begin', 'encoding_migration_end', 'context_begin', 'context_end']
    if event:
        assert all(key in event for key in chain + ['migration_begin', 'migration_end', 'decoding_begin', 'decoding_end'])
        clock = [start] + [event[key] for key in chain] + [stamps[0]]
        result['ttft_partition_valid'] = all(second >= first for first, second in zip(clock, clock[1:]))
        if result['ttft_partition_valid']:
            for index, (first, second) in enumerate(zip(clock, clock[1:])):
                result['ttft_part_' + str(index) + '_ms'] = (second - first) * 1000
        result['kv_begin_ge_first_api_stamp'] = event['migration_begin'] >= stamps[0]
        result['kv_end_le_second_api_stamp'] = event['migration_end'] <= stamps[1]
        result['decode_begin_minus_second_api_stamp_ms'] = (event['decoding_begin'] - stamps[1]) * 1000
        result['decode_begin_minus_last_api_stamp_ms'] = (event['decoding_begin'] - stamps[-1]) * 1000
    return result, gaps, event


def output_overlap(starts, ends, first, second):
    if first == second:
        return 0  # Coalesced notification has no time interval; not zero active requests.
    midpoint = (first + second) / 2
    count = bisect.bisect_right(starts, midpoint) - bisect.bisect_right(ends, midpoint)
    assert count >= 1
    return count


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def freeze_snapshot(root):
    manifest_bytes = (root / 'SHA256SUMS').read_bytes()
    manifest = manifest_bytes.decode('utf-8')
    entries = {}
    for line in manifest.splitlines():
        expected, name = line.split('  ', 1)
        assert name not in entries
        assert (root / name).resolve().is_relative_to(root)
        assert digest(root / name) == expected, name
        entries[name] = expected
    actual = {path.relative_to(root).as_posix() for path in root.rglob('*')
              if path.is_file() and '__pycache__' not in path.parts and path.name != 'SHA256SUMS'}
    assert actual == set(entries)
    assert len(entries) == 969
    archive = root.parent / 'reproduction-h20.zip'
    archive_hash = digest(archive)
    assert archive_hash == ARCHIVE_SHA256
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.read('reproduction/SHA256SUMS') == manifest_bytes, 'directory manifest differs from pinned archive'
    return {'files_verified': len(entries), 'manifest_sha256': digest(root / 'SHA256SUMS'),
            'directory_content_sha256': hashlib.sha256(manifest.encode()).hexdigest(),
            'archive_sha256': archive_hash}


def run(root, output):
    if not __debug__:
        raise SystemExit('Run without -O or PYTHONOPTIMIZE: validation assertions are required')
    root, output = root.resolve(), output.resolve()
    assert not output.is_relative_to(root), 'frozen source must never contain analysis output'
    assert not root.is_relative_to(output), 'analysis output cannot contain frozen source'
    assert not output.exists() or not any(output.iterdir()), 'use an empty or unused analysis output directory'
    output.mkdir(parents=True, exist_ok=True)
    before = freeze_snapshot(root)
    selected = [item for item in json.loads((root / 'report/summary.json').read_text(encoding='utf-8'))
                if item['role'].startswith(('epd-h20', 'baseline-epd-h20'))]
    assert len(selected) == 16
    expected = {(host, role + suffix, images, concurrency)
                for host, suffix, points in [('qjh003', '', [(i, c) for i in (1, 4) for c in (1, 4, 8)]),
                                             ('qjh005', '-qjh005', [(1, 1), (4, 8)])]
                for role in ('epd-h20', 'baseline-epd-h20') for images, concurrency in points}
    actual = [(pathlib.PurePosixPath(item['source_case']).parts[2], item['role'], item['images'], item['concurrency']) for item in selected]
    assert len(set(actual)) == len(actual) and set(actual) == expected
    records, cases, sources = [], [], []
    for item in selected:
        host = pathlib.PurePosixPath(item['source_case']).parts[2]
        case = (root / item['source_case']).resolve()
        assert case.is_relative_to(root)
        assert item['result_validity'] == 'measurement_valid'
        assert item['source_kind'] == ('cache-fix' if (item['images'], item['concurrency']) == (1, 1) else 'original')
        path = case / 'requests.jsonl'
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        rows = [row for row in rows if not row['warmup']]
        assert len(rows) == 300 and collections.Counter(row['repetition'] for row in rows) == {0: 100, 1: 100, 2: 100}
        for repetition in range(3):
            assert {row['index'] for row in rows if row['repetition'] == repetition} == set(range(100))
        clocks = {}
        for endpoint in {row['endpoint'] for row in rows}:
            own = [row for row in rows if row['endpoint'] == endpoint]
            clocks[endpoint] = (sorted(row['response']['timestamps'][0] for row in own),
                                sorted(row['response']['timestamps'][-1] for row in own))
        measured, all_later, by_overlap = [], [], collections.defaultdict(list)
        for row in rows:
            values, gaps, events = measure(row)
            assert bool(events) == item['role'].startswith('epd-')
            starts, ends = clocks[row['endpoint']]
            overlap = []
            for first, second, gap in zip(row['response']['timestamps'][1:-1], row['response']['timestamps'][2:], gaps[1:]):
                count = output_overlap(starts, ends, first, second)
                if count:
                    overlap.append(count)
                by_overlap[count].append(gap)
            if overlap:
                values['output_window_overlap_mean'] = statistics.mean(overlap)
            measured.append(values)
            all_later.extend(gaps[1:])
            records.append({'host': host, 'role': item['role'], 'images': item['images'], 'concurrency': item['concurrency'],
                            'repetition': row['repetition'], 'index': row['index'], 'endpoint': row['endpoint'],
                            'source_case': item['source_case'], **values})
        metrics = {name: stats([row[name] for row in measured if name in row]) for name in sorted(set().union(*(row.keys() for row in measured)))}
        for original, new in [('ttft', 'ttft_ms'), ('latency', 'e2e_ms')]:
            for quantile in ('p50', 'p95'):
                assert math.isclose(metrics[new][quantile], item[original + '_' + quantile + '_ms'], abs_tol=1e-5)
        for quantile in ('p50', 'p95'):
            assert math.isclose(stats([row['decode_window_ms'] / 127 for row in measured])[quantile], item['tpot_' + quantile + '_ms'], abs_tol=1e-5)
        repetitions = []
        for repeat in range(3):
            subset = [values for row, values in zip(rows, measured) if row['repetition'] == repeat]
            later = [gap for row in rows if row['repetition'] == repeat for gap in measure(row)[1][1:]]
            repetitions.append({'repetition': repeat, 'metrics': {name: stats([row[name] for row in subset if name in row]) for name in metrics}, 'later_gaps_ms': stats(later)})
        cases.append({'host': host, 'role': item['role'], 'images': item['images'], 'concurrency': item['concurrency'],
                      'source_case': item['source_case'], 'source_kind': item['source_kind'],
                      'metrics': metrics, 'later_gaps_ms': stats(all_later),
                      'later_gaps_by_output_window_overlap': {str(count): stats(values) for count, values in sorted(by_overlap.items())},
                      'repetitions': repetitions, 'legacy_summary_reconciled': True,
                      'invalid_ttft_partitions': sum(not row['ttft_partition_valid'] for row in measured) if item['role'].startswith('epd-') else None})
        sources.append({'file': path.relative_to(root).as_posix(), 'sha256': digest(path), 'formal_requests': len(rows)})
    assert len(records) == 4800
    after = freeze_snapshot(root)
    assert before == after
    names = list(dict.fromkeys(key for row in records for key in row))
    with (output / 'per-request.csv').open('w', newline='', encoding='utf-8') as destination:
        writer = csv.DictWriter(destination, fieldnames=names)
        writer.writeheader()
        writer.writerows(records)
    result = {'scope': 'Observable output intervals and CPU interface events, not GPU execution durations or causal attribution',
              'formal_requests': len(records), 'configurations': len(cases), 'sources': sources,
              'frozen_before': before, 'frozen_after': after,
              'ttft_partition_labels': ['submission_to_issued', 'issued_to_preprocessed', 'wait_encoding', 'encoding_call', 'wait_embedding_call', 'embedding_call', 'wait_prefill', 'prefill_call', 'prefill_end_to_first_api_stamp'],
              'clock_scope': 'Client and services on the same host use perf_counter; API observation follows callback/queue consumption, not GPU completion. kv_* inequalities describe CPU/API ordering only; their converses do not establish callback ordering.',
              'partition_scope': 'Per-request ordered parts, or means over the same valid subset, can be summed; segment percentiles cannot be summed. Invalid partition counts are explicit, overall latency rows are never removed.',
              'output_overlap_definition': 'Same-endpoint requests with first <= gap midpoint < last output timestamp; proxy only, not GPU batch size; histogram bin 0 means zero-duration coalesced notifications, excluded from overlap mean',
              'cases': cases}
    (output / 'analysis.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'formal_requests': len(records), 'configurations': len(cases), 'frozen_source_unchanged': before == after}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source_root', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    run(args.source_root, args.output)
