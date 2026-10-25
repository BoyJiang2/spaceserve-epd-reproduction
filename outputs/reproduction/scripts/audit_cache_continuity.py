"""Check the original later loads share persistent workers and full RGB coverage."""
import argparse
import json
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument('root', type=pathlib.Path)
args = parser.parse_args()
results = []
for host in ('qjh003', 'qjh005'):
    suffix = '-qjh005' if host == 'qjh005' else ''
    for role in ('epd-h20', 'baseline-epd-h20'):
        matrix = args.root / 'data/raw' / host / (role + suffix)
        runtime = json.loads((args.root / 'evidence' / host / ('baseline-runtime.json' if role.startswith('baseline') else 'epd-runtime.json')).read_text())
        expected_pids = {worker['pid'] for worker in runtime['workers']}
        process_sets, overhead, samples = set(), [], 0
        with (matrix / 'gpu-memory.jsonl').open() as source:
            for line in source:
                sample = json.loads(line)
                pids = {process['pid'] for gpu in sample['gpus'] for process in gpu['owned_processes']}
                process_sets.add(tuple(sorted(pids)))
                for gpu in sample['gpus']:
                    if gpu['owned_process_sum_bytes'] is not None:
                        overhead.append(gpu['physical_used_bytes'] - gpu['owned_process_sum_bytes'])
                samples += 1
        assert process_sets == {tuple(sorted(expected_pids))}, (host, role, process_sets)
        seen, cases, previous_end = {}, [], 0
        for case in sorted(matrix.glob('images*-c*')):
            rows = [json.loads(line) for line in (case / 'requests.jsonl').read_text().splitlines()]
            summaries = json.loads((case / 'summary.json').read_text())
            assert min(row['submission_perf_counter'] for row in rows) >= previous_end
            before = {url: len(names) for url, names in seen.items()}
            if cases:
                assert all(count == 20 for count in before.values())
            for row in rows:
                seen.setdefault(row['endpoint'], set()).update(pathlib.Path(path).name for path in row['images'])
            assert all(len(names) == 20 for names in seen.values())
            previous_end = summaries[-1]['end_perf_counter']
            cases.append({'case': case.name, 'rgb_coverage_before_case': before,
                          'rgb_coverage_after_case': {url: len(names) for url, names in seen.items()}})
        results.append({'host': host, 'role': role, 'passed': True, 'samples': samples,
                        'stable_gpu_worker_pids': sorted(expected_pids),
                        'physical_minus_owned_memory_mib_range': [min(overhead) / 2**20, max(overhead) / 2**20],
                        'cases': cases})
record = {'scope': 'Path coverage reconstructed assuming the reviewed non-evicting interface cache; source run_matrix loops preserve services, GPU samples show unchanged owned worker PIDs, and case clocks are sequential. This is not measured cache-hit cost or proof of all API state.',
          'results': results}
(args.root / 'report/h20-cache-continuity.json').write_text(json.dumps(record, indent=2))
print(json.dumps([{key: value for key, value in item.items() if key != 'cases'} for item in results], indent=2))
