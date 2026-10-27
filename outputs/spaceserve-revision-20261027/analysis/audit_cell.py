# Derived from frozen scripts/audit_formal_cell.py SHA256 7a1b31c12200909936cd77646e27e3519d8c915b5f36888ade7b0f6f01cc4aa9.
# Only evidence reads relocate; serialized deployment paths retain their original meaning.
"""Reject incomplete or contaminated SpaceServe measurements in the fixed schedule."""
import json
import math
from pathlib import PurePosixPath


ROOT = PurePosixPath('/var/tmp/boyjiang-spaceserve-revision-20261027')


def audit(case,planned,source):
    config = json.loads((case / 'measurement/config.json').read_text())
    if config['model']!=str(ROOT/'models/Qwen2-VL-7B-Instruct') or config['dataset']!=str(ROOT/'dataset') or config['urls']!=['http://127.0.0.1:19770']:
        raise RuntimeError('model/dataset/endpoint differs from frozen deployment')
    if config['images']!=planned['images'] or config['concurrency']!=planned['concurrency']:
        raise RuntimeError('unexpected SpaceServe model or load')
    launch=json.loads((case/'launch.json').read_text())
    if launch['role']!=planned['role'] or launch['block']!=planned['block']:
        raise RuntimeError('actual role/block differs from schedule')
    rows = [json.loads(line) for line in (case / 'measurement/requests.jsonl').read_text().splitlines()]
    summaries = json.loads((case / 'measurement/summary.json').read_text())
    if (config['tokens'], config['warmup'], config['requests'], config['repetitions']) != (128, 20, 100, 1):
        raise RuntimeError('unexpected request protocol')
    if len(rows) != 120 or sum(row['warmup'] for row in rows) != 20 or len(summaries) != 1:
        raise RuntimeError('incomplete request count')
    warmup = [row for row in rows if row['warmup']]
    if sorted(row['index'] for row in warmup) != list(range(20)) or any(row['repetition'] != -1 for row in warmup):
        raise RuntimeError('missing or duplicate warmup requests')
    dataset = json.loads((source / 'dataset/manifest.json').read_text())
    frozen = json.loads((source / 'evidence/MODEL_INPUTS_VERIFIED-attempt1.json').read_text())
    reference=json.loads((source/'results/preflight-models-attempt1/reference.json').read_text())
    expected_ids=next(row['response']['processed_prompt_token_ids'] for row in reference if row['case']['id']==f'coco-{config["images"]}')
    cpu=json.loads((source/'evidence/formal-target-CPU.json').read_text())
    if cpu['formal_manifest_sha256']!='a1f79489ec38e14b76f2ae53b6ac6ba9e1f9ac14d33dbb397dbcfa05efca92eb' or cpu['tests_passed']!=26 or cpu['tests_skipped']!=0:
        raise RuntimeError('actual target CPU receipt differs from reviewed formal deployment')
    image_id=cpu['actual_image_token_id']
    if type(image_id) is not int or image_id<=0:
        raise RuntimeError('invalid actual model image token ID')
    if config['prompt'] != frozen['frozen_prompts'][str(config['images'])]['prompt'] or config.get('profile_after_warmup') is not False:
        raise RuntimeError('prompt changed or profiler enabled in formal cell')
    for row in rows:
        expected = [str(ROOT / 'dataset' / dataset['images'][(row['index'] * config['images'] + j) % 20]['file']) for j in range(config['images'])]
        if row['images'] != expected:
            raise RuntimeError('actual request image sequence differs from frozen protocol')
        if not row['success'] or row['output_tokens'] != 128 or row['visual_tokens'] != 256 * config['images']:
            raise RuntimeError('failed request or wrong generated/visual length')
        response = row['response']
        if row['endpoint']!='http://127.0.0.1:19770' or response['processed_prompt_token_ids']!=expected_ids:
            raise RuntimeError('endpoint or actual processed input IDs differ from G3 reference')
        if response['processed_prompt_token_ids'].count(image_id)!=256*config['images']:
            raise RuntimeError('actual visual token count differs from frozen image shape')
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
        if any(row['submission_perf_counter'] < summary['start_perf_counter'] or row['submission_perf_counter'] + row['latency_s'] > summary['end_perf_counter'] + 1e-8 for row in group):
            raise RuntimeError('formal request lies outside its measured window')
        for metric in ('latency_s','ttft_s','tpot_s'):
            values=sorted(row[metric] for row in group)
            for name,fraction in (('p50',.5),('p95',.95)):
                index=(len(values)-1)*fraction
                low=int(index)
                value=values[low]+(values[min(low+1,len(values)-1)]-values[low])*(index-low)
                if not math.isclose(summary[metric][name],value,rel_tol=1e-8,abs_tol=1e-9):
                    raise RuntimeError('latency summary differs from raw requests')
        samples = [item for item in memory if summary['start_perf_counter'] <= item['perf_counter'] <= summary['end_perf_counter']]
        if len(samples) < 2 or any(gpu['foreign_compute_pids'] for item in samples for gpu in item['gpus']):
            raise RuntimeError('missing memory samples or foreign target-GPU process; preserve and stop')
        if any(not gpu['owned_processes'] or gpu['owned_process_sum_bytes'] is None for item in samples for gpu in item['gpus']):
            raise RuntimeError('all-process GPU memory attribution unavailable')
        gaps = [b['perf_counter'] - a['perf_counter'] for a, b in zip(samples, samples[1:])]
        if any(gap<=0 for gap in gaps) or any(len(sample['gpus'])!=1 or sample['gpus'][0]['device']!=4 for sample in samples):
            raise RuntimeError('GPU sample order or physical device differs')
        if any(gpu['owned_process_sum_bytes']!=sum(item['used_bytes'] for item in gpu['owned_processes']) for sample in samples for gpu in sample['gpus']):
            raise RuntimeError('GPU attributed memory sum differs')
        begin_gap = samples[0]['perf_counter'] - summary['start_perf_counter']
        end_gap = summary['end_perf_counter'] - samples[-1]['perf_counter']
        if max(gaps) > 2 or begin_gap > 1 or end_gap > 1:
            raise RuntimeError('memory sampling stopped or has large gaps; sampled peak is insufficient')
        coverage.append({'repetition': repetition, 'samples': len(samples), 'max_gap_s': max(gaps),
                         'first_sample_after_start_s': begin_gap, 'last_sample_before_end_s': end_gap})
    if not json.loads((case / 'rgb-after.json').read_text())['passed']:
        raise RuntimeError('RGB cache validation failed')
    return {'passed': True, 'formal_requests': 100, 'warmup_requests': 20, 'images': config['images'], 'concurrency': config['concurrency'], 'memory_coverage': coverage,
            'scope': 'one formal cell technical validation; shared-host/MPS snapshots cannot exclude all transient interference; independent G4 required', 'sampling_quality': {'max_gap_s': 2, 'max_edge_s': 1}}


