# SpaceServe / EPD Disaggregation 小规模复现

本仓库保存已完成实验的代码、补丁、逐请求记录、报告与机制证据。2026-10-25开始整理，实际发布验收时间见发布记录；没有为上传重新运行GPU实验。发布验收状态见[发布记录](publication/publish-state.json)。

Git保留可直接浏览的代码、报告、PNG/SVG和小体积数据；大CUDA trace、nsys/SQLite、输入图集及完整封包由同仓库Release承载。[资产索引](publication/ASSETS.md)提供真实验收状态、大小、SHA256及下载链接，[逐文件覆盖清单](publication/source-files.json)记录原路径、原SHA、Git位置或Release包内成员。原封存文档的本地路径不改，下面导航使用仅修正链接的GitHub阅读副本。

## 结果总览

各批次只与自己的同机、同模型、同GPU预算基线比较，不做跨主机/模型绝对排名。每配置20预热、100正式请求×3，目标128输出tokens；固定并发不等同真实到达率SLO。

| 批次/测量主机 | 模型与GPU预算 | 请求范围 | 主要观察 |
|---|---|---|---|
| SpaceServe 7B / qjh000 | Qwen2-VL-7B-Instruct，FP16/TP1/eager，单H20；native vLLM / 解耦 / encoder SM mask | 18配置，5400正式＋360预热 | 未划分/native吞吐−6.32%至＋5.86%；mask/native−7.52%至＋6.29%，新增四点mask相对未划分均下降 |
| EPD方案A / qjh003 | MiniCPM-V-2_6，FP16/TP1；E:P:D=1:1:1与同三H20完整三副本 | 8配置，2400正式＋160预热；后续CPU分析在qjh000 | off吞吐低/高为三副本0.930/0.941倍；高负载EPD观测扰动5.0027158%超过5%诊断阈值，trace仅路径存在用途 |
| 首轮Space / sapphire1、sapphire3 | Qwen2-VL-2B，单4090或L20，与各自原生vLLM比较 | 分属首轮封存矩阵 | 4090六点约0.92–1.08倍；L20低/高未划分约1.01/1.25倍、encoder mask约1.15/1.30倍；不能外推至H20/7B |
| 首轮EPD / qjh003、qjh005 | MiniCPM-V-2_6，同机三H20公平预算 | 最终选4800正式；缓存初态不一致的旧1200被补测替代并保留 | qjh003六点0.89–0.99倍，qjh005低/高约0.93/0.95倍，均无吞吐加速 |
| 离线后续 / epd-followup | 只读首轮两台H20的4800请求，无新增测量 | API通知间隔及事件源码语义分析 | 后续通知窗口普遍更长；不能将通知、CPU事件或无记录CUDA直接作为GPU耗时/空闲或因果证据 |

首轮reproduction共归档15000正式请求；报告选13800，其中1800条旧sapphire3 EPD只作诊断，12000条为有效测量。被替代、失败、诊断数据均独立保留，不混入正式加速结论。sapphire3出现纯CUDA跨卡拷贝损坏；没有维护前后对照证明IOMMU因果。

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

## EPD方案A：同三卡完整三副本基线

主结果使用profiler关闭off；基线是相同三张H20上的三个完整模型副本，客户端均衡分发。不是拿三卡EPD对单卡基线。

| 图/C | 三副本 req/s ± SD | EPD req/s ± SD | EPD/三副本 | TTFT P50 ms 基线→EPD | E2E P95 ms 基线→EPD |
|---|---:|---:|---:|---:|---:|
| 1/1 | 0.5479 ± 0.0009 | 0.5095 ± 0.0008 | 0.9298× | 47.40→56.60 | 1846.45→1990.70 |
| 4/8 | 3.9127 ± 0.0040 | 3.6809 ± 0.0517 | 0.9408× | 147.83→153.00 | 2129.12→2319.54 |

on/off观测扰动另列，不能替代off主结果：

| 系统 | 1图/C1 吞吐变化 | 4图/C8 吞吐变化 |
|---|---:|---:|
| EPD | -1.0917327% | -5.0027158% |
| 完整三副本 | -0.7725678% | -3.0872309% |

<details>
<summary>历史4090 / L20 / 双H20与各自baseline的完整对照表（展开）</summary>

以下为首轮报告的原表；tokens/s是128输出token条件下的均值±SD，†为缓存初态修正后的补测。旧表口径与最新req/s表分开，不合并排序。

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

L20仅低/高两点；4090当前库/驱动拒绝SM mask，不宣称划分成功。旧sapphire3 EPD数据损坏，仅诊断，不能与上述有效H20 EPD表混合。

</details>

![qjh000单H20 7B完整六负载](outputs/qjh000-migration/report/performance-all.png)

4图/C8的未划分组TTFT P50为825.88ms，原生1434.21ms，同时TPOT P50为22.03ms，原生19.27ms。mask额外收益不是普遍结论。实际encoder stream SM 78→64可恢复/重施，但不是decoder互斥分区或论文完整SIS/TWSRFT；LM仍保留visual权重，另驻留encoder，合计显存全部计入。

![EPD方案A吞吐与时延](outputs/epd-profile-a/report/throughput-latency.png)

正式输入图片/RGB及processed IDs对齐，但部分输出token不同，不能保证全部逐token或语义等价。三重复均值±样本SD不构成显著性检验；固定执行顺序、时间漂移、采样边界与因果未定限制完整保留。EPD高扰动案例未缩窗重采，不称原重采门槛已通过，也不量化解释off运行瓶颈。

## 报告与代码入口

| 内容 | 阅读入口 | 原始代码/配置 |
|---|---|---|
| qjh000完整结论、图表、设备/重叠/SM机制 | [结论](docs/reading/outputs/qjh000-migration/report/final-summary.md) / [完整六点报告](docs/reading/outputs/qjh000-migration/report/space-all-report.md) | [scripts](outputs/qjh000-migration/scripts) / [analysis](outputs/qjh000-migration/analysis) / [版本和逐文件权重pin](outputs/qjh000-migration/configs) / [累计patch](outputs/qjh000-migration/results/patches) |
| EPD方案A受限分析 | [报告](docs/reading/outputs/epd-profile-a/report/report.md) | [实际启动/压测脚本](outputs/epd-profile-a/results/formal/used-scripts) / [分析](outputs/epd-profile-a/analysis) / [instrumentation patch](outputs/epd-profile-a/instrumentation.patch) |
| 首轮4090/L20 Space与双H20 EPD | [分主机报告](docs/reading/outputs/reproduction/report.md) | [scripts](outputs/reproduction/scripts) / [patches](outputs/reproduction/patches) / [configs](outputs/reproduction/configs) |
| 首轮数据的后续离线分析 | [报告](docs/reading/outputs/epd-followup/report.md) / [源码事件解释](docs/reading/outputs/epd-followup/source-notes.md) | [scripts](outputs/epd-followup/scripts) / [CPU tests](outputs/epd-followup/tests) / [source](outputs/epd-followup/source) |

逐请求数据：最新Space在[results/formal](outputs/qjh000-migration/results/formal)；EPD方案A在[results/formal](outputs/epd-profile-a/results/formal)；首轮在[data/raw](outputs/reproduction/data/raw)；离线派生值在[results](outputs/epd-followup/results)。原始G1–G5记录随各批次reviews保留；本次上传审查另在[publication/reviews](publication/reviews)。

历史图：[4090](outputs/reproduction/report/spaceserve-4090.png)、[L20](outputs/reproduction/report/spaceserve-l20.png)、[qjh003](outputs/reproduction/report/epd-h20.png)、[qjh005](outputs/reproduction/report/epd-h20-qjh005.png)。模型、主机及批次分别展示，未重新聚合已有统计。

## 原始证据下载与完整恢复

Release：[experiments-2026-10-25](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/tag/experiments-2026-10-25)。私有仓库资产需要有权限的GitHub登录。完整封包保留原bytes，不是重新压缩的派生包；原SHA256SUMS只有恢复完整树后才应全量验证。

使用已登录的GitHub CLI下载并核对（也可在Release页面下载同名文件）：

```bash
gh release download experiments-2026-10-25 --repo BoyJiang2/spaceserve-epd-reproduction --dir release-downloads
(cd release-downloads && sha256sum -c ../publication/ASSETS.sha256)
mkdir -p restore/outputs/epd-profile-a
unzip release-downloads/spaceserve-7b-h20.zip -d restore/outputs
unzip release-downloads/reproduction-h20.zip -d restore/outputs
unzip release-downloads/epd-followup.zip -d restore/outputs
unzip release-downloads/epd-profile-a.zip -d restore/outputs/epd-profile-a
cp release-downloads/reproduction-h20.zip restore/outputs/
```

四批全部来源文件都有Git或包内成员映射；大trace/nsys/SQLite可从对应完整包按成员路径提取。历史reproduction.zip、reproduction-review-pending.zip、reproduction-peer-diagnostic.zip单独标为历史/诊断，不作为当前正式结果替代品。资产大小、SHA与下载链接见[索引](publication/ASSETS.md)。

## Release完整封包、大小与SHA256

发布前：以下为目标地址，尚未实际上传或下载验收。真实状态见publication/publish-state.json。

| 批次/用途 | 下载文件 | 大小（bytes / MiB） | SHA256 |
|---|---|---:|---|
| qjh000单H20/7B最终封包，含CUDA trace | [spaceserve-7b-h20.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/spaceserve-7b-h20.zip) | 947,439,150 / 903.55 | `27101c16596d1db7e4d3f08eaf86b0456264fa370876ee813cbaace251c43eee` |
| qjh003 EPD方案A受限最终封包，含nsys/SQLite | [epd-profile-a.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/epd-profile-a.zip) | 236,452,469 / 225.50 | `f7a35baf1c7e0e13ea1b1df65d4436efff199c5b21c876198289fbbfb2a1c094` |
| 首轮4090/L20 Space及双H20 EPD最终选用封包 | [reproduction-h20.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/reproduction-h20.zip) | 79,894,392 / 76.19 | `3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38` |
| 首轮数据的只读后续离线分析 | [epd-followup.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/epd-followup.zip) | 1,043,008 / 0.99 | `d155537944ea9095f2b1eecbd3780f57a611100aa9701b5e5617f4137d38a3f9` |
| 历史首版，非当前正式选用结果 | [reproduction.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/reproduction.zip) | 67,954,214 / 64.81 | `4ca04873975832309377feaea281b71b214b9badfbae488be80eda6a43474c7d` |
| 历史待审快照，非当前正式选用结果 | [reproduction-review-pending.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/reproduction-review-pending.zip) | 77,535,470 / 73.94 | `a661a300df154bcd0767c2dfd9a111e082e9d3f5b27b48047e4a60bfb7e4bba4` |
| 历史通信/诊断快照，非性能结论 | [reproduction-peer-diagnostic.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/reproduction-peer-diagnostic.zip) | 69,361,661 / 66.15 | `b4b950ce36918b2a46f536f7725861cf592aa3665b0d43bc77a045909e606c25` |

## CPU复算

在新restore副本中复算，避免覆盖Git封存原文。统计使用各批已记载Python版本，绘图固定Matplotlib3.9.2、NumPy1.26.4；epd-followup实际Python3.12.14，其余分析主要Python3.10标准库。CUDA SQLite分析还需完整Release证据。

```bash
mkdir -p restore/recomputed
python restore/outputs/qjh000-migration/analysis/space_results.py --root restore/outputs/qjh000-migration --phase all --output restore/recomputed/space-all.json
python restore/outputs/epd-profile-a/analysis/aggregate.py --root restore/outputs/epd-profile-a --frozen restore/outputs/reproduction
python restore/outputs/epd-profile-a/analysis/trace_analysis.py --root restore/outputs/epd-profile-a
python restore/outputs/epd-profile-a/analysis/notification_intervals.py --root restore/outputs/epd-profile-a
python restore/outputs/epd-followup/scripts/analyze.py restore/outputs/reproduction restore/recomputed/followup
```

各批原命令及绘图入口见对应README阅读副本。上传校验本身仅使用CPU，不运行上述GPU服务或改变封存统计。

## GPU复跑方法与设置

本仓库提交启动/压测/安装脚本供复现，不自动执行。先选空闲GPU、专属目录和预算，依据固定版本准备环境和权重，完成适用G1/G2/G3再运行。原脚本含主机、boot、GPU UUID、锁/私有MPS、批准marker和拒绝覆盖守卫；换主机须重新验证，不能直接删除守卫。

- [qjh000原始命令和前置条件](docs/reading/outputs/qjh000-migration/README.md)：Qwen2-VL-7B，FP16、TP1、eager、context4096、1/4图、C1/4/8；run_formal.sh依次比较native/解耦/有效encoder mask，先低高两点，经G4后续其余四点。同GPU 100%私有MPS，正式关闭profiler，禁止并行准备/下载/分析干扰。
- [首轮bootstrap及参数](outputs/reproduction/scripts/bootstrap.sh)：SpaceServe 2B与EPD MiniCPM分别固定隔离环境。H20 cuBLAS12.4.5.8为有证据的局部兼容覆盖，与torch原包元数据差异保留；不要将首轮2B安装路径当成最新7B配置。
- [EPD方案A实际脚本](outputs/epd-profile-a/results/formal/used-scripts/run_profile_a.sh)：同三卡EPD和完整三副本、观测off/on、两个负载点；2400条既有测量没有重跑。相同请求序列、缓存条件和采样，动态切换/请求内编码并行关闭。

权重、虚拟环境、编译/下载缓存及凭据均不提交。模型文件revision/bytes/SHA只保留pin，不把逐文件revision说成单一共同revision。上游commit、补丁来源和许可见[第三方说明](THIRD_PARTY_NOTICES.md)，不将上游代码写成本项目原创。
