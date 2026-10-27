"""Re-audit local copies and render baseline comparisons; never grant a Gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics

from analyze_formal import analyze, run_metrics

ROLES = ('baseline-space', 'space', 'space-mask')
LABELS = {'baseline-space': 'Native vLLM', 'space': 'Decoupled', 'space-mask': 'Encoder mask'}
LOADS = [(images, concurrency) for images in (1, 4) for concurrency in (1, 4, 8)]


def raw_figure(result, output):
    """Descriptive points only; missing/invalid slots are text, never zero values."""
    os.environ.setdefault('MPLCONFIGDIR', str(output / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size': 9}):
        figure, axes = plt.subplots(2, 3, figsize=(14, 9), layout='constrained')
        for axis, (images, concurrency) in zip(axes.flat, LOADS):
            cells = [cell for cell in result['cells'] if (cell['images'], cell['concurrency']) == (images, concurrency)]
            for index, role in enumerate(ROLES):
                observed = [cell for cell in cells if cell['role'] == role and cell['status'] == 'valid']
                axis.scatter([cell['block'] + (index - 1) * .12 for cell in observed],
                             [cell['metrics']['requests_per_s'] for cell in observed],
                             color=f'C{index}', marker=('o', 's', '^')[index], s=35, label=LABELS[role])
            notes = []
            for block in range(3):
                missing = [short for short, role in zip(('N', 'D', 'M'), ROLES)
                           if any(cell['block'] == block and cell['role'] == role and cell['status'] == 'missing' for cell in cells)]
                invalid = [short for short, role in zip(('N', 'D', 'M'), ROLES)
                           if any(cell['block'] == block and cell['role'] == role and cell['status'] not in ('missing', 'valid') for cell in cells)]
                notes.append(f'B{block} missing:{",".join(missing) or "-"}; invalid/partial:{",".join(invalid) or "-"}')
            axis.text(0, -.21, '\n'.join(notes), transform=axis.transAxes, va='top', fontsize=8)
            axis.set_title(f'{images} image(s) / C{concurrency} | valid {sum(cell["status"] == "valid" for cell in cells)}/9')
            axis.set_xticks(range(3), ['B0', 'B1', 'B2'])
            axis.set_xlim(-.4, 2.4)
            peak = max((cell['metrics']['requests_per_s'] for cell in cells if cell['status'] == 'valid'), default=1)
            axis.set_ylim(0, peak * 1.08)
            axis.set_xlabel('Frozen time block (horizontal offsets identify roles)')
            axis.set_ylabel('Successful requests / second (individual run)')
            axis.grid(alpha=.2)
        prefix = 'SYNTHETIC CPU TEST ONLY\n' if result.get('synthetic') else ''
        figure.suptitle(prefix + f'PARTIAL: SpaceServe / H20 / Qwen2-VL-7B | {result["valid_cells"]}/54 valid\n'
                         'Per-run observations only; no aggregate inference\n'
                         'N: Native vLLM (blue circle) | D: Decoupled (orange square) | M: Encoder mask (green triangle)', fontsize=11)
        for suffix in ('png', 'svg'):
            figure.savefig(output / ('raw-observations.' + suffix), dpi=160)
        plt.close(figure)


def number(value, digits=4):
    return '未知' if value is None else f'{value:.{digits}f}'


def grouped(cells, role, images, concurrency, metric):
    return [run_metrics(row)[metric] for row in cells
            if (row['role'], row['images'], row['concurrency']) == (role, images, concurrency)]


def figures(result, output):
    os.environ.setdefault('MPLCONFIGDIR', str(output / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    synthetic = 'SYNTHETIC CPU TEST ONLY - ' if result.get('synthetic') else ''
    labels = [f'{images} image(s) / C{concurrency}' for images, concurrency in LOADS]
    with plt.rc_context({'font.size': 10}):
        figure, axes = plt.subplots(1, 2, figsize=(14, 5), layout='constrained')
        for index, role in enumerate(ROLES):
            series = [grouped(result['cells'], role, *load, 'requests_per_s') for load in LOADS]
            axes[0].bar([x + (index - 1) * .24 for x in range(6)],
                        [statistics.mean(values) for values in series], width=.24,
                        yerr=[statistics.stdev(values) for values in series], capsize=3, label=LABELS[role])
        axes[0].set_ylabel('Successful requests / second (mean +/- sample SD)')
        axes[0].set_ylim(bottom=0)
        axes[0].legend()
        for index, (role, baseline) in enumerate((('space', 'baseline-space'), ('space-mask', 'baseline-space'), ('space-mask', 'space'))):
            series = [next(row['throughput'] for row in result['intervals']
                           if (row['role'], row['baseline_role'], row['images'], row['concurrency']) == (role, baseline, *load)) for load in LOADS]
            centers = [row['geometric_mean_ratio'] for row in series]
            axes[1].errorbar([x + (index - 1) * .15 for x in range(6)], centers,
                yerr=[[center - row['lower'] for center, row in zip(centers, series)],
                      [row['upper'] - center for center, row in zip(centers, series)]],
                fmt='o', capsize=3, label=LABELS[role] + ' / ' + LABELS[baseline])
        axes[1].axhline(1, color='gray', linestyle='--')
        axes[1].set_yscale('log')
        axes[1].set_ylabel('Paired geometric throughput ratio, 95% t CI (df=2)')
        axes[1].legend(fontsize=8)
        for axis in axes:
            axis.set_xticks(range(6), labels, rotation=25, ha='right')
            axis.grid(axis='y', alpha=.2)
        figure.suptitle(synthetic + 'SpaceServe / H20 / Qwen2-VL-7B - three time blocks')
        for suffix in ('png', 'svg'):
            figure.savefig(output / ('throughput-relative.' + suffix), dpi=160)
        plt.close(figure)
        figure, axes = plt.subplots(1, 3, figsize=(16, 5), layout='constrained')
        for axis, metric, label in zip(axes, ('ttft_s_p95', 'tpot_s_p95', 'latency_s_p95'), ('TTFT P95', 'TPOT P95', 'End-to-end P95')):
            for index, role in enumerate(ROLES):
                series = [grouped(result['cells'], role, *load, metric) for load in LOADS]
                axis.bar([x + (index - 1) * .24 for x in range(6)],
                    [1000 * statistics.mean(values) for values in series], width=.24,
                    yerr=[1000 * statistics.stdev(values) for values in series], capsize=3, label=LABELS[role])
            axis.set_xticks(range(6), labels, rotation=25, ha='right')
            axis.set_ylabel(label + ' (ms; run quantile mean +/- sample SD)')
            axis.set_ylim(bottom=0)
            axis.grid(axis='y', alpha=.2)
        axes[0].legend(fontsize=8)
        figure.suptitle(synthetic + 'Run-level P95 variation; these error bars are not confidence intervals')
        for suffix in ('png', 'svg'):
            figure.savefig(output / ('latency.' + suffix), dpi=160)
        plt.close(figure)


def render(root, output):
    result = analyze(root)
    output.mkdir(parents=True, exist_ok=False)
    payload = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    (output / 'analysis.json').write_bytes(payload)
    lines = ['# SpaceServe H20顺序平衡补充对照', '',
             '**候选报告；须实际独立G4/G5，不是实验通过或总目标完成声明。**', '',
             'Qwen2-VL-7B-Instruct，单H20、FP16/TP1/eager；原生vLLM、解耦和encoder mask使用同GPU预算、私有MPS100%、固定COCO20图及同一请求序列。每cell20预热＋100正式，输出128tokens；六负载、三时间区组、54个计划单元。', '',
             f'完整性：**{"完整54单元" if result["complete"] else "未完成或证据不足"}**；有效单元{result["valid_cells"]}/54。', '',
             '[全部源SHA、逐次统计及配对区间](analysis.json)，JSON SHA256：`' + hashlib.sha256(payload).hexdigest() + '`。', '',
             '三次时间区组是独立重复口径；100请求不当100个重复。吞吐区间使用同区组配对log比值、df2的95% Student-t；三次估计很弱，宽区间保留。三对六负载为探索比较，无多重检验后显著性宣称。冻结完整计划中负载内三位置各一次，但两两先后仍2:1；未完成批次不声称实际已实现完整位置平衡，完整批次也不能称完全先后平衡或因果收益。', '']
    if result.get('synthetic'):
        lines[0:0] = ['# SYNTHETIC CPU TEST ONLY — 不是GPU实测', '']
    terminal = result.get('terminal_controller')
    lines += ['## 实际退出及全局检查', '',
              '控制器退出：' + ('尚无终态回执，不能判为停止或成功。' if terminal is None else
                  f'PID {terminal["pid"]}，exit={terminal.get("exit_code")}；原始字段保留在analysis.json，原因不作推测。'), '']
    lines += ['- ' + str(error).replace('|', '\\|').replace('\n', ' ') for error in result['global_errors']]
    if not result['global_errors']:
        lines += ['已收集单元未发现本分析器覆盖范围内的全局冲突；这不替代G4或排除共享主机瞬态干扰。']
    lines += ['', '## 全部计划单元及逐次观测', '',
              '延迟为该次100正式请求P50/P95，单位ms；显存为窗内自有进程合计采样峰值GiB，可能包含MPS共享分配，不是独占物理容量。缺失不填零；失败/部分单元不作为有效性能点。', '',
              '| 索引/区组/图/C/组 | 状态 | 正式/预热记录；记录失败；正式失败率 | req/s；tokens/s | TTFT P50/P95 | TPOT P50/P95 | E2E P50/P95 | 采样合计GiB |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for cell in result['cells']:
        inventory = cell.get('raw_inventory') or {}
        counts = '/'.join(str(inventory.get(key, '未知')) for key in ('formal_rows', 'warmup_rows')) + '；' + str(inventory.get('recorded_failures', '未知'))
        metrics = cell.get('metrics') if cell['status'] == 'valid' else None
        counts += '；' + (number(100 * metrics['failure_rate'], 2) + '%' if metrics else '未知')
        quantiles = [('/'.join(number(1000 * metrics[metric][q], 2) for q in ('p50', 'p95')) if metrics else '—')
                     for metric in ('ttft_s', 'tpot_s', 'latency_s')]
        label = f'{cell["index"]}/{cell["block"]}/{cell["images"]}/{cell["concurrency"]}/{cell["role"]}'
        rate = number(metrics['requests_per_s']) + '；' + number(metrics['output_tokens_per_s'], 2) if metrics else '—'
        peak = number(cell['sampled_peak_bytes'] / 1024**3, 2) if metrics else '—'
        lines.append(f'| {label} | {cell["status"]} | {counts} | {rate} | ' + ' | '.join(quantiles) + f' | {peak} |')
        if cell.get('error'):
            lines.append('\n该项错误：' + cell['error'].replace('|', '\\|').replace('\n', ' ') + '\n')
    lines += ['', '## 全部54项计划配对', '',
              '只列同区组有效双方的单次吞吐比；有全局冲突则全部禁比值。单次比值不代表三次总体收益。', '',
              '| 区组/图/C | 目标/分母 | 双方状态 | 单次吞吐比 |', '|---|---|---|---:|']
    for pair in result['all_planned_pairs']:
        lines.append(f'| {pair["block"]}/{pair["images"]}/{pair["concurrency"]} | {pair["role"]}/{pair["baseline_role"]} | {pair["target_status"]}/{pair["baseline_status"]} | {number(pair["throughput_ratio"])} |')
    if result['complete']:
        lines += ['', '## 完整矩阵：三次运行与配对区间', '',
                  '吞吐和输出tokens/s为三次运行均值±样本SD。每次延迟分位数及采样峰值见上表；所有指标的逐区组配对区间见analysis.json。图中P95误差条是三次运行分位数的SD，不是合并300请求分位数或置信区间。', '',
                  '| 图/C/组 | req/s均值±SD | tokens/s均值±SD |', '|---|---:|---:|']
        for images, concurrency in LOADS:
            for role in ROLES:
                rates = grouped(result['cells'], role, images, concurrency, 'requests_per_s')
                tokens = grouped(result['cells'], role, images, concurrency, 'output_tokens_per_s')
                lines.append(f'| {images}/{concurrency}/{role} | {statistics.mean(rates):.4f}±{statistics.stdev(rates):.4f} | {statistics.mean(tokens):.2f}±{statistics.stdev(tokens):.2f} |')
        lines += ['', '| 图/C | 目标/分母 | 配对几何比［95%区间］ |', '|---|---|---:|']
        for row in result['intervals']:
            interval = row['throughput']
            lines.append(f'| {row["images"]}/{row["concurrency"]} | {row["role"]}/{row["baseline_role"]} | {interval["geometric_mean_ratio"]:.4f} ［{interval["lower"]:.4f}, {interval["upper"]:.4f}］ |')
        figures(result, output)
        lines += ['', '![吞吐与三种配对比](throughput-relative.png)', '', '![逐次延迟分位数波动](latency.png)', '']
    else:
        lines += ['', '**不生成完整矩阵性能图、合并区间或总体加速结论。** 保留全部计划项和逐次原件，后续仅按有效预约与新审查处理断点。', '']
        if not result['global_errors'] and result['valid_cells'] > 0:
            raw_figure(result, output)
            lines += ['### 逐次原始观察（不是总体结论）', '',
                      '下图只展示本批有效单次运行，全部六负载、三组及缺失/失败状态同时呈现；没有均值、拟合或置信区间。点的水平偏移只区分组，不代表真实经过时长。完整位置平衡是冻结计划，未完成批次不声称已实际达成。', '',
                      '![部分矩阵逐次原始观察](raw-observations.png)', '']
    lines += ['## 机制覆盖与解释限制', '',
              '实际预检已验证encoder真实stream的mask撤销/重施；正式组关闭profiler和SM探针。加载库不等于decoder应用mask；没有decoder互斥分区、SM数量对应吞吐份额或完整论文调度复现结论。', '',
              'min/max pixels=200704参数被vLLM忽略，实际输入448×448、每图256视觉token。解耦decoder仍保留visual与language参数，另有独立visual encoder，不能称language-only。预检trace不用于反推formal off关键路径。', '',
              '共享主机快照会遗漏瞬态干扰；固定并发不等于到达率SLO，未测极限容量。本批与历史4090/L20/H20结果分开，所有退化保留，不作跨硬件绝对排名。', '']
    (output / 'report.md').write_text('\n'.join(lines), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    render(args.root, args.output)
