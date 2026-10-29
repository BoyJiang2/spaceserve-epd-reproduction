# EPD Disaggregation 复现项目

[qjh003固定目录迁移状态与静态证据](migration-qjh003-20261029/README.md)：原始资产已迁移，flat IPC/RUNPATH/shebang待重定位；没有本批新性能数据，历史baseline对照保持独立。

当前 [qjh003 固定目录代码与迁移状态](migration/README.md)：本地 G2 通过，目标迁移与新测试未执行；公平 PD 的 native36/selected360 接线仍未完成。

[本项目baseline完整对照](comparison/README.md) · [实际代码](code) · [版本配置](configs) · [补丁](patches) · [原始数据与证据](data/README.md) · [源文件SHA映射](SOURCE_FILES.json)


[返回项目总入口](../README.md) · [English overview](../README.en.md#epd-disaggregation) · [论文覆盖](../PAPER_VS_REPRO.md) · [补丁审计](../PATCH_AUDIT.md)

本项目研究MiniCPM-V-2_6的Encode–Prefill–Decode三阶段链路。EPD为E:P:D=1:1:1、FP16/TP1；性能基线是同一台机器、同三张H20上的三个完整模型副本，由客户端均衡分发。

最新已验收批次是qjh003方案A：2400正式＋160预热，后续CPU分析在qjh000，测量未重跑。请求内编码并行和动态角色切换关闭，视觉token存储与迁移仍在；未实现DistServe基线、容量扫描或到达率SLO。此页不与SpaceServe单卡/不同模型结果作绝对排名。qjh000修正批次已按受阻分支收口：53/60单元，完整C未完成，七项不再续接；与旧方案A分批展示。289请求模型正确性通过，但lite GPU窗口导出失败；B阶段（观测开销）正式未运行，经独立审查仅继续既定C-off，不声称观测等效或内部瓶颈已定位。

## 后续公平 PD 基线：CPU验证通过，GPU待验证

后续公平 PD 基线已有[独立 G1/G2 通过的 v11 代码](plans/fair-pd-20261027-v11/README.md)，[qjh000目标CPU实际76 PASS](validation/qjh000-cpu-20261027/README.md)，0失败/错误/跳过，完整日志与独立审查保留；[旧 v8 候选](plans/fair-pd-20261027/README.md)独立保留。**真实 GPU/模型验证尚未执行，没有新增性能结果**；三个完整副本、调优 PD 和 EPD 的完整对照仍待完成。CPU契约测试与以下已运行性能批次分开。2026-10-28 新增 [v13 候选](plans/fair-pd-20261028-v13/README.md)（v12 薄 controller＋v13-a 修复＋qjh000 当日 CPU 范围），[qjh000 目标 CPU 实际 87 PASS](validation/qjh000-cpu-20261028/README.md)，0 失败/错误/跳过；同样不含 GPU/模型或性能结果。

## qjh000修正批次：终态部分结果

[本批完整原件、Release下载与SHA256](REVISION_ASSETS.md)

**53/60单元，5300正式＋1060预热，七项未执行。** 唯一续接exit1（IdentityUnconfirmed），底层原因未知，按事前规则不再续接。实际部分G4与窄受阻G5已通过，完整六区组性能复现未完成。lite观察G3失败，B正式未运行；不能声称观察等效或已定位off内部瓶颈。

[全部30计划baseline配对及逐次结果](../outputs/epd-revision-20261026/report/C-terminal-reviewed-candidate/report.md) · [可复算统计](../outputs/epd-revision-20261026/report/C-terminal-reviewed-candidate/analysis.json) · [原始数据](../outputs/epd-revision-20261026/results/performance) · [审查、退出与限制索引](../outputs/epd-revision-20261026/report/publication-status.md) · [代码与复跑入口](../outputs/epd-revision-20261026/README.md)

缺失项不填零，不出完整矩阵CI或合并加速结论；已有退化与近持平观测均保留。下方旧方案A与图表来自不同批次，不与本批汇总。

## EPD方案A：同三卡完整三副本基线

主结果使用profiler关闭off；基线是相同三张H20上的三个完整模型副本，客户端均衡分发。不是拿三卡EPD对单卡基线。

| 图/C | 三副本 req/s ± SD | EPD req/s ± SD | EPD/三副本 | TTFT P50 ms 基线→EPD | E2E P95 ms 基线→EPD |
|---|---:|---:|---:|---:|---:|
| 1/1 | 0.5479 ± 0.0009 | 0.5095 ± 0.0008 | 0.9298× | 47.40→56.60 | 1846.45→1990.70 |
| 4/8 | 3.9127 ± 0.0040 | 3.6809 ± 0.0517 | 0.9408× | 147.83→153.00 | 2129.12→2319.54 |

### 方案A off：完整吞吐、延迟和显存对照

req/s与输出tokens/s为三次运行均值±样本SD；各延迟为300正式请求合并P50/P95（ms），不是独立重复CI。显存为三卡自有进程采样峰值合计（GiB）。

| 图/C/系统 | req/s ± SD | 输出 tokens/s ± SD | TTFT P50/P95 | TPOT P50/P95 | E2E P50/P95 | 采样显存 GiB |
|---|---:|---:|---:|---:|---:|---:|
| 1/1/三完整副本 | 0.5479 ± 0.0009 | 70.13 ± 0.11 | 47.40/49.32 | 13.97/14.15 | 1822.27/1846.45 | 177.11 |
| 1/1/EPD | 0.5095 ± 0.0008 | 65.21 ± 0.10 | 56.60/60.69 | 14.97/15.21 | 1957.95/1990.70 | 208.52 |
| 4/8/三完整副本 | 3.9127 ± 0.0040 | 500.82 ± 0.51 | 147.83/349.16 | 14.62/14.99 | 2002.40/2129.12 | 179.36 |
| 4/8/EPD | 3.6809 ± 0.0517 | 471.16 ± 6.62 | 153.00/337.07 | 15.08/15.61 | 2073.65/2319.54 | 208.52 |

来源：[原始聚合与三次运行](../outputs/epd-profile-a/report/performance.json)，本项目[实际配置副本](configs/profile-a)逐SHA关联封存源，不重算或替换旧结果。

on/off观测扰动另列，不能替代off主结果：

| 系统 | 1图/C1 吞吐变化 | 4图/C8 吞吐变化 |
|---|---:|---:|
| EPD | -1.0917327% | -5.0027158% |
| 完整三副本 | -0.7725678% | -3.0872309% |


## 图表、观测与解释边界

![EPD方案A吞吐与时延](../outputs/epd-profile-a/report/throughput-latency.png)

低/高负载off吞吐均低于三副本。高负载on的观测扰动5.0027158%越过旧预设5%诊断阈值：trace仅用于路径存在，不定量解释off瓶颈，未重采到阈值内。kernel活动并集不是可消除关键路径，交接窗口不是纯通信成本，不能推出“收益上限约2%”或“必然退化”。

固定并发不是Poisson到达率SLO；三次重复及固定顺序限制保留。合计采样显存不是论文E worker峰值或容量收益。输入/RGB对齐但部分输出token不同，不声称全量逐token或语义等价。

## 历史H20对照与只读后续分析

以下沿用首轮报告原表：tokens/s为128输出token条件下三次运行均值±样本SD，†为缓存初态修正后的补测；与最新方案A的req/s分别展示。每配置20请求预热，100正式请求重复三次。

### qjh003 MiniCPM，三H20完整三副本 vs EPD

| 图数 / 并发 | 基线 tokens/s | 目标 tokens/s | 吞吐比 | TTFT P95 ms：基线→目标 | TPOT P95 ms：基线→目标 | E2E P95 ms：基线→目标 |
|---|---:|---:|---:|---:|---:|---:|
| 1 / 1 † | 70.1 ± 0.0 | 65.5 ± 0.1 | 0.93× | 50.3→58.9 | 14.23→15.13 | 1854.6→1978.9 |
| 1 / 4 | 284.6 ± 0.7 | 275.6 ± 2.3 | 0.97× | 60.0→80.4 | 14.19→14.36 | 1852.5→1895.4 |
| 1 / 8 | 571.9 ± 1.4 | 510.1 ± 2.6 | 0.89× | 119.4→117.8 | 13.48→15.03 | 1776.4→1996.4 |
| 4 / 1 | 66.9 ± 0.0 | 62.0 ± 0.2 | 0.93× | 144.4→158.1 | 14.13→15.23 | 1933.8→2088.6 |
| 4 / 4 | 263.0 ± 1.1 | 259.5 ± 0.5 | 0.99× | 154.2→181.1 | 14.97→14.63 | 2039.7→2022.5 |
| 4 / 8 | 498.9 ± 1.7 | 472.8 ± 1.6 | 0.95× | 349.9→330.1 | 14.96→15.52 | 2162.3→2243.2 |

### qjh005 MiniCPM，三H20完整三副本 vs EPD

| 图数 / 并发 | 基线 tokens/s | 目标 tokens/s | 吞吐比 | TTFT P95 ms：基线→目标 | TPOT P95 ms：基线→目标 | E2E P95 ms：基线→目标 |
|---|---:|---:|---:|---:|---:|---:|
| 1 / 1 † | 70.9 ± 0.0 | 66.1 ± 0.1 | 0.93× | 48.7→58.2 | 13.94→14.92 | 1816.9→1951.9 |
| 4 / 8 | 508.3 ± 2.5 | 481.7 ± 0.8 | 0.95× | 351.3→328.1 | 14.62→14.95 | 2032.8→2206.7 |


旧sapphire3的1800条EPD记录因纯CUDA跨卡数据损坏仅作诊断，不能混入H20有效性能结果；没有维护前后对照证明IOMMU因果。首轮最终选用H20共4800正式，后续分析只读这些数据，不新增测量。

离线后续记录的通知窗口普遍更长；不能将通知、CPU事件或无记录CUDA直接作为GPU耗时、空闲或因果证据。

| 内容 | 入口 |
|---|---|
| 方案A报告与逐请求数据 | [受限报告](../docs/reading/outputs/epd-profile-a/report/report.md) / [正式数据](../outputs/epd-profile-a/results/formal) |
| 实际启动/压测和分析 | [used-scripts](../outputs/epd-profile-a/results/formal/used-scripts) / [analysis](../outputs/epd-profile-a/analysis) / [instrumentation](../outputs/epd-profile-a/instrumentation.patch) |
| 首轮H20与缓存修正 | [分主机报告](../docs/reading/outputs/reproduction/report.md) / [缓存修正版补丁](../outputs/reproduction/patches/epd-h20-cache-fixed.patch) / [配置](../outputs/reproduction/configs) |
| 离线后续 | [报告](../docs/reading/outputs/epd-followup/report.md) / [事件源码解释](../docs/reading/outputs/epd-followup/source-notes.md) / [scripts](../outputs/epd-followup/scripts) / [tests](../outputs/epd-followup/tests) |

## 复跑入口

GPU前置条件是同机三张可用卡、通信一致性和冷启/重启正确性。按[方案A实际启动协议](../outputs/epd-profile-a/results/formal/used-scripts/run_profile_a.sh)与[可移植状态](../PORTABLE.md)准备；不是任意单卡可跑。两组模型、输入、缓存、精度、GPU总预算及请求序列必须一致；不将三卡EPD对单卡结果称吞吐加速。

下列为恢复完整证据后、在仓库根目录使用副本复算的入口；SQLite分析需Release中的原始证据，避免覆盖封存统计：

```bash
python restore/outputs/epd-profile-a/analysis/aggregate.py --root restore/outputs/epd-profile-a --frozen restore/outputs/reproduction
python restore/outputs/epd-profile-a/analysis/trace_analysis.py --root restore/outputs/epd-profile-a
python restore/outputs/epd-profile-a/analysis/notification_intervals.py --root restore/outputs/epd-profile-a
python restore/outputs/epd-followup/scripts/analyze.py restore/outputs/reproduction restore/recomputed/followup
```

分析环境依批次pin；epd-followup为Python3.12.14，其余主要Python3.10。H20的cuBLAS12.4.5.8局部兼容覆盖有单独证据，不能无记录切换依赖。

## 完整证据下载

[Release](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/tag/experiments-2026-10-25)包含下列EPD及首轮共享包。完整恢复、其他历史/诊断包和校验方法见[资产索引](../publication/ASSETS.md)。

| 批次/用途 | 下载文件 | 大小（bytes / MiB） | SHA256 |
|---|---|---:|---|
| qjh003 EPD方案A受限最终封包，含nsys/SQLite | [epd-profile-a.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/epd-profile-a.zip) | 236,452,469 / 225.50 | `f7a35baf1c7e0e13ea1b1df65d4436efff199c5b21c876198289fbbfb2a1c094` |
| 首轮4090/L20 Space及双H20 EPD最终选用封包 | [reproduction-h20.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/reproduction-h20.zip) | 79,894,392 / 76.19 | `3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38` |
| 首轮数据的只读后续离线分析 | [epd-followup.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/epd-followup.zip) | 1,043,008 / 0.99 | `d155537944ea9095f2b1eecbd3780f57a611100aa9701b5e5617f4137d38a3f9` |
