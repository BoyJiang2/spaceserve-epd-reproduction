"""Render audited B/C baseline comparisons, including incomplete batches; no gate approval."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics

from analyze_cells import analyze


def render(root, phase, output, *, synthetic=False):
    result = analyze(root, phase)
    terminal_path = root / 'evidence/C-resume-exit.json'
    if phase == 'performance' and terminal_path.exists():
        terminal_bytes = terminal_path.read_bytes()
        result['terminal_controller'] = json.loads(terminal_bytes)
        result['source_sha256']['evidence/C-resume-exit.json'] = hashlib.sha256(terminal_bytes).hexdigest()
    if synthetic:
        result['synthetic'] = True
    output.mkdir(parents=True, exist_ok=False)
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False).encode()
    (output / 'analysis.json').write_bytes(payload)
    lines = ['# EPD修正批次：' + ('B轻量观测开销' if phase == 'overhead' else 'C五负载性能对照'), '',
             '**候选报告，待实际独立G4/G5审查。分析器不授予任何Gate。**', '',
             'MiniCPM-V-2_6，FP16/TP1；EPD E:P:D=1:1:1，对照同三张H20上的三个完整模型副本。统一图数上限8、context4096；IRP与动态角色切换关闭。', '',
             '每cell20预热、100正式；六个时间区组。吞吐为成功请求/整个正式窗口，延迟单位ms。旧三重复结果不混入本批区间。', '',
             f'数据完整性：**{"完整" if result["complete"] else "未完成或证据不足"}**；有效cell {sum(c["status"] == "valid" for c in result["cells"])}/{len(result["cells"])}。', '',
             '[完整逐cell统计、错误和源SHA](analysis.json)。分析JSON SHA256：`' + hashlib.sha256(payload).hexdigest() + '`。', '']
    if synthetic:
        lines[0:0] = ['# SYNTHETIC TEST ONLY — 合成测试，不是GPU实验结果', '']
    if result.get('execution_scope') == 'C-off-only':
        lines += ['## 失败分支与解释范围', '',
                  '**EPD lite观察G3失败：冷启/重启worker没有导出CUDA窗口。B阶段（观测开销）正式未运行，未证明观测等效。** 独立G1及失败G4批准后仅执行原预算C-off；不调剂B预算、不增加GPU正确性请求。模型正确性通过与完整观察失败分别记录。', '',
                  '每cell计时窗外保存全机GPU、host load、available memory和swap快照；它们会遗漏窗内瞬态竞争。结果只支持该共享主机条件下的相对性能，不证明纯观察器成本、off阶段关键路径或内部因果瓶颈。', '']
    if result.get('performance_execution'):
        lines += ['## 中断及唯一断点续接', '',
                  '原控制器完成block0的10个单元（1000正式＋200预热）后，在下一单元启动阶段中断；原退出码未知（null）、原因未知。前10个单元原样保留，计划仅续接原顺序剩余50个单元（5000正式＋1000预热）；实际完成数量以数据完整性与逐cell统计为准，没有重采或调剂B预算。', '',
                  '冻结的执行版本范围（完成情况见逐cell统计）：' + '；'.join(f'索引{x["indices"]}：`{x["producer_sha256"]}`' for x in result['performance_execution']) + '。控制器版本变化不等于推理算法变化，差异与审批见原始证据。', '']
        if 'continuation_formal_window_gap_s' in result:
            lines += [f'前一区组最后正式窗口结束至续接首个正式窗口开始相隔 {result["continuation_formal_window_gap_s"]:.2f} 秒，包含清理、等待、重启及预热，不能解释为纯故障耗时。', '']
    if result.get('terminal_controller'):
        terminal = result['terminal_controller']
        terminal_relative = os.path.relpath(root / 'evidence', output).replace('\\', '/')
        lines += ['## 唯一续接的实际终止', '',
                  f'实际控制器PID {terminal["pid"]}，退出码 {terminal["exit_code"]}，错误类型 `{terminal.get("error_type")}`：{terminal.get("error", "")}。本次唯一续接额度已耗尽，不再补跑缺失单元；本批为终态部分结果，完整C未完成。身份读取失败的底层原因尚未确定，不能据此断定模型数值错误。', '',
                  f'[原退出回执]({terminal_relative}/C-resume-exit.json) · [终态资源释放证据]({terminal_relative}/C-terminal-resource-status.json)。', '']
    if result['complete']:
        os.environ.setdefault('MPLCONFIGDIR', str(output / '.mplconfig'))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        cells = result['cells']

        def metrics(load, system, mode, metric='requests_per_s'):
            return [c['metrics'][metric] for c in cells if c['load'] == load and c['system'] == system and c['mode'] == mode]

        def mean_sd(values):
            return f'{statistics.mean(values):.4f} ± {statistics.stdev(values):.4f}'

        if phase == 'overhead':
            fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), layout='constrained')
            lines += ['## off与lite对照', '',
                      '| 负载/系统 | off req/s 均值±SD | lite req/s 均值±SD | lite/off吞吐比 90%CI |',
                      '|---|---:|---:|---:|']
            for load in ('low', 'high'):
                for system in ('baseline-epd', 'epd'):
                    interval = result['intervals'][f'{load}/{system}/throughput']
                    lines.append(f'| {load}/{system} | {mean_sd(metrics(load,system,"off"))} | {mean_sd(metrics(load,system,"lite"))} | {interval["geometric_mean_ratio"]:.4f} [{interval["lower"]:.4f}, {interval["upper"]:.4f}] |')
            labels = [f'{load}/{system}' for load in ('low', 'high') for system in ('baseline-epd', 'epd')]
            for axis, metric, title, margin in zip(axes, ('throughput','ttft_s','tpot_s'), ('Throughput','TTFT P50','TPOT P50'), ((.98,1.02),(.97,1.03),(.97,1.03))):
                axis.axvspan(*margin, color='#d5ebd5', alpha=.7, label='Prespecified equivalence margins')
                for y, label in enumerate(labels):
                    interval=result['intervals'][f'{label}/{metric}']
                    center,low,high=(interval[k] for k in ('geometric_mean_ratio','lower','upper'))
                    axis.errorbar(center,y,xerr=[[center-low],[high-center]],fmt='o',color='#2364aa',capsize=3)
                axis.axvline(1,color='gray',linestyle='--')
                axis.set_yticks(range(4),labels)
                axis.invert_yaxis()
                axis.set_xlabel('lite / off; paired 90% t interval, 6 blocks')
                axis.set_title(title)
            lines += ['', '## 预设等效性判断', '',
                      '| 负载/系统/指标 | 几何均值比 | 90%区间 | 预设界限 | 等效性已证实 |',
                      '|---|---:|---:|---:|---|']
            for name, interval in result['intervals'].items():
                lines.append(f'| {name} | {interval["geometric_mean_ratio"]:.4f} | [{interval["lower"]:.4f}, {interval["upper"]:.4f}] | {interval["margins"]} | {"是" if interval["equivalence_demonstrated"] else "否（含不确定）"} |')
            lines += ['', '图中绿色背景为各指标预设等效性界限。未证实等效可能来自扰动或区间过宽，不能直接称“观察器有实质开销”。所有指标通过也仍需独立正确性及事件关联/覆盖验收，才能辅助解释对应负载；不据此宣称off因果瓶颈已定位。']
        else:
            fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained')
            loads = list('ABCDE')
            lines += ['## 同三卡baseline对照', '',
                      '| 负载 | 三副本 req/s 均值±SD | EPD req/s 均值±SD | 三副本输出 tokens/s 均值±SD | EPD输出 tokens/s 均值±SD | EPD/三副本 几何均值 [95%CI] |',
                      '|---|---:|---:|---:|---:|---:|']
            for x,load in enumerate(loads):
                base=metrics(load,'baseline-epd','off'); epd=metrics(load,'epd','off')
                interval=result['intervals'][load]
                lines.append(f'| {load} | {mean_sd(base)} | {mean_sd(epd)} | {mean_sd(metrics(load,"baseline-epd","off","output_tokens_per_s"))} | {mean_sd(metrics(load,"epd","off","output_tokens_per_s"))} | {interval["geometric_mean_ratio"]:.4f} [{interval["lower"]:.4f}, {interval["upper"]:.4f}] |')
                axes[0].bar(x-.18,statistics.mean(base),width=.36,color='#7e9ebc',label='3 full replicas' if x==0 else None)
                axes[0].bar(x+.18,statistics.mean(epd),width=.36,color='#e5a15b',label='EPD 1:1:1' if x==0 else None)
                center,low,high=(interval[k] for k in ('geometric_mean_ratio','lower','upper'))
                axes[1].errorbar(center,x,xerr=[[center-low],[high-center]],fmt='o',color='#2364aa',capsize=3)
            axes[0].set_xticks(range(5),loads); axes[0].set_ylabel('Successful requests/s, mean of 6 runs')
            axes[0].legend(loc='lower left',bbox_to_anchor=(0,1.01),ncol=2,frameon=False)
            axes[1].set_yticks(range(5),loads); axes[1].invert_yaxis(); axes[1].axvline(1,color='gray',linestyle='--')
            axes[1].set_xlabel('EPD / 3 replicas; paired 95% t interval')
            lines += ['', 'A=1图/128输出/C1；B=4图/128/C8；C=1图/128/C8；D=8图/128/C8；E=8图/32/C8。均值±样本SD为运行描述，配对区间来自六个共同时间区组的对数比，不以请求为独立重复。', '',
                      '## 预设探索对比', '', '| 比值之比 | 几何均值 [95%CI] |', '|---|---:|']
            for name,interval in result['exploratory_contrasts'].items():
                lines.append(f'| {name} | {interval["geometric_mean_ratio"]:.4f} [{interval["lower"]:.4f}, {interval["upper"]:.4f}] |')
            lines += ['', 'D/C增图同时改变视觉token、prefill、KV和batch；E/D缩短输出同时改变驻留。探索对比未作多重比较校正，不预设单调或收益，不将其归因为独占内部阶段因果。']
        if synthetic:
            fig.suptitle('SYNTHETIC TEST ONLY - NOT EXPERIMENT RESULTS',color='#b22222')
        fig.savefig(output/'baseline-comparison.png',dpi=160)
        fig.savefig(output/'baseline-comparison.svg')
        plt.close(fig)
        lines += ['', '![各自baseline对照](baseline-comparison.png)', '', '## 合并请求延迟（仅描述）', '',
                  '| 负载/系统/模式 | 正式请求数 | TTFT P50/P95 ms | TPOT P50/P95 ms | E2E P50/P95 ms |', '|---|---:|---:|---:|---:|']
        for name,item in result['pooled_descriptive_latency'].items():
            values=[f'{item[m]["p50"]*1000:.2f}/{item[m]["p95"]*1000:.2f}' for m in ('ttft_s','tpot_s','latency_s')]
            lines.append(f'| {name} | {item["formal_requests"]} | '+ ' | '.join(values)+' |')
        lines += ['', '## 三卡自有进程采样显存', '',
                  '| 负载/系统/模式 | 六次运行采样峰值的均值±SD GiB | 最大采样值 GiB |', '|---|---:|---:|']
        for load, system, mode in sorted({(c['load'], c['system'], c['mode']) for c in cells}):
            values = [v / 2**30 for v in metrics(load, system, mode, 'sampled_peak_owned_bytes')]
            lines.append(f'| {load}/{system}/{mode} | {mean_sd(values)} | {max(values):.4f} |')
    else:
        lines += ['不生成性能/等效性区间或对照图。所有计划cell继续列出，不能仅筛选完成者计算六区组结论。', '',
                  '| 计划序号 | 区组/负载/系统/模式 | 状态 | 实际记录数 / 记录失败数 |', '|---|---|---|---:|']
        for cell in result['cells']:
            inventory=cell.get('raw_inventory',{})
            lines.append(f'| {cell["schedule_index"]} | {cell["block"]}/{cell["load"]}/{cell["system"]}/{cell["mode"]} | {cell["status"]} | {inventory.get("rows","未知")} / {inventory.get("recorded_failures","未知")} |')
        if phase == 'performance':
            comparable = not result.get('chronology_errors')
            if not comparable:
                lines += ['', '**全局可比性检查失败，以下数值仅供诊断，全部配对比值停止计算。**', '',
                          '错误：' + '；'.join(result['chronology_errors']), '']
            lines += ['', '## 全部计划配对的逐次原始观测', '',
                      '这里只描述已经产生且单元审计通过的运行；未完成矩阵不作合并估计、总体加速结论或CI。单次比值不是六区组结论，缺失项不填零、不筛选有利负载。所有区组/负载均列出；表格排序用于导航，不改变冻结采集顺序。', '',
                      '| 区组/负载 | 三副本 req/s / tokens/s | EPD req/s / tokens/s | 单次EPD/基线 | 基线/EPD状态 |',
                      '|---|---:|---:|---:|---|']
            observed = {(c['block'], c['load'], c['system']): c for c in result['cells']}
            for block in range(6):
                for load in 'ABCDE':
                    base = observed[(block, load, 'baseline-epd')]
                    epd = observed[(block, load, 'epd')]
                    def cell_value(cell):
                        if cell['status'] != 'valid':
                            return '—'
                        m = cell['metrics']
                        return f'{m["requests_per_s"]:.4f} / {m["output_tokens_per_s"]:.2f}'
                    ratio = f'{epd["metrics"]["requests_per_s"] / base["metrics"]["requests_per_s"]:.4f}×' if comparable and base['status'] == epd['status'] == 'valid' else '—'
                    lines.append(f'| {block}/{load} | {cell_value(base)} | {cell_value(epd)} | {ratio} | {base["status"]}/{epd["status"]} |')
        lines += ['', '具体解析错误、阶段完成标记错误、时间/boot冲突及额外目录在analysis.json中完整保留。']
    relative=os.path.relpath(root,output).replace('\\','/')
    lines += ['', '## 原始证据与限制', '', f'[逐cell原始目录]({relative}/results/{phase}) · [配置及代码清单]({relative}/configs) · [G3及运行证据]({relative}/evidence)', '',
              'TTFT为服务端首token时间减客户端提交时间，不含首token回传；TPOT为首末token间隔除以输出数减一。显存为三卡自有进程采样合计，不称连续精确峰值或论文E-worker容量收益。', '',
              '六区组t区间依赖对数配对差近似正态，样本量小；固定并发不是到达率SLO。输入/长度/路由通过不保证全量逐token或语义等价。阶段窗口不能求和成独占GPU成本，也不能从on观测反推off关键路径。失败与退化均保留。', '',
              '本报告需结合实际独立审查、清理及资源释放证据验收；仅保存文件或绘图成功不表示复现完成。', '']
    (output/'report.md').write_bytes('\n'.join(lines).encode('utf-8'))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--phase',choices=('overhead','performance'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    render(args.root.resolve(),args.phase,args.output.resolve())
