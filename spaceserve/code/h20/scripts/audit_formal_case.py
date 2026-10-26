"""Reject incomplete or contaminated SpaceServe measurements before expanding load."""
import argparse
import json
import math
from pathlib import Path


def audit(case):
    config = json.loads((case / 'measurement/config.json').read_text())
    if Path(config['model']).name != 'Qwen2-VL-7B-Instruct' or config['images'] not in (1, 4) or config['concurrency'] not in (1, 4, 8):
        raise RuntimeError('unexpected SpaceServe model or load')
    rows = [json.loads(line) for line in (case / 'measurement/requests.jsonl').read_text().splitlines()]
    summaries = json.loads((case / 'measurement/summary.json').read_text())
    if (config['tokens'], config['warmup'], config['requests'], config['repetitions']) != (128, 20, 100, 3):
        raise RuntimeError('unexpected request protocol')
    if len(rows) != 320 or sum(row['warmup'] for row in rows) != 20 or len(summaries) != 3:
        raise RuntimeError('incomplete request count')
    warmup = [row for row in rows if row['warmup']]
    if sorted(row['index'] for row in warmup) != list(range(20)) or any(row['repetition'] != -1 for row in warmup):
        raise RuntimeError('missing or duplicate warmup requests')
    for row in rows:
        if not row['success'] or row['output_tokens'] != 128 or row['visual_tokens'] != 256 * config['images']:
            raise RuntimeError('failed request or wrong generated/visual length')
        response = row['response']
        if len(response['output_token_ids']) != 128 or len(response['timestamps']) != 128:
            raise RuntimeError('missing token-level evidence')
        stamps = response['timestamps']
        if any(not math.isfinite(value) for value in stamps) or any(a > b for a, b in zip(stamps, stamps[1:])):
            raise RuntimeError('invalid token timestamp order')
        start = row['submission_perf_counter']
        if not start <= stamps[0] <= stamps[-1] <= start + row['latency_s']:
            raise RuntimeError('invalid same-host timestamp domain')
        if not math.isclose(row['ttft_s'], stamps[0] - start, abs_tol=1e-9) or not math.isclose(row['tpot_s'], (stamps[-1] - stamps[0]) / 127, abs_tol=1e-9):
            raise RuntimeError('request metrics differ from raw token timestamps')
        if len(row['images']) != config['images'] or len(set(row['images'])) != config['images'] or not response.get('processed_prompt_token_ids'):
            raise RuntimeError('missing image routing or processed-input evidence')
    memory = [json.loads(line) for line in (case / 'gpu-memory.jsonl').read_text().splitlines()]
    coverage = []
    for repetition, summary in enumerate(summaries):
        group = [row for row in rows if not row['warmup'] and row['repetition'] == repetition]
        if sorted(row['index'] for row in group) != list(range(100)) or summary['repetition'] != repetition or summary['successes'] != 100:
            raise RuntimeError('missing or duplicate repetition requests')
        if summary['requests'] != 100 or summary['failure_rate'] != 0 or summary['duration_s'] <= 0 or not math.isclose(summary['end_perf_counter'] - summary['start_perf_counter'], summary['duration_s'], abs_tol=1e-8):
            raise RuntimeError('invalid repetition interval')
        if not math.isclose(summary['requests_per_s'], 100 / summary['duration_s']) or not math.isclose(summary['output_tokens_per_s'], 12800 / summary['duration_s']):
            raise RuntimeError('throughput differs from measured interval')
        samples = [item for item in memory if summary['start_perf_counter'] <= item['perf_counter'] <= summary['end_perf_counter']]
        if len(samples) < 2 or any(gpu['foreign_compute_pids'] for item in samples for gpu in item['gpus']):
            raise RuntimeError('missing memory samples or foreign target-GPU process; preserve and stop')
        if any(not gpu['owned_processes'] or gpu['owned_process_sum_bytes'] is None for item in samples for gpu in item['gpus']):
            raise RuntimeError('all-process GPU memory attribution unavailable')
        gaps = [b['perf_counter'] - a['perf_counter'] for a, b in zip(samples, samples[1:])]
        begin_gap = samples[0]['perf_counter'] - summary['start_perf_counter']
        end_gap = summary['end_perf_counter'] - samples[-1]['perf_counter']
        if max(gaps) > 1 or begin_gap > .3 or end_gap > .3:
            raise RuntimeError('memory sampling stopped or has large gaps; sampled peak is insufficient')
        coverage.append({'repetition': repetition, 'samples': len(samples), 'max_gap_s': max(gaps),
                         'first_sample_after_start_s': begin_gap, 'last_sample_before_end_s': end_gap})
    if not json.loads((case / 'rgb-after.json').read_text())['passed']:
        raise RuntimeError('RGB cache validation failed')
    return {'passed': True, 'formal_requests': 300, 'warmup_requests': 20, 'images': config['images'], 'concurrency': config['concurrency'], 'memory_coverage': coverage,
            'scope': 'technical request/visual length, target-GPU contamination and sampled memory; independent G4 still required'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('case', type=Path)
    args = parser.parse_args()
    result = audit(args.case)
    (args.case / 'technical-audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
