"""Render the audited phase JSON; this script never starts a model or GPU job."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

NAMES = {'baseline-space': 'Native vLLM', 'space': 'SpaceServe', 'space-mask': 'SpaceServe + encoder SM mask'}
COLORS = {'baseline-space': '#0072B2', 'space': '#D55E00', 'space-mask': '#009E73'}


def run(root, phase):
    directory = root / 'report'
    result = json.loads((directory / f'space-{phase}.json').read_text())
    if result.get('passed') is not True or result['phase'] != phase:
        raise RuntimeError('audited phase JSON missing or mismatched')
    roles = result['roles']
    if roles not in [['baseline-space', 'space'], ['baseline-space', 'space', 'space-mask']]:
        raise RuntimeError('unexpected role set')
    indexed = {(row['role'], row['images'], row['concurrency']): row for row in result['cases']}
    loads = [(images, concurrency) for images in [1, 4] for concurrency in [1, 4, 8] if (roles[0], images, concurrency) in indexed]
    expected_loads = [(1, 1), (4, 8)] if phase == 'points' else [(images, concurrency) for images in [1, 4] for concurrency in [1, 4, 8]]
    if len(indexed) != len(loads) * len(roles) or loads != expected_loads:
        raise RuntimeError('incomplete plot matrix')
    figure, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    x, width = np.arange(len(loads)), .8 / len(roles)
    for offset, role in enumerate(roles):
        rows = [indexed[(role, images, concurrency)] for images, concurrency in loads]
        shift = (offset - (len(roles) - 1) / 2) * width
        bars = axes[0, 0].bar(x + shift, [row['requests_per_s']['mean'] for row in rows], width=width,
                             yerr=[row['requests_per_s']['sd'] for row in rows], capsize=3,
                             color=COLORS[role], label=NAMES[role])
        axes[0, 0].bar_label(bars, fmt='%.3f', padding=3, fontsize=8, rotation=90 if phase == 'all' else 0)
        for axis, metric in [(axes[0, 1], 'e2e'), (axes[1, 0], 'ttft'), (axes[1, 1], 'tpot')]:
            axis.plot(x, [row['metrics_ms'][metric]['p50'] for row in rows], 'o-', color=COLORS[role], label=NAMES[role])
            axis.plot(x, [row['metrics_ms'][metric]['p95'] for row in rows], '^--', color=COLORS[role])
    titles = ['Successful requests/s (mean +/- run SD)', 'End-to-end latency (ms)', 'Time to first token (ms)', 'Time per output token (ms)']
    for axis, title in zip(axes.flat, titles):
        axis.set_title(title)
        axis.set_xticks(x, [f'{images} image(s)\nC={concurrency}' for images, concurrency in loads])
        axis.set_ylim(bottom=0)
        axis.grid(axis='y', alpha=.2)
        axis.set_axisbelow(True)
        axis.legend(fontsize=7)
    axes[0, 0].set_ylim(top=axes[0, 0].get_ylim()[1] * 1.12)
    figure.suptitle('Qwen2-VL-7B-Instruct, one H20 on qjh000, profiler off\nLatency: solid P50, dashed P95; 300 measured requests per configuration')
    figure.savefig(directory / f'performance-{phase}.png', dpi=180)
    figure.savefig(directory / f'performance-{phase}.svg')
    plt.close(figure)

    status = json.loads((root / 'status.json').read_text())
    stage = '低／高两点' if phase == 'points' else '完整六点'
    lines = [f'# SpaceServe 7B：qjh000 {stage}对照', '',
        f"本表覆盖{len(roles)}组、{len(result['cases'])}配置、{result['formal_requests']:,}条正式请求和{result['warmup_requests']}条预热。GPU预算固定为同一张H20。统计由逐请求数据复算，独立审查状态见文末。", '',
        f'![吞吐和延迟](performance-{phase}.png)', '',
        '## 同机对照结果', '',
        '| 组别 | 图/C | 请求/s 均值±SD | 输出tokens/s 均值±SD | TTFT P50/P95 ms | TPOT P50/P95 ms | E2E P50/P95 ms | 所有进程采样峰值GiB | 失败率 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for images, concurrency in loads:
        for role in roles:
            row = indexed[(role, images, concurrency)]
            metrics = [f"{row['metrics_ms'][name]['p50']:.2f}/{row['metrics_ms'][name]['p95']:.2f}" for name in ['ttft', 'tpot', 'e2e']]
            lines.append(f"| {NAMES[role]} | {images}/{concurrency} | {row['requests_per_s']['mean']:.4f}±{row['requests_per_s']['sd']:.4f} | {row['output_tokens_per_s']['mean']:.2f}±{row['output_tokens_per_s']['sd']:.2f} | " + ' | '.join(metrics) + f" | {row['sampled_owned_peak_gib']:.3f} | {row['failure_rate']:.1%} |")
    lines += ['', '| 对照组 | 图/C | 请求吞吐/原生 | 输出token IDs不同的配对数（含20预热） |', '|---|---|---:|---:|']
    for row in result['comparisons']:
        lines.append(f"| {NAMES[row['experiment']]} | {row['images']}/{row['concurrency']} | {row['request_throughput_ratio']:.4f}× | {len(row['output_token_differences'])}/{row['compared_requests_including_warmup']} |")
    if 'space-mask' in roles:
        lines += ['', '| 图/C | 启用SM掩码/不启用掩码的请求吞吐 |', '|---|---:|']
        for images, concurrency in loads:
            ratio = indexed[('space-mask', images, concurrency)]['requests_per_s']['mean'] / indexed[('space', images, concurrency)]['requests_per_s']['mean']
            lines.append(f'| {images}/{concurrency} | {ratio:.4f}× |')
    ratios = [row['request_throughput_ratio'] for row in result['comparisons']]
    if phase == 'all':
        lines += ['', '完整矩阵各负载的收益、退化和下一轮建议见[本轮结论](final-summary.md)。']
    lines += ['', f"各实验组相对原生的平均吞吐比范围为{min(ratios):.4f}–{max(ratios):.4f}×。比值只描述本轮三次均值，不是显著性检验；差异须结合SD、延迟和采样显存一起读，不预设所有负载都加速。逐重复数值、采样覆盖及所有输出差异key保存在JSON。", '',
        '首轮低／高两点的具体取舍如下；完整矩阵也保留这两个已测点，不重复采集。']
    for images, concurrency in [(1, 1), (4, 8)]:
        baseline = indexed[('baseline-space', images, concurrency)]
        for role in roles[1:]:
            tested = indexed[(role, images, concurrency)]
            delta = (tested['requests_per_s']['mean'] / baseline['requests_per_s']['mean'] - 1) * 100
            lines.append(f"{images}图/C{concurrency}下，{NAMES[role]}相对原生吞吐均值{delta:+.2f}%；TTFT P50由{baseline['metrics_ms']['ttft']['p50']:.2f}变为{tested['metrics_ms']['ttft']['p50']:.2f}ms，TPOT P50由{baseline['metrics_ms']['tpot']['p50']:.2f}变为{tested['metrics_ms']['tpot']['p50']:.2f}ms。")
        if 'space-mask' in roles:
            delta = (indexed[('space-mask', images, concurrency)]['requests_per_s']['mean'] / indexed[('space', images, concurrency)]['requests_per_s']['mean'] - 1) * 100
            lines.append(f"同点掩码对未划分组的吞吐均值变化为{delta:+.2f}%。")
        lines.append('')
    lines += ['高点TTFT改善同时TPOT P50变差，不能称所有延迟都改善；低点解耦组TTFT P50也高于原生。上述首轮两点中SM的额外变化很小，三次重复不构成稳定额外收益或显著性的证明。', '',
        'G4复核也观察到同一实现对同一输入存在输出变化，原生高点同样如此；详见reviews/g4-points-data-subagent.md。输出差异来源未定位，不据抽查保证全量语义质量，也不称全部逐token一致。', '']
    if 'space-mask' in roles:
        lines += [f"高点掩码组E2E P95为{indexed[('space-mask', 4, 8)]['metrics_ms']['e2e']['p95']:.2f}ms，原生为{indexed[('baseline-space', 4, 8)]['metrics_ms']['e2e']['p95']:.2f}ms，尾部也须与中位数一起比较。", '']
    lines += [
        '## 设置与机制覆盖', '',
        'Qwen/Qwen2-VL-7B-Instruct，FP16、TP=1、eager，最大上下文4096、最大序列数8，生成128 tokens；每配置20预热＋100正式×3。相同20张COCO RGB448×448图片、提示词、采样参数和请求序列，逐请求核对256视觉tokens/图、处理后input IDs及真实API端点。prefix与多模态预处理缓存关闭，RGB预载对齐。两个实现均有processor kwargs非keyword-only被丢弃的警告，对齐依据为实际RGB、视觉tokens和处理后IDs，不声称该kwargs已生效。', '',
        '同一GPU0 UUID：`GPU-d1b595ce-0b57-cdee-c1c0-9b1051aaa07e`，驱动535.161.08；Torch2.5.1/cu124、vLLM0.7.2、transformers4.49.0。SpaceServe固定66de079af4234b27f7f82ff91d238ef1351324ba，mysmctrl固定6ff57356968a3f04158b9273aa881ee6bdf04229。全部组使用同一个100%私有MPS，正式计时关闭profiler和SM诊断，模型准备、trace导出及本项目其他负载在正式测量外完成。', '',
        'cold＋restart三组共90个固定正确性案例通过，单图、多图与并发路由绑定同一原生reference。真实参数均FP16驻留同物理GPU；解耦组原始CUDA trace证明编码与语言模型执行存在重叠。SM组同PID/同实际encoder stream重复得到78→64，零mask恢复78，重新施加及首次真实编码均64；原生bit布局与实际服务二进制SHA一致。该机制仅限制编码器stream，不是decoder互斥分区或完整论文SIS，也不能将SM数量比、交叠比例当吞吐加速。', '',
        '实际主模型仍含visual权重：原生/Space语言模型进程各8,291,375,616参数，解耦另驻留675,759,104参数的encoder；未将额外视觉权重从显存统计剔除。显存为worker、API和私有MPS实际GPU进程之和，逐样本核对PID、bytes求和、物理容量与采样间隙；采样峰值不等于瞬时精确峰值。MPS身份是边界快照，另有全程GPU采样，不能证明任意瞬时外来负载绝不存在。', '',
        '官方分支的多图覆盖、缓存释放、进程队列兼容及设备/stream观测所需最小补丁保留在results/patches；所有先前失败尝试也保留。GPU重叠的原始自动JSON使用大epoch浮点微秒，有极小量化误差；独立G3以相对时间复算确认机制，报告不使用过多小数。', '',
        '## 统计与解释边界', '',
        '请求吞吐和输出tokens/s为三次实际计时窗口的算术平均±样本SD；延迟为300条正式请求合并后的inclusive线性插值P50/P95。TTFT为首个服务端token时间减客户端提交时间，未含首token回传；TPOT=(末token−首token)/127；E2E包括HTTP完成。正式结果为固定并发，不能推导真实到达率SLO。模型实现、调度和日志路径也有差异，不把全部原生/解耦差异归因为单一机制。', '',
        '旧4090/L20实验为2B，qjh003 EPD使用MiniCPM与三卡预算，本批为qjh000的7B/单卡；三者分别与各自同机基线比较，不拼成跨模型或跨硬件绝对排名。EPD方案A受限交付已独立封存，见../../epd-profile-a/report/report.md。本报告不授权新增PD/DistServe或自动资源搜索。', '',
        '当前能回答实现是否跑通、实际机制及表内负载下的收益/退化。显存已实测，吞吐/延迟差本身不能区分通信、CPU调度或GPU计算的因果占比；必要时应在下一轮另审最小消融。是否扩大模型应依据这些同机结果与显存余量，而不是追求论文A100倍数。', '',
        '## 复算与审查', '',
        f"G3：{status['gates'].get('G3_model_service', 'pending')}。本阶段G4：{status['gates'].get('G4_points' if phase == 'points' else 'G4_full', 'pending')}；交付G5：{status['gates'].get('G5', 'pending')}。技术audit通过不能替代独立审查，实际结论与处理见reviews/。", '',
        '```bash',
        f'python3 analysis/space_results.py --root /path/to/qjh000-migration --phase {phase} --output /path/to/qjh000-migration/report/space-{phase}.json',
        f'python3 analysis/write_space_report.py --root /path/to/qjh000-migration --phase {phase}', '```', '',
        '统计使用Python3.10标准库；绘图使用Matplotlib3.9.2、NumPy1.26.4，在本地CPU执行。原始measurement、配置、实际启动/压测脚本、GPU内存、RGB、MPS边界、模型参数及补丁保存在results/formal/。全矩阵复算还验证两点G4原bytes批准及双层SHA，原始数据不做修正或删异常。', '']
    (directory / f'space-{phase}-report.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote audited {phase} report and PNG/SVG')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--phase', choices=['points', 'all'], required=True)
    args = parser.parse_args()
    run(args.root.resolve(), args.phase)
