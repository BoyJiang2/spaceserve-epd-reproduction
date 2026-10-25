"""Produce the final concise report only after all 30 audited cases exist."""
import argparse
import json
import pathlib


parser = argparse.ArgumentParser()
parser.add_argument("summary", type=pathlib.Path)
parser.add_argument("--output", type=pathlib.Path, required=True)
parser.add_argument("--artifact-root", required=True)
parser.add_argument("--comparison", type=pathlib.Path, required=True)
args = parser.parse_args()
rows = json.loads(args.summary.read_text())
assert len(rows) == 30 and sum(row["requests"] for row in rows) == 9000
assert all(row["failure_rate"] == 0 and row["output_tokens"] == [128] for row in rows)
index = {(row["role"], row["images"], row["concurrency"]): row for row in rows}
root = args.artifact_root.rstrip("/\\").replace("\\", "/")
comparisons = json.loads(args.comparison.read_text())
paired = sum(row["requests"] for row in comparisons)
matched = sum(row["exact_output_token_ids_equal"] for row in comparisons)
assert len(comparisons) == 16 and paired == 4800
comparison_note = ("全部配对输出一致。" if matched == paired else
                   "不同输出的请求索引保存在 output-comparison.json；本轮未逐一判定这些差异的语义质量，不宣称正式请求全部逐 token 等价。")
baseline_variation = sum(row["baseline_repeated_input_variation"]["with_multiple_outputs"] > 0 for row in comparisons)
if baseline_variation:
    comparison_note += f"配对配置中有 {baseline_variation} 组的原生基线对重复相同输入也产生过不同输出；这说明完全匹配率还受重复运行变动影响，但不能据此直接判定所有目标差异的原因。"
comparison_lines = ["| 目标 | 配对请求 | 输出 IDs 完全匹配 |", "|---|---:|---:|"]
for target in sorted({row["target"] for row in comparisons}):
    group = [row for row in comparisons if row["target"] == target]
    total = sum(row["requests"] for row in group)
    exact = sum(row["exact_output_token_ids_equal"] for row in group)
    comparison_lines.append(f"| {target} | {total} | {exact}（{exact / total:.1%}） |")


def table(baseline, target):
    lines = ["| 图数 | 并发 | 基线 tokens/s | 目标 tokens/s | 吞吐比 | TTFT P95 ms：基线→目标 | TPOT P95 ms：基线→目标 |",
             "|---:|---:|---:|---:|---:|---:|---:|"]
    for images in (1, 4):
        for concurrency in (1, 4, 8):
            a, b = index[baseline, images, concurrency], index[target, images, concurrency]
            lines.append(f"| {images} | {concurrency} | {a['output_tokens_per_s_mean']:.1f} ± {a['output_tokens_per_s_sd']:.1f} | "
                         f"{b['output_tokens_per_s_mean']:.1f} ± {b['output_tokens_per_s_sd']:.1f} | "
                         f"{b['output_tokens_per_s_mean'] / a['output_tokens_per_s_mean']:.2f}× | "
                         f"{a['ttft_p95_ms']:.1f} → {b['ttft_p95_ms']:.1f} | {a['tpot_p95_ms']:.2f} → {b['tpot_p95_ms']:.2f} |")
    return "\n".join(lines)


def range_text(baseline, target):
    ratios = [index[target, images, concurrency]["output_tokens_per_s_mean"] / index[baseline, images, concurrency]["output_tokens_per_s_mean"]
              for images in (1, 4) for concurrency in (1, 4, 8)]
    wins = sum(value > 1 for value in ratios)
    return f"六个配置中，目标吞吐高于基线的有 {wins} 个；吞吐比范围 {min(ratios):.2f}–{max(ratios):.2f}×。"


memory_lines = ["| 配置 | 分配 GPU 数 | 各负载点的采样峰值范围 GiB（分配 GPU 合计） |", "|---|---:|---:|"]
for role in sorted({row["role"] for row in rows}):
    group = [row for row in rows if row["role"] == role]
    values = [row["sampled_physical_memory_peak_gib"] for row in group]
    memory_lines.append(f"| {role} | {group[0]['assigned_gpu_count']} | {min(values):.2f}–{max(values):.2f} |")

l20_lines = ["| 图数 / 并发 | vLLM tokens/s | SpaceServe tokens/s | SpaceServe + mask tokens/s |", "|---|---:|---:|---:|"]
for images, concurrency in [(1, 1), (4, 8)]:
    values = [index[role, images, concurrency] for role in ["baseline-space-l20-mps", "space-l20-mps", "space-mask-l20-mps"]]
    formatted = [f"{row['output_tokens_per_s_mean']:.1f} ± {row['output_tokens_per_s_sd']:.1f}" for row in values]
    l20_lines.append(f"| {images} / {concurrency} | " + " | ".join(formatted) + " |")
l20_high = [index[role, 4, 8] for role in ["baseline-space-l20-mps", "space-l20-mps", "space-mask-l20-mps"]]
l20_tradeoff = (f"4 图 / 并发 8 时，解耦及 mask 的吞吐分别为基线的 "
                f"{l20_high[1]['output_tokens_per_s_mean'] / l20_high[0]['output_tokens_per_s_mean']:.2f}× 和 "
                f"{l20_high[2]['output_tokens_per_s_mean'] / l20_high[0]['output_tokens_per_s_mean']:.2f}×；"
                f"TTFT P95 则从 {l20_high[0]['ttft_p95_ms']:.1f} ms 变为 "
                f"{l20_high[1]['ttft_p95_ms']:.1f} / {l20_high[2]['ttft_p95_ms']:.1f} ms。吞吐与首 token 延迟需同时评估。")

stage_lines = ["| 图数 / 并发 | 编码 ms | Prefill ms | embedding 迁移 ms | KV 迁移 ms |", "|---|---:|---:|---:|---:|"]
epd_rows = [row for row in rows if row["role"] == "epd-l20"]
transfers = [row["embedding_migration_ms_median"] + row["kv_migration_ms_median"] for row in epd_rows]
stage_interpretation = (f"历史记录中，两个迁移接口的中位数之和约 {min(transfers):.1f}–{max(transfers):.1f} ms，"
                        "但原操作使用异步 CUDA copy，接口返回不能证明 GPU 拷贝完成。"
                        "原始 KV 探针后续测到 CPU 提交约 2–3 ms、GPU 完成约 59 秒且数据错误，"
                        "因此不能据上述接口事件认定通信开销很小。重启慢实例约 23 秒主要集中于首、次 token 的间隔，"
                        "后续 token 仍约 22 ms；平均 TPOT 不能单独定位逐步解码计算瓶颈。")
for images in (1, 4):
    for concurrency in (1, 4, 8):
        row = index["epd-l20", images, concurrency]
        stage_lines.append(f"| {images} / {concurrency} | {row['encoding_ms_median']:.2f} | {row['prefill_ms_median']:.2f} | "
                           f"{row['embedding_migration_ms_median']:.2f} | {row['kv_migration_ms_median']:.2f} |")

report = f"""# SpaceServe / EPD 小规模复现报告

日期：2026-10-23。完成 30 个配置、9,000 条正式请求和 600 条预热请求；HTTP 与数据格式审计通过，均实际生成 128 tokens。后续发现 CUDA P2P 数据损坏，已将其中 1,800 条 EPD 请求降级为诊断记录，不能作为可靠性能结论；其余 7,200 条同卡或独立副本测量保留。每个矩阵的有效性标记在 `validity.json`，完整目标仍未完成。

验收结论：SpaceServe 解耦及并发机制跑通，SM mask 在 L20 验证通过、4090 未通过。EPD 的原始 KV copy 和独立 CUDA Runtime copy 均出现数据不一致，**跨卡通信一致性与稳定复跑验收未通过**。sapphire3 的八张 GPU 均处于裸机 IOMMU `DMA-FQ` 域，属于 NVIDIA 不支持的 PCIe P2P 配置；最终因果还需管理员调整后重测。维护或换机方案见 `report/host-maintenance-proposal.md`。

## SpaceServe：4090 同卡对照

固定 SpaceServe `66de079af423`，原生 vLLM 0.7.2；Qwen2-VL-2B-Instruct、FP16、TP=1、eager。基线和目标都启用限定 GPU 的 CUDA MPS，在同一张 4090 顺序测试。

{range_text('baseline-space-4090-mps', 'space-4090-mps')}

{table('baseline-space-4090-mps', 'space-4090-mps')}

![SpaceServe 4090 吞吐和延迟对照]({root}/report/spaceserve-4090.png)

## EPD：L20 三卡预算对照

固定 EPDServe `9b111f710dfb`，vLLM 0.6.1.post2；MiniCPM-V-2_6、FP16、TP=1。EPD 为 E:P:D=1:1:1，关闭 IRP 和动态角色切换；基线在同三张 GPU 上部署三个完整模型副本，客户端轮询分发。

以下仅为历史诊断记录。由于后续独立探针确认 P2P 数据损坏，该组数据不能用来回答 EPD 是否加速，也不能把差距归因于调度算法。原始数据保留用于追溯，CSV 和图均标记 `diagnostic_only`。

历史观测吞吐比为 0.87–0.93×，已撤回其性能结论效力，等待有效传输环境下重新完成公平对照。

{table('baseline-epd-l20', 'epd-l20')}

![EPD L20 吞吐和延迟对照]({root}/report/epd-l20.png)

EPD 自带阶段事件的历史中位耗时如下。这些是接口跨度，部分只记录异步提交，不能作为实际 GPU 完成时间或 PCIe 带宽；原日志的 decoding_begin 会被后续迭代覆盖，未用它推断排队时间。

{chr(10).join(stage_lines)}

{stage_interpretation}

## L20 的 SpaceServe 趋势与 SM mask

在同一张 L20 顺序运行基线、解耦以及静态编码器 mask 两个负载点，均启用 MPS。每点同样预热 20、测量 100、重复 3 次。

{chr(10).join(l20_lines)}

{l20_tradeoff}

![L20 SpaceServe 验证]({root}/report/spaceserve-l20.png)

## 机制与正确性

- 4090 跨卡 CUDA IPC 实测错误 217，EPD 按预定分支转 L20。早期 L20 探针只检查 IPC 指针导入后的 D2H 读取，不覆盖跨 GPU D2D DMA，不能据此判定 EPD 传输通过。
- 4090 和 L20 的双进程 CUDA 时间线均记录到编码与解码 kernel 重叠，原始 trace 和时钟对齐统计在 evidence 中。Profiler 工作负载不参与正式性能统计。
- L20 原生与 MPS 环境均实测编码器 mask 将运行 kernel 的 SM 数由 92 降到 68。4090 的驱动暴露 CUDA Driver API 13.0，当前 libsmctrl 不支持；4090 SM mask 标为未完成。
- EPD 的 7 组单图、多图和并发检查与完整模型基线的 output token IDs 一致；SpaceServe 真实图片并发路由通过，目标与基线的 token IDs 对照保存在证据文件中。
- 另外单独执行 8 并发路由检查，覆盖不同图片同时到达；正确性检查与正式压测分开运行，使用保存的完整模型参考输出。
- Qwen2-VL-2B 的多图语义描述仍可能出错，部分诊断中纯色图片也不适合作路由 oracle；原始基线和目标结果均保留。服务等价性检查不表示模型语义质量全部通过。

![L20 编码与解码 CUDA kernel 的重叠窗口]({root}/report/kernel-overlap-l20-mask.png)

EPD 的额外冷启动检查发现失败：新服务不做应用预热，直接并发提交 8 个 32-token 纯色图请求时，批次在 120 秒内未完成，解码 GPU 保持忙碌。此项不在正式 128-token 矩阵内，但构成可靠性限制；原因尚未定位，未改写通信层。客户端、服务端日志和复现条件保存在 `evidence/sapphire3/epd-cold-c8-failure.json` 及对应 logs 中，不能宣称冷启动并发已通过。

再次重启后的顺序预热还出现约 26 秒/请求的退化，明显慢于正式服务实例约 3 秒/请求。已核对 CLI、代码版本、GPU、缓存块数及主要环境配置，未找到明确原因。重启诊断原始请求单独保存，不混入正式矩阵；前述 EPD 倍率仅代表已完成测量的该服务实例，尚未证明跨重启稳定重现。扩大实验前应先定位这个问题。

20 次顺序预热及 1 次诊断请求都实际完成后，重试 8 个 32-token 请求仍在 120 秒超时，说明本次预热未消除此问题。44 个专门样例的服务级对照通过，包含 3 个基线和目标均未通过多图语义 oracle、但输出 IDs 相同的 Qwen 样例；不能将它们计为语义质量通过。EPD 的新增冷、暖两次 8 并发检查未通过，均保留失败材料。正式 128-token 矩阵的 0% HTTP 失败率不适用于这些额外检查。

另外保存了退化实例的 4 个解码步短 trace、核名耗时分析和临时 profiling 补丁；它们只用于诊断，不能据短窗口定位整次请求的退化原因。采集后已恢复原 worker 源码，未改变正式矩阵采用的通信或调度实现。

进一步定位得到独立反例：纯 CUDA Runtime `cudaMemcpyPeer` 在 0→1 和 1→2 上均返回成功且宣称 P2P 支持，但已校验的 1 MiB 源数据复制后变成 `ff`；原始 KV 操作在 2048/24728 blocks 两种缓存形状上均约 59 秒完成且校验失败。完整 JSON、源/目标 SHA256 和代码保存在 `evidence/sapphire3`。这已把故障缩小到 EPD 以外的 CUDA PCIe P2P 层，不能靠修改 Ray 启动时序掩盖。

启动脚本现会拒绝在已知不支持的裸机 DMA IOMMU 域上启动 EPD，避免继续产出看似成功的无效结果。当前未修改主机内核、GRUB、驱动或 ACS；需要管理员维护或更换环境后重新验证。NVIDIA 的官方限制见 [CUDA 12.4 文档](https://docs.nvidia.com/cuda/archive/12.4.1/pdf/CUDA_C_Programming_Guide.pdf)及 [NCCL 故障排查](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/troubleshooting/gpu_troubleshooting.html)。

正式请求另做离线配对：16 组配置、{paired:,} 对请求的图片顺序和处理后输入 IDs 相同，其中 {matched:,} 对输出 token IDs 完全相同。{comparison_note}

{chr(10).join(comparison_lines)}

## 显存、收益与限制

{chr(10).join(memory_lines)}

显存取 NVML 在测量及预热期间的物理使用量采样峰值，按分配 GPU 合计；实际采样间隔见 summary.csv。进程归属另存于原始日志，包含本实验 MPS 服务进程。缓存预算和阶段模型保留方式影响此值，不能直接解释为纯权重大小。

本轮视觉输入为 448×448 的 1/4 张图片，生成长度为 128。三卡 EPD 只有一张卡执行解码，而三副本基线有三张卡执行完整模型，这会影响资源平衡；但在传输校验失败的环境中，不能定量归因其收益或退化。原公开 EPD worker 中删除无关阶段模型的代码被注释，本轮保留原行为；表中 EPD 显存也仅为历史进程观测。

SpaceServe 固定公开分支采用 FIFO 编码调度和静态编码器 mask，解码器 mask 调用被注释；本轮未补写论文完整 SIS/TWSRFT。因此应按公开实现的缩小机制实验解释结果。4090/L20 的显存、带宽与互连均不同于论文 A100，倍率不外推。

## 测量口径与材料

固定 20 张 COCO 图片，RGB、448×448、相同提示词和请求序列。固定并发闭环测试，不作 SLO attainment 或真实到达率结论。吞吐为三次独立测量均值 ± 样本标准差；P50/P95 在 300 条正式请求上合并计算。TTFT 使用同机服务端首 token 时间减客户端提交时间，不含首 token 网络返回开销；TPOT 为首末 token 时间差除以 127；端到端延迟使用完整 HTTP 往返。

机器是共享主机，其他 GPU 上已有任务保留运行；本实验使用单独确认可用的 GPU，未锁定 GPU 时钟。重复间波动因此一并报告，不将小于波动量的差别解释为稳定收益。L20 只验证低、高两个负载点，不能推出完整负载曲线。

详细 P50/P95、失败率、显存和重复波动见 report/summary.csv；原始请求、GPU 采样、运行配置与独立审计见 data/raw；代码、补丁、模型哈希及环境锁定见 scripts、patches、configs。初期 0.7.3 与失败预检数据已排除。EPD 原矩阵的测量后标记遇到脚本解析错误，独立审计确认六格数据完整后补写标记；未改动已完成的测量值。

当前需要管理员提供支持的数据传输环境：维护 sapphire3 关闭 IOMMU DMA 翻译后重测，或使用另一套通过 P2P 数据校验的三卡主机。随后重跑 EPD 及同次启动状态下的三副本基线，再考虑 PD 基线。SpaceServe 可在后续扩大视觉负载或使用 Qwen2-VL-7B；当前完整目标仍保持进行中。没有跨机部署或通信层重写。

来源：[SpaceServe 论文](https://papers.nips.cc/paper_files/paper/2025/file/720e7ebc49c84252abc0754dddf80976-Paper-Conference.pdf)、[EPD 论文](https://proceedings.mlr.press/v267/singh25d.html)、两篇官方固定版本代码及本目录实测数据。
"""
args.output.write_text(report, encoding="utf-8")
print(args.output)
