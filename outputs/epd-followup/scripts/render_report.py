"""Render already-computed observable timing statistics; no source data mutation."""
import json
import math
import pathlib
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root = pathlib.Path(sys.argv[1]).resolve()
data = json.loads((root / 'results/analysis.json').read_text(encoding='utf-8'))
cases = data['cases']
pairs = []
for target in cases:
    if target['role'].startswith('epd-'):
        baseline = next(row for row in cases if row['host'] == target['host'] and row['images'] == target['images']
                        and row['concurrency'] == target['concurrency'] and row['role'].startswith('baseline'))
        pairs.append((baseline, target))
assert len(pairs) == 8

labels = [f"{target['host']}\n{target['images']} img / C{target['concurrency']}" for _, target in pairs]
x = np.arange(len(pairs))
fig, axes = plt.subplots(1, 2, figsize=(15, 5), constrained_layout=True)
for axis, name, title in [(axes[0], 'first', 'First API output gap: request P50 (ms)'),
                           (axes[1], 'later', 'Later API output gaps: pooled P99 (ms)')]:
    for offset, index, label, color in [(-.18, 0, '3 full-model replicas', '#546377'), (.18, 1, 'EPD 1:1:1', '#266cbd')]:
        values = [pair[index]['metrics']['first_gap_ms']['p50'] if name == 'first' else pair[index]['later_gaps_ms']['p99'] for pair in pairs]
        axis.bar(x + offset, values, width=.35, label=label, color=color)
    axis.set(title=title, xticks=x, xticklabels=labels, ylabel='ms')
    axis.grid(axis='y', alpha=.2)
    axis.tick_params(axis='x', labelsize=8)
axes[0].legend(fontsize=9)
fig.savefig(root / 'output-gaps.png', dpi=170)
plt.close(fig)

parts = [('ttft_ms', 'TTFT', '#7d91ac'), ('first_gap_ms', 'First gap', '#f0ad47'),
         ('later_window_ms', 'Later 126 gaps', '#3577b9'), ('http_tail_ms', 'HTTP tail', '#6ab5a0')]
fig, axis = plt.subplots(figsize=(12, 5), constrained_layout=True)
bottom = np.zeros(len(pairs))
delta_rows = []
for name, label, color in parts:
    values = np.array([target['metrics'][name]['mean'] - baseline['metrics'][name]['mean'] for baseline, target in pairs])
    assert np.all(values >= 0), 'signed stacking needs an update if a component is negative'
    axis.bar(x, values, bottom=bottom, label=label, color=color)
    bottom += values
axis.set(title='Mean end-to-end difference: EPD minus baseline (API observation, ms)',
         ylabel='ms', xticks=x, xticklabels=labels)
axis.legend(ncol=4, fontsize=9)
axis.grid(axis='y', alpha=.2)
for index, (baseline, target) in enumerate(pairs):
    delta = {name: target['metrics'][name]['mean'] - baseline['metrics'][name]['mean'] for name, _, _ in parts}
    delta['e2e_ms'] = target['metrics']['e2e_ms']['mean'] - baseline['metrics']['e2e_ms']['mean']
    assert math.isclose(sum(delta[name] for name, _, _ in parts), delta['e2e_ms'], abs_tol=1e-5)
    axis.text(index, bottom[index] + 2, f"{bottom[index]:.1f}", ha='center', fontsize=8)
    delta_rows.append({'host': target['host'], 'images': target['images'], 'concurrency': target['concurrency'], **delta})
axis.set_ylim(0, max(bottom) * 1.15)
fig.savefig(root / 'latency-mean-difference.png', dpi=170)
plt.close(fig)
(root / 'results/paired-mean-differences.json').write_text(json.dumps(delta_rows, indent=2), encoding='utf-8')

lines = ['# EPD退化：已有输出时间线能说明什么', '',
         '本批只读第一轮封存数据，无新GPU实验。16个配置、4,800条正式请求全部通过旧摘要对账，旧969文件与外层ZIP的SHA在分析前后相同。G1及G2/G3已APPROVE_WITH_NITS，当前数据与结论等待G4/G5审查。', '',
         '最明确的观察：EPD不仅首个输出间隔较长，后续输出窗口也普遍更长；低负载的平均E2E差主要累积在后126个间隔。高负载下，三副本基线的间隔P99存在约147ms长尾，EPD约19–20ms；这不等于EPD总吞吐更高，也不证明长尾来自prefill干扰。', '',
         '## 首间隔与后续间隔', '',
         '每格300请求；首间隔P50按请求计算，后续P95/P99按300×126＝37,800个间隔合并计算。两种分位数总体不同，不能把它们直接相加或把间隔当独立重复试验。数值为基线→EPD，单位ms。', '',
         '| 主机 / 图数 / 并发 | 首间隔P50 | 后续间隔P95 | 后续间隔P99 | 首末输出窗口P50 |',
         '|---|---:|---:|---:|---:|']
for baseline, target in pairs:
    lines.append(f"| {target['host']} / {target['images']} / {target['concurrency']} | "
                 f"{baseline['metrics']['first_gap_ms']['p50']:.2f}→{target['metrics']['first_gap_ms']['p50']:.2f} | "
                 f"{baseline['later_gaps_ms']['p95']:.2f}→{target['later_gaps_ms']['p95']:.2f} | "
                 f"{baseline['later_gaps_ms']['p99']:.2f}→{target['later_gaps_ms']['p99']:.2f} | "
                 f"{baseline['metrics']['decode_window_ms']['p50']:.1f}→{target['metrics']['decode_window_ms']['p50']:.1f} |")
lines += ['', f"![First and later API output gaps]({(root / 'output-gaps.png').as_posix()})", '',
          '首间隔本身包含不同执行路径：EPD的首token由P产出，随后经KV交接进入D；基线没有相同阶段事件。这里比较的是API输出通知间隔，不是两个相同kernel的延迟。', '',
          '## 平均端到端差异的算术分解', '',
          '逐请求E2E＝TTFT＋首间隔＋后126间隔窗口＋HTTP尾部，因此对同样300条请求的均值可相加。下表是EPD均值减基线均值；它是观察窗口的算术分解，不能当作CPU/GPU组件耗时归因。', '',
          '| 主机 / 图数 / 并发 | ΔTTFT | Δ首间隔 | Δ后126间隔窗口 | ΔHTTP尾 | ΔE2E |',
          '|---|---:|---:|---:|---:|---:|']
for row in delta_rows:
    lines.append(f"| {row['host']} / {row['images']} / {row['concurrency']} | " + ' | '.join(f"{row[name]:.2f}" for name in ['ttft_ms', 'first_gap_ms', 'later_window_ms', 'http_tail_ms', 'e2e_ms']) + ' |')
lines += ['', f"![Mean latency arithmetic decomposition]({(root / 'latency-mean-difference.png').as_posix()})", '',
          'qjh003低负载平均E2E增加127.63ms，后126间隔合计增加114.98ms、首间隔只增加4.87ms；qjh005分别为131.11ms、118.52ms、4.70ms。它排除了“已观察到的延迟差全部集中在首交接间隔”这一简单解释，仍不能排除通信造成后续依赖、API通知、调度或GPU步效率等间接影响。两系统还包含EPDServe自带引擎与原生vLLM的实现差异，这约每后续间隔0.9ms的低负载差不能直接归于解耦本身。', '',
          'EPD自身也有孤立的大间隔，部分低负载/中并发重复的最大值约209–532ms，不能把较小的池化P99理解成“EPD没有停顿”。各次重复的max与P99须一并查看。', '',
          '每次100请求的重复、完整P50/P95/P99/max及按输出窗口重叠数分组的值保存在results/analysis.json；没有只保留有利重复，也未把两台主机分位数合并。并发度、真实batch及资源预算同时不同，不能靠重叠代理单独识别批量效率因果。', '',
          '## 原事件的正确解释', '',
          '源码及隔离CPU复现确认事件字典后写覆盖，decoding_begin的去重判断又使用了错误键类型，无法保留第一次D派发。API时间戳在消费token并await断连检查后生成；基线在vLLM异步yield后记时。两者都是服务通知观测，具体路径不同。完整源码位置与SHA见source-notes.md、source-event-excerpts.md及source/replay-manifest.json。', '',
          '在本批所有2,400条EPD正式响应中，TTFT事件链均有序且完整、阶段对未见负跨度。KV调用结束均不晚于第二个API通知；这种CPU/API关系不保证真实GPU复制何时完成。数据未出现相同token时间戳，不代表已证明GPU每步恰好对应一次通知。reported_decode只作原事件描述，未作为完整解码耗时或归因依据。', '',
          '后续窗口重叠数仅用同端点首末通知半开区间重建，可能包含正在迁移或排队的请求，不是GPU在执行的batch。prefill、encoding和migration事件是CPU调用/回调时刻；不据它们计算NVLink带宽、GPU利用率或调度因果。E/P等待假设本批未作结论：TTFT分段仅保存于analysis.json，尚未结合实际GPU/队列执行作解释。', '',
          '## 下一步', '',
          '优先按next-experiments.md的方案A，在原模型/协议下做CPU+CUDA trace与profiler关闭/开启对照，观察每步API等待、Ray提交、GPU kernel及实际copy依赖。方案B的同三卡PD候选改变资源分配且官方目录尚未验证，需另行G1/G2审查及用户确认；本批没有安装或启动它。', '',
          '1图/C1来自缓存修正后的较晚会话，其他负载来自原连续矩阵；同一case内成对比较较可靠，跨负载趋势可能混入会话差异。每case只有三次100请求，300样本P95约15个尾部样本，极大间隔可能由孤立事件主导；重复详情须一并阅读。所有结论只适用于固定小模型、图片与输出长度。', '',
          '复跑见README.md；原始记录留在第一轮包，新增逐请求可观测指标在results/per-request.csv，来源路径及SHA、封存前后快照均在analysis.json。本批没有修补官方事件记录路径，避免将仪表修改混入既有性能结论。']
# These factual sentences are checked against all rows before rendering.
targets = [case for case in cases if case['role'].startswith('epd-')]
assert all(case['invalid_ttft_partitions'] == 0 for case in targets)
assert all(case['metrics']['kv_end_le_second_api_stamp']['n_true'] == 300 for case in targets)
assert all(case['metrics'][name]['n_true'] == 300 for case in targets for name in ['encoding_ordered', 'embedding_call_ordered', 'prefill_call_ordered', 'kv_call_ordered', 'reported_decode_ordered'])
assert all(case['metrics']['later_zero_gaps']['max'] == 0 for case in cases)
(root / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(root / 'report.md')
