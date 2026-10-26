"""Recompute historical descriptive comparisons; never run GPU or edit sealed inputs."""
import hashlib
import json
import math
from pathlib import Path
import statistics


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(root):
    archive_path = root / 'outputs/qjh000-migration/report/space-all.json'
    archived = json.loads(archive_path.read_text())
    cases, sources = {}, [{'path': archive_path.relative_to(root).as_posix(), 'sha256': sha(archive_path)}]
    for role in ('baseline-space', 'space', 'space-mask'):
        for images, concurrency in ((1, 1), (1, 4), (1, 8), (4, 1), (4, 4), (4, 8)):
            phase = 'points' if (images, concurrency) in ((1, 1), (4, 8)) else 'rest'
            folder = root / f'outputs/qjh000-migration/results/formal/{phase}/{role}/images{images}-c{concurrency}/measurement'
            requests = [json.loads(line) for line in (folder / 'requests.jsonl').read_text().splitlines()]
            rows = [row for row in requests if not row['warmup']]
            summary = json.loads((folder / 'summary.json').read_text())
            if len(rows) != 300 or len(requests) != 320 or len(summary) != 3:
                raise ValueError('unexpected historical protocol')
            if sorted(item['repetition'] for item in summary) != [0, 1, 2]:
                raise ValueError('duplicate or missing repetition')
            if any(not row['success'] or row['output_tokens'] != 128 for row in requests):
                raise ValueError('unexpected failure or output length')
            rates = []
            for item in summary:
                matched = [row for row in rows if row['repetition'] == item['repetition']]
                duration = item['end_perf_counter'] - item['start_perf_counter']
                if not math.isfinite(duration) or duration <= 0:
                    raise ValueError('invalid throughput duration')
                rate = len(matched) / duration
                if len(matched) != 100 or abs(rate - item['requests_per_s']) > 1e-12:
                    raise ValueError('throughput window mismatch')
                rates.append(rate)
            result = {'throughput_mean': statistics.mean(rates), 'throughput_sd': statistics.stdev(rates),
                      'throughput_runs': rates}
            for metric in ('ttft', 'tpot'):
                result[metric + '_p50_ms'] = statistics.median(row[metric + '_s'] for row in rows) * 1000
            old = next(row for row in archived['cases'] if (row['role'], row['images'], row['concurrency']) == (role, images, concurrency))
            expected = [old['requests_per_s']['mean'], old['metrics_ms']['ttft']['p50'], old['metrics_ms']['tpot']['p50']]
            actual = [result['throughput_mean'], result['ttft_p50_ms'], result['tpot_p50_ms']]
            if any(abs(a - b) > 1e-9 for a, b in zip(actual, expected)):
                raise ValueError('raw recomputation differs from sealed report')
            cases[(role, images, concurrency)] = result
            for name in ('requests.jsonl', 'summary.json'):
                path = folder / name
                sources.append({'path': path.relative_to(root).as_posix(), 'sha256': sha(path)})
    output = []
    for images, concurrency in ((1, 1), (1, 4), (1, 8), (4, 1), (4, 4), (4, 8)):
        baseline = cases[('baseline-space', images, concurrency)]
        for role in ('space', 'space-mask'):
            tested = cases[(role, images, concurrency)]
            output.append({'images': images, 'concurrency': concurrency, 'role': role,
                           'baseline': baseline, 'tested': tested,
                           'changes_percent': {metric: 100 * (tested[metric] / baseline[metric] - 1)
                                               for metric in ('throughput_mean', 'ttft_p50_ms', 'tpot_p50_ms')}})
    return {'source': 'historical qjh000 H20 / Qwen2-VL-7B / 18 configurations',
            'formal_requests': 5400, 'warmup_requests': 360, 'rows': output, 'source_files': sources,
            'limitations': ['Descriptive changes, not causal effects or significance tests.',
                            'Three throughput runs per configuration; latency pools 300 formal requests.',
                            'Fixed historical execution order; no paired-run CI can be recovered afterwards.']}


def run(root):
    result = collect(root)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    destination = root / 'docs/revision'
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'space-relative.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    figure, axes = plt.subplots(1, 3, figsize=(16, 6), sharey=True)
    metrics = [('throughput_mean', 'Throughput (higher is better)'),
               ('ttft_p50_ms', 'TTFT P50 (lower is better)'), ('tpot_p50_ms', 'TPOT P50 (lower is better)')]
    for axis, (metric, title) in zip(axes, metrics):
        for role, offset, color, label in [('space', -.18, '#2563a6', 'Decoupled'),
                                            ('space-mask', .18, '#df8232', 'Encoder mask')]:
            values = [row['changes_percent'][metric] for row in result['rows'] if row['role'] == role]
            y = [i + offset for i in range(6)]
            axis.barh(y, values, height=.32, color=color, label=label)
            for position, value in zip(y, values):
                axis.annotate(f'{value:+.2f}%', (value, position), xytext=(3 if value >= 0 else -3, 0),
                              textcoords='offset points', ha='left' if value >= 0 else 'right', va='center', fontsize=8)
        axis.axvline(0, color='#444444', linewidth=.8)
        axis.margins(x=.24)
        axis.set_title(title, fontsize=11)
        axis.set_xlabel('Change relative to native vLLM (%)')
        axis.grid(axis='x', alpha=.2)
    axes[0].set_yticks(range(6), ['1 image / C1', '1 image / C4', '1 image / C8', '4 images / C1', '4 images / C4', '4 images / C8'])
    axes[0].invert_yaxis()
    figure.legend(*axes[0].get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(.5, .94), ncol=2, fontsize=9)
    figure.suptitle('Historical single-H20 7B: observed throughput and latency trade-offs', fontsize=14)
    figure.text(.5, .025, 'Three runs/configuration; pooled latency P50. Descriptive ratios only; fixed order confounds time drift. No new GPU runs.', ha='center', fontsize=9)
    figure.tight_layout(rect=(0, .065, 1, .89))
    for extension in ('png', 'svg'):
        figure.savefig(destination / ('space-relative.' + extension), dpi=170)
    plt.close(figure)
    print(json.dumps({'passed': True, 'configurations': 18, 'formal_requests': 5400, 'source_hashes': len(result['source_files'])}))


if __name__ == '__main__':
    run(Path(__file__).resolve().parents[2])
