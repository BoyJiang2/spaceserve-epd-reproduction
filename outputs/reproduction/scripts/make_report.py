"""Generate the combined report after both H20 acceptance chains pass."""
import argparse
import json
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument('root', type=pathlib.Path)
args = parser.parse_args()
root = args.root.resolve()
rows = json.loads((root / 'report/summary.json').read_text())
acceptance = json.loads((root / 'report/h20-acceptance.json').read_text())
cache_fix = json.loads((root / 'report/cache-fix-acceptance.json').read_text())
comparisons = json.loads((root / 'report/output-comparison.json').read_text())
review_state = json.loads((root / 'report/experiment-status.json').read_text())['independent_review']
review_gates = '；'.join(f'{gate}：{value}' for gate, value in review_state['gates'].items())
assert len(rows) == 46 and sum(row['requests'] for row in rows) == 13800
assert len(acceptance) == 2 and all(item['passed'] for item in acceptance)
assert sum(item['formal_requests'] for item in acceptance) == 4800
assert all(item['passed'] for item in cache_fix) and sum(item['formal_requests'] for item in cache_fix) == 1200
assert len(comparisons) == 24 and sum(item['requests'] for item in comparisons) == 7200
cache_pairs = [item for item in comparisons if item['source_kind'] == 'cache-fix']
assert len(cache_pairs) == 2 and {(item['target'], item['case']) for item in cache_pairs} == {('epd-h20', 'images1-c1'), ('epd-h20-qjh005', 'images1-c1')}
assert all(row['result_validity'] == ('diagnostic_only' if row['role'] == 'epd-l20' else 'measurement_valid') for row in rows)
assert all(row['source_kind'] == 'cache-fix' for row in rows if row['role'].startswith(('epd-h20', 'baseline-epd-h20')) and (row['images'], row['concurrency']) == (1, 1))
index = {(row['role'], row['images'], row['concurrency']): row for row in rows}


def table(baseline, target):
    lines = ['| 图数 / 并发 | 基线 tokens/s | 目标 tokens/s | 吞吐比 | TTFT P95 ms：基线→目标 | TPOT P95 ms：基线→目标 | E2E P95 ms：基线→目标 |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for b in sorted((row for row in rows if row['role'] == target), key=lambda row: (row['images'], row['concurrency'])):
        a = index[baseline, b['images'], b['concurrency']]
        ratio = b['output_tokens_per_s_mean'] / a['output_tokens_per_s_mean']
        mark = ' †' if target.startswith('epd-h20') and (b['images'], b['concurrency']) == (1, 1) else ''
        lines.append(f"| {b['images']} / {b['concurrency']}{mark} | {a['output_tokens_per_s_mean']:.1f} ± {a['output_tokens_per_s_sd']:.1f} | {b['output_tokens_per_s_mean']:.1f} ± {b['output_tokens_per_s_sd']:.1f} | {ratio:.2f}× | {a['ttft_p95_ms']:.1f}→{b['ttft_p95_ms']:.1f} | {a['tpot_p95_ms']:.2f}→{b['tpot_p95_ms']:.2f} | {a['latency_p95_ms']:.1f}→{b['latency_p95_ms']:.1f} |")
    if target.startswith('epd-h20'):
        lines.extend(['', '† 此行为统一RGB缓存初态后的成对补测；原低负载数据保留在原目录，并明确标为已替代。'])
    return '\n'.join(lines)


def ratio_text(baseline, target):
    ratios = [row['output_tokens_per_s_mean'] / index[baseline, row['images'], row['concurrency']]['output_tokens_per_s_mean'] for row in rows if row['role'] == target]
    return f"吞吐比为 {min(ratios):.2f}–{max(ratios):.2f}×；{len(ratios)} 个配置中有 {sum(value > 1 for value in ratios)} 个高于基线。"


def image(name, alt):
    return f'![{alt}]({(root / "report" / name).as_posix()})'


memory = ['| 角色 | 分配 GPU | 合计物理显存采样峰值 GiB（配置范围） | 正式请求失败率 |', '|---|---:|---:|---:|']
for role in sorted({row['role'] for row in rows if row['role'] != 'epd-l20'}):
    group = [row for row in rows if row['role'] == role]
    peaks = [row['sampled_physical_memory_peak_gib'] for row in group]
    memory.append(f"| {role} | {group[0]['assigned_gpu_count']} | {min(peaks):.2f}–{max(peaks):.2f} | {max(row['failure_rate'] for row in group):.1%} |")
matched = sum(row['exact_output_token_ids_equal'] for row in comparisons)
valid_pairs = [row for row in comparisons if row['target'] != 'epd-l20']
valid_matched = sum(row['exact_output_token_ids_equal'] for row in valid_pairs)
assert sum(row['requests'] for row in valid_pairs) == 5400
matches = ['| 目标 | 配对请求 | 输出 token IDs 完全匹配 |', '|---|---:|---:|']
for target in sorted({row['target'] for row in comparisons}):
    group = [row for row in comparisons if row['target'] == target]
    count = sum(row['requests'] for row in group)
    same = sum(row['exact_output_token_ids_equal'] for row in group)
    label = target + ('（仅诊断）' if target == 'epd-l20' else '')
    matches.append(f'| {label} | {count} | {same}（{same / count:.1%}） |')
directions = []
for images, concurrency in ((1, 1), (4, 8)):
    ratios = [index[target, images, concurrency]['output_tokens_per_s_mean'] / index[baseline, images, concurrency]['output_tokens_per_s_mean'] for baseline, target in [('baseline-epd-h20', 'epd-h20'), ('baseline-epd-h20-qjh005', 'epd-h20-qjh005')]]
    agreement = '收益/退化方向一致' if (ratios[0] > 1) == (ratios[1] > 1) else '收益/退化方向不同，需要更多重复才能判断稳定性'
    directions.append(f"{images} 图、并发 {concurrency}：qjh003 为 {ratios[0]:.2f}×，qjh005 为 {ratios[1]:.2f}×，{agreement}。")

report = f'''# SpaceServe / EPD 小规模复现报告

Claude额度耗尽后，用户授权独立subagent接替审查，实际审查者与结论分别归档，历史失败记录保留。当前Gate状态：{review_gates}。首单图配置已完成统一RGB初态的成对补测，数据技术审计通过；最终验收以Gate结论为准。审查安排见reviews/prompts/subagent-handoff-20261023.md，处理记录见reviews/review-followup-20261023.md。

本轮已完成双H20的EPD测量与同机三卡预算对照，并合并已有SpaceServe 4090/L20结果。H20最终选用16个配置、4,800条正式请求和320条矩阵内预热；每配置均预热20请求、正式100请求重复三次，实际输出均为128 token IDs。

归档共50个配置、15,000条正式请求与1,000条矩阵内预热。报告选用46个配置、13,800条正式请求：其中1,800条旧sapphire3 EPD仅诊断，12,000条有效测量参与性能结论。另有1,200条旧H20低负载请求因RGB缓存初态不一致被补测替代，原始数据完整保留，不参与最终性能汇总。补测本身新增4配置、1,200条正式请求与80条预热；没有删去首次重复或改变全局20推理预热/100正式×3。专门的启动与正确性请求不计入压测数量。

## EPD：qjh003 主测

qjh003 为 8×H20（约 96GB/卡）、NVLink、驱动 580.126.20；使用同一 NUMA 域的 GPU 0/1/2。EPDServe 固定 `9b111f710dfb4724072b603d626a1e4dad93ef1f`，MiniCPM-V-2_6、FP16、TP=1、E:P:D=1:1:1，关闭 IRP 和动态角色切换。基线为同机、同三张卡上的三个完整模型副本，客户端轮询分发。

{ratio_text('baseline-epd-h20', 'epd-h20')}

{table('baseline-epd-h20', 'epd-h20')}

{image('epd-h20.png', 'qjh003 EPD 吞吐与延迟对照')}

## EPD：qjh005 独立趋势验证

qjh005 的 GPU 型号、卡容量、NVLink 拓扑和驱动与 qjh003 相同，独立使用本机 GPU 0/1/2；模型、依赖及参数相同，同样与本机三副本比较。两台各自运行完整单机链路，没有跨机拆分 E/P/D。归档目录的 `-qjh005` 后缀仅用于区分来源，原始配置保留实际路径。

{table('baseline-epd-h20-qjh005', 'epd-h20-qjh005')}

{' '.join(directions)} qjh005 只测低、高两个点，不能据此推出完整负载曲线。

{image('epd-h20-qjh005.png', 'qjh005 低高负载对照')}

## 机制、兼容性与正确性

两台的六个相关方向均通过16MiB纯CUDA P2P完整哈希校验。原始KV IPC操作在2048/24728 blocks两种缓存分配形状、六个方向、各三次复制中共通过72次；另按每台实际服务日志的60553 blocks分配规模补测P→D，共六次。每次实际传输18 blocks、约15.75MiB，并非复制整个60553-block缓存，已传元素全部比较一致。原始embedding IPC在每台E→P复制四张图的embedding，连续三次均一致。记录包含源验证、目标验证及CUDA event完成时间；API返回成功本身不作为通过标准。探针在block/image内使用常数模式，单凭探针不能排除所有维度置换，固定端到端用例提供补充证据。

旧 cuBLAS 12.1.3.1 可在 H20 上独立复现 FP16 线性层 SIGFPE，GDB 栈位于 libcublasLt 算法选择。仅将隔离环境的 cuBLAS 更新至 12.4.5.8 后，两台各四组矩阵乘法数值校验通过。PyTorch 2.4.0+cu121、vLLM 0.6.1.post2、Transformers 4.44.2 保持原版本；这是明确的局部兼容覆盖，PyTorch 包元数据仍声明其旧 cuBLAS 依赖。EPD 和基线使用同一覆盖版本，实际 GPU 进程已加载的库路径另有快照。NVIDIA 在 CUDA 12.4 Update 1 说明中记录了 Hopper FPE 修复。[官方说明](https://docs.nvidia.com/cuda/archive/12.4.1/cuda-toolkit-release-notes/index.html#cublas-release-12-4-update-1)

原H20机制验收每台45个服务对照用例，共90个通过：包括完整模型参考、8并发参考、EPD首次启动及一次服务重启后的单图/多图与8并发路由。补测另每台30个用例，共60个通过，覆盖EPD及基线首端点；其余两个基线副本分别做RGB缓存校验和正式请求检查，不称三个副本各自完成独立C8正确性测试。处理后输入IDs、输出token IDs与参考均相同，固定颜色顺序及并发隔离检查通过。原始C++通信操作保持官方代码；必要Python修改包括多图读取修复、IRP参数转发、输出IDs及纯RGB缓存预载/元数据校验。此审查不是native二进制的独立重建认证。

## SpaceServe：已有同卡实验

SpaceServe 固定 `66de079af4234b27f7f82ff91d238ef1351324ba`，对应原生 vLLM 0.7.2；Qwen2-VL-2B-Instruct、FP16、TP=1、eager。基线与目标均使用限定单卡的 CUDA MPS。同一张 4090 上的结果如下。

{ratio_text('baseline-space-4090-mps', 'space-4090-mps')}

{table('baseline-space-4090-mps', 'space-4090-mps')}

{image('spaceserve-4090.png', 'SpaceServe 4090 同卡对照')}

L20 的低、高负载点：

{table('baseline-space-l20-mps', 'space-l20-mps')}

启用编码器 SM mask：

{table('baseline-space-l20-mps', 'space-mask-l20-mps')}

{image('spaceserve-l20.png', 'SpaceServe L20 趋势验证')}

独立 CUDA trace 观察到编码与解码 kernel 重叠；L20 的编码器 mask 将实际使用 SM 从 92 降为 68，4090 的当前 libsmctrl/驱动组合拒绝该能力。固定公开分支只对编码器施加静态 mask，解码器 mask 被注释，采用 FIFO 编码调度；没有补写论文完整 SIS/TWSRFT。因而这里报告公开实现的缩小机制试验，4090 不宣称 SM 划分成功。详细 CUDA 时间线与证据沿用 sapphire 阶段材料。

## 显存和输出对照

{chr(10).join(memory)}

显存为 NVML 按分配 GPU 合计的物理使用量采样峰值，涵盖矩阵内预热与正式请求，目标采样周期 100ms，实际间隔保存在 summary.csv；它不是绝对瞬时峰值，也不等于纯权重大小。EPD 的公开 worker 保留无关阶段模型的原行为，缓存与模型保留方式均会影响显存。相同 GPU 数是本轮资源预算口径，不能据同一个 gpu-memory-utilization 参数推断两组实际显存相等。

有效测量中的正式请求离线配对共 5,400 对，图片顺序和处理后输入 IDs 相同，其中 {valid_matched:,} 对输出 token IDs 完全相同。另保留旧 L20 EPD 的 1,800 对诊断；含诊断合计 7,200 对、{matched:,} 对输出完全匹配。差异索引与基线重复同输入的输出变动均保存在 report/output-comparison.json；未逐一评估这些差异的语义质量，不宣称正式输出全部等价。诊断配对不参与有效结果的匹配率。

{chr(10).join(matches)}

既有sapphire阶段服务对照另有44个用例（37个SpaceServe、7个历史EPD）；其中三个Qwen多图样例的基线与目标都未通过语义oracle，但token IDs相同，只计为服务等价性检查，不计为语义质量通过。历史EPD仍受后续数据损坏诊断限制。H20原验收90个加补测60个固定用例与正式请求离线配对属于不同验证范围。

## 结果解释与边界

本轮每张 MiniCPM 图片只有 64 个视觉 token，单请求为 1/4 张图、生成 128 tokens。E/P/D 静态分工中只有一张卡解码，而三副本基线可以在三张卡上执行完整请求；编码负载、解码批量效率、Ray 调度和逐块通信提交都会影响收益。表中的吞吐及延迟共同决定是否值得采用，不能只选有利指标，也不能仅凭阶段接口耗时定量归因。

阶段日志中的迁移事件可能只记录异步 CPU 提交；GPU 完成时间以独立 native 探针为准，不将接口跨度解释为 NVLink 峰值带宽。跨机部署、通信层重写、动态角色切换、自动资源搜索、PD 基线及完整消融均未纳入本轮。

sapphire3 的历史 EPD 请求虽曾完成 HTTP 返回，但后续独立 CUDA P2P 与原始 KV 操作均发现数据损坏，其裸机 GPU IOMMU 域为 DMA-FQ；未做维护前后对照，不能据此证明唯一原因是 IOMMU。已撤回这组数据的性能效力，未改系统启动参数或重启主机；当前改用经过数据校验的 H20。历史原始数据、失败日志和维护建议均保留在 evidence/sapphire3、data/raw/sapphire3 及 report/sapphire-stage-report.md。

下一轮先围绕当前退化点做阶段 GPU profiling 和 PD 基线，区分解码资源分配、批量效率与调度开销；再根据视觉负载是否足够，选择扩大图片数量/分辨率或模型。当前小模型与固定并发结果不足以外推论文 A100 的倍率，也不能代表真实到达率下的 SLO 达标率。

## 测量和复跑

固定20张COCO图片，RGB、448×448，相同提示词和请求序列，已检查的两组接口层均缓存RGB图片。每配置全局20请求预热，正式100请求重复三次，temperature=0、ignore_eos=True，实际生成128 token IDs；token计数包含特殊token。吞吐为三次均值±样本标准差；P50/P95在300条正式请求上合并计算。未作统计显著性检验，小于重复波动的差别谨慎解释。

历史H20首单图/C1的20条全局预热曾使EPD覆盖20张COCO图片、三个基线副本只覆盖7/7/6张；未测首次RGB加载的额外耗时，不能据此定量归因。经G1/G2独立审查，在双方各服务启动阶段只预载同20张RGB对象，不执行模型前向、不新增推理预热请求，再对两台该点成对补测。补测前后，通过只读接口从实际缓存对象取得mode、尺寸和像素SHA；每个EPD端点及全部三个基线副本均与独立源图解码结果一致，共16份服务快照、320张图片对象校验。服务PID前后相同，GPU UUID、运行库、启动boot ID均有记录。根据持续运行脚本、稳定GPU worker PID及无淘汰字典，推演原后续负载的RGB覆盖持续填满；这不是直接缓存命中率测量，也不能排除所有API状态变化。G4据此认可保留其余负载，无需扩大补测。证据见data/cache-fix/、report/cache-fix-acceptance.json、report/h20-cache-continuity.json与reviews/subagent-g4-cache-fix-data-20261023.md。

TTFT 为同机服务端首 token 时间减客户端提交时间，不含首 token 网络返回开销；接口本轮非流式返回。TPOT 为首末 token 时间差除以 127；端到端延迟为完整 HTTP 往返。共享主机未锁定 GPU 时钟，每次启动前检查可用卡，不终止他人任务。

复跑见 README.md；完整配置、依赖与权重哈希见 configs/ 和各主机 evidence/；逐请求结果、GPU 采样及运行配置见 data/raw/。summary.csv 包含完整 P50/P95、失败率、显存和三次重复值。h20-acceptance.json、delivery-audit.json 和 completion-audit.md 给出分项验收证据；SHA256SUMS 与归档 CRC 用于材料完整性校验。
'''
(root / 'report.md').write_text(report, encoding='utf-8')
print(root / 'report.md')
