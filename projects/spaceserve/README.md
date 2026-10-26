# SpaceServe 复现项目

[返回项目总入口](../../README.md) · [English overview](../../README.en.md#spaceserve) · [论文覆盖](../../PAPER_VS_REPRO.md) · [补丁审计](../../PATCH_AUDIT.md)

本项目研究同卡编码器与语言模型的解耦、并发及encoder stream SM mask。最新测量为qjh000单H20、Qwen2-VL-7B-Instruct、FP16/TP1/eager，3组18配置、5400正式＋360预热；旧4090/L20、2B结果另列。

仅覆盖固定公开实现子集，未复现完整SIS/TWSRFT或decoder互斥分区。LM仍保留visual权重，另有encoder驻留；所有自有GPU进程显存合计计入。本页全部性能对照属于SpaceServe，不与EPD的三卡预算或模型作绝对排名。

## 最新SpaceServe：直接与原生vLLM比较

同qjh000单H20、7B、同请求序列。吞吐为三重复均值±样本SD（req/s）；比值用未四舍五入均值计算。

| 图/C | 原生vLLM | 解耦 | 解耦/原生变化 | encoder mask | mask/原生变化 |
|---|---:|---:|---:|---:|---:|
| 1/1 | 0.4457 ± 0.0002 | 0.4514 ± 0.0005 | +1.29% | 0.4489 ± 0.0006 | +0.72% |
| 1/4 | 1.7749 ± 0.0036 | 1.7713 ± 0.0141 | -0.20% | 1.6415 ± 0.0014 | -7.52% |
| 1/8 | 3.1360 ± 0.0067 | 3.1226 ± 0.0218 | -0.43% | 2.9047 ± 0.0166 | -7.38% |
| 4/1 | 0.4112 ± 0.0001 | 0.3852 ± 0.0005 | -6.32% | 0.3810 ± 0.0008 | -7.35% |
| 4/4 | 1.3313 ± 0.0033 | 1.3328 ± 0.0035 | +0.12% | 1.2937 ± 0.0112 | -2.82% |
| 4/8 | 2.0138 ± 0.0067 | 2.1318 ± 0.0114 | +5.86% | 2.1404 ± 0.0046 | +6.29% |

延迟不能只看吞吐。下表为TTFT / TPOT P50（ms），P50合并300条正式请求计算；TTFT为服务端首token时间减客户端提交时间，不含首token回传。E2E P50/P95和采样显存完整保留于报告。

| 图/C | 原生 TTFT / TPOT | 解耦 TTFT / TPOT | mask TTFT / TPOT |
|---|---:|---:|---:|
| 1/1 | 107.77 / 16.74 | 131.80 / 16.35 | 132.72 / 16.44 |
| 1/4 | 265.99 / 15.81 | 209.18 / 16.10 | 218.99 / 17.41 |
| 1/8 | 449.86 / 15.88 | 262.13 / 17.53 | 281.65 / 18.69 |
| 4/1 | 356.43 / 16.29 | 497.32 / 16.52 | 485.93 / 16.78 |
| 4/4 | 705.58 / 18.05 | 712.08 / 18.35 | 617.89 / 19.37 |
| 4/8 | 1434.21 / 19.27 | 825.88 / 22.03 | 818.67 / 22.21 |

### 观察到的指标权衡

![历史六负载相对原生vLLM的变化](../../docs/revision/space-relative.png)

百分比为`100×(实验组/原生−1)`，吞吐越高越好，延迟越低越好。吞吐使用三次运行均值，TTFT/TPOT使用300正式请求合并P50；图中没有将请求当独立运行计算置信区间。三次运行值、样本SD和37项源SHA见[派生数据](../../docs/revision/space-relative.json)，[CPU重算入口](../../scripts/revision/compare_existing_space.py)验证原始记录与封存统计一致。4图/C8解耦组表现为TTFT降低42.42%、TPOT增加14.37%、吞吐增加5.86%，是观察到的权衡，不是排队时间转移的证明。固定顺序与时间漂移限制保留。

## 历史4090/L20：各自与原生vLLM比较

以下沿用首轮报告原表：tokens/s为128输出token条件下三次运行均值±样本SD。每配置20请求预热，100正式请求重复三次；与最新7B/H20批次分开展示。

### sapphire1，Qwen2-VL-2B，单4090原生 vs 解耦

| 图数 / 并发 | 基线 tokens/s | 目标 tokens/s | 吞吐比 | TTFT P95 ms：基线→目标 | TPOT P95 ms：基线→目标 | E2E P95 ms：基线→目标 |
|---|---:|---:|---:|---:|---:|---:|
| 1 / 1 | 69.8 ± 0.5 | 68.3 ± 1.1 | 0.98× | 90.1→106.0 | 17.01→16.92 | 2240.2→2243.8 |
| 1 / 4 | 252.7 ± 10.1 | 262.2 ± 5.2 | 1.04× | 158.9→114.2 | 18.05→17.42 | 2424.6→2304.3 |
| 1 / 8 | 462.6 ± 12.5 | 477.2 ± 6.1 | 1.03× | 253.1→187.7 | 18.48→18.15 | 2530.8→2420.7 |
| 4 / 1 | 60.4 ± 0.3 | 55.5 ± 0.6 | 0.92× | 384.0→590.7 | 17.00→16.90 | 2509.0→2690.0 |
| 4 / 4 | 189.9 ± 1.5 | 191.9 ± 2.7 | 1.01× | 717.5→675.4 | 20.10→19.12 | 3086.0→2910.7 |
| 4 / 8 | 308.3 ± 4.9 | 331.4 ± 5.3 | 1.08× | 1250.2→2146.5 | 23.49→21.13 | 3742.7→3517.6 |

### sapphire3，Qwen2-VL-2B，单L20原生 vs 解耦

| 图数 / 并发 | 基线 tokens/s | 目标 tokens/s | 吞吐比 | TTFT P95 ms：基线→目标 | TPOT P95 ms：基线→目标 | E2E P95 ms：基线→目标 |
|---|---:|---:|---:|---:|---:|---:|
| 1 / 1 | 72.8 ± 0.4 | 73.9 ± 3.0 | 1.01× | 78.0→97.6 | 15.40→15.05 | 2029.4→2006.5 |
| 4 / 8 | 315.8 ± 3.4 | 394.9 ± 8.1 | 1.25× | 1333.3→1977.8 | 21.57→17.19 | 3735.4→3098.3 |

### sapphire3，Qwen2-VL-2B，单L20原生 vs encoder mask

| 图数 / 并发 | 基线 tokens/s | 目标 tokens/s | 吞吐比 | TTFT P95 ms：基线→目标 | TPOT P95 ms：基线→目标 | E2E P95 ms：基线→目标 |
|---|---:|---:|---:|---:|---:|---:|
| 1 / 1 | 72.8 ± 0.4 | 83.8 ± 0.4 | 1.15× | 78.0→91.9 | 15.40→12.45 | 2029.4→1674.5 |
| 4 / 8 | 315.8 ± 3.4 | 411.7 ± 12.9 | 1.30× | 1333.3→1696.7 | 21.57→17.30 | 3735.4→2939.0 |

L20仅低/高两点；4090当前库/驱动拒绝SM mask，不宣称划分成功。


## 完整图表与机制限制

![单H20完整六负载](../../outputs/qjh000-migration/report/performance-all.png)

encoder stream SM实测78→64，可清零恢复并重新施加；原trace记录编码与语言CUDA活动重叠。这不等于完整互斥分区，也不保证吞吐提高。部分输出token IDs不同，输入相同不代表全部逐token或语义等价。三重复、固定顺序与时间漂移限制保留，不将描述性百分比当显著性或因果结论。

## 代码、报告与复跑

| 内容 | 入口 |
|---|---|
| 最新结论/完整统计 | [结论](../../docs/reading/outputs/qjh000-migration/report/final-summary.md) / [六点报告](../../docs/reading/outputs/qjh000-migration/report/space-all-report.md) |
| 启动、压测和分析 | [scripts](../../outputs/qjh000-migration/scripts) / [analysis](../../outputs/qjh000-migration/analysis) / [实际脚本](../../outputs/qjh000-migration/results/formal/used-scripts) |
| 版本、权重pin及补丁 | [configs](../../outputs/qjh000-migration/configs) / [累计补丁](../../outputs/qjh000-migration/results/patches) |
| 逐请求与机制证据 | [正式数据](../../outputs/qjh000-migration/results/formal) / [机制入口](../../docs/reading/outputs/qjh000-migration/README.md) |
| 4090/L20历史批次 | [阶段报告](../../docs/reading/outputs/reproduction/report/sapphire-stage-report.md) / [旧配置](../../outputs/reproduction/configs) / [旧补丁](../../outputs/reproduction/patches) |

以下CPU命令在仓库根目录执行，需Matplotlib3.9.2，不运行GPU，不改原始数据：

```bash
python scripts/revision/compare_existing_space.py
```

恢复完整证据后，也可在副本重算原始Space统计（不覆盖封存统计）：

```bash
mkdir -p restore/recomputed
python restore/outputs/qjh000-migration/analysis/space_results.py --root restore/outputs/qjh000-migration --phase all --output restore/recomputed/space-all.json
```

GPU复跑按[原命令与前提](../../docs/reading/outputs/qjh000-migration/README.md)和[可移植状态](../../PORTABLE.md)：context4096、1/4图、C1/4/8，native/解耦/encoder mask同卡、相同私有MPS与缓存条件。原路径、UUID、boot、锁和审查marker不能直接删除；新主机必须重新验证。旧2B安装路径不是最新7B配置。

## 完整证据下载

[Release](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/tag/experiments-2026-10-25)保留原完整ZIP；最新Space包与首轮共享包如下。共享包同时含EPD材料，按Space来源路径取用；其余历史包和完整恢复步骤见[资产索引](../../publication/ASSETS.md)。

| 批次/用途 | 下载文件 | 大小（bytes / MiB） | SHA256 |
|---|---|---:|---|
| qjh000单H20/7B最终封包，含CUDA trace | [spaceserve-7b-h20.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/spaceserve-7b-h20.zip) | 947,439,150 / 903.55 | `27101c16596d1db7e4d3f08eaf86b0456264fa370876ee813cbaace251c43eee` |
| 首轮4090/L20 Space及双H20 EPD最终选用封包 | [reproduction-h20.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/reproduction-h20.zip) | 79,894,392 / 76.19 | `3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38` |
