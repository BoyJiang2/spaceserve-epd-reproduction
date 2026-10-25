# EPD方案A：观测扰动与CUDA时间线

qjh003上8配置、2,400条正式请求和160条预热已完成，失败率为0，全部生成128 tokens。qjh000仅执行后续CPU分析，未重跑测量。

**主要结论：**关闭观测时，EPD在1图/C1、4图/C8下的吞吐分别为同三卡三副本基线的0.930×、0.941×，均无加速。高负载EPD的观测流程使吞吐降低**5.0027158%**，越过预设5%诊断阈值；这不是显著性检验，也不等于纯CUDA profiler开销。

![吞吐与端到端延迟](throughput-latency.png)

## 设置与统计口径

MiniCPM-V-2_6、FP16、TP=1；EPD为E:P:D=1:1:1，基线为相同三张H20上的三个完整副本并由客户端均衡分发。固定COCO子集/RGB指纹、提示词及处理后输入；每图64视觉tokens。每配置20预热、100正式×3，固定并发，关闭动态角色切换与请求内编码并行。Torch2.4.0/cu121、vLLM0.6.1.post2、transformers4.44.2、实际加载cuBLAS12.4.5.8。实际启动参数与版本以results/formal/used-scripts、runtime.json为准。

吞吐为三次正式请求吞吐的算术平均±样本标准差；延迟为300请求合并后的inclusive线性插值P50/P95。TPOT=(末token时间−首token时间)/127。显存为三卡所有本项目GPU进程合计的采样峰值，不能称瞬时精确峰值。固定并发结果不推导到达率SLO。

| 观测 | 系统 | 图/C | 请求/s，均值±SD | TTFT P50/P95 ms | TPOT P50/P95 ms | E2E P50/P95 ms | 合计采样峰值GiB |
|---|---|---|---:|---:|---:|---:|---:|
| off | EPD 1:1:1 | 1/1 | 0.5095±0.0008 | 56.60/60.69 | 14.97/15.21 | 1957.95/1990.70 | 208.518 |
| off | EPD 1:1:1 | 4/8 | 3.6809±0.0517 | 153.00/337.07 | 15.08/15.61 | 2073.65/2319.54 | 208.518 |
| off | Three replicas | 1/1 | 0.5479±0.0009 | 47.40/49.32 | 13.97/14.15 | 1822.27/1846.45 | 177.111 |
| off | Three replicas | 4/8 | 3.9127±0.0040 | 147.83/349.16 | 14.62/14.99 | 2002.40/2129.12 | 179.361 |
| on | EPD 1:1:1 | 1/1 | 0.5039±0.0030 | 55.23/59.52 | 15.11/15.62 | 1974.27/2043.19 | 208.625 |
| on | EPD 1:1:1 | 4/8 | 3.4968±0.1149 | 155.04/421.49 | 15.56/18.38 | 2140.04/2554.51 | 208.605 |
| on | Three replicas | 1/1 | 0.5437±0.0056 | 46.98/49.40 | 14.03/14.35 | 1828.74/1871.30 | 177.193 |
| on | Three replicas | 4/8 | 3.7919±0.0858 | 148.36/350.35 | 14.82/16.27 | 2032.37/2240.48 | 179.443 |

## 观测流程的影响

EPD低/高负载on相对off吞吐变化为−1.092%/−5.0027158%；三副本为−0.773%/−3.087%。off相对封存的有效旧结果变化均小于0.5%。on不替代off主要性能结果，不从原始分母中扣除采集控制开销。

采集start发生在第3重复末16请求提交前，但计入该重复吞吐；EPD低/高耗时0.722429/0.728635秒，三副本为2.080065/2.228097秒。stop在计时结束后。高并发start时index77–83仍在执行；84–99是完整选定16请求，整个trace还含边界请求。这个设计的on/off差包含控制、打点、采集及运行波动，不能分离纯profiler执行代价。

24重复首条调度开销范围约0.438–1.975ms，末条记账约0.224–0.400ms，均保留在原吞吐窗口。显存最大内部采样间隙0.290194秒，窗口首尾最大约0.166秒；逐配置明细见reviews/g4-formal-statistics-subagent.md与performance.json。

processed input IDs在所有配对中相同。高负载三副本on/off有4/300对输出token不同、off/旧有5/300对不同；EPD/三副本高负载off、on分别有12/300、10/300对不同。固定路由正确性已验收，但这不表示全部性能请求逐token相同，差异均保留。

## 实际CUDA关联与解释边界

8份SQLite核验64个完整选定请求，每请求128次、共8192次API输出，以及E/P/D或基线prefill/decode CUDA活动。关联采用同进程correlationId、同线程同步worker NVTX中的完整runtime launch；GPU结束允许晚于CPU范围。逐请求kernel时长取并集，共享batch kernel只是该请求参与的活动，不能求和为独占GPU成本。物理身份采用实测PID→UUID与trace PID集合，CUPTI deviceId是进程局部编号。

| 负载 | E kernel并集P50 ms | P kernel并集P50 ms | D kernel并集P50 ms | E末→P首P50 ms | P末→D首P50 ms |
|---|---:|---:|---:|---:|---:|
| 1图/C1 | 16.550 | 16.641 | 1517.111 | 6.727 | 7.218 |

高负载EPD观测扰动超过5%，其trace在本版只证明E/P/D及迁移路径存在，不用于量化瓶颈或off因果解释，因此上表只保留低负载EPD。先前cuda-analysis.json中高EPD计算作为历史诊断记录保留，用途限制见interpretation-scope.json。没有执行缩窗重采，不能称原重采门槛已满足；当前用户goal明确不重跑已完成2400请求，受限交付范围已独立G1复核。

低负载采集片段中解码活动跨度长于编码/预填充；阶段交接间隔含通信、排队与调度，不能称纯通信时间。基线prefill同时包含视觉处理，未虚构单独E。迁移copy统计仅为整个捕获窗口中关联到迁移worker调用的copy次数、记录字节和时间并集，不按请求分摊、不解释为链路带宽。

高负载三副本trace开头有边界kernel缺少完整worker范围，分别88/354/346个，已在cuda-analysis.json列为跳过计数；完整选定16请求均有阶段关联和完整API输出，但仍只称“已关联CUDA活动”，不扩写为全部GPU成本。CPU lifetime中的await/通知间隔没有当GPU执行时长，解码begin覆盖最后一步的问题也未用来构造整段解码时长。

**待验证假设：**解码与阶段交接可能限制当前负载下的流水收益。D包含多步解码和共享batch活动曝光，不能仅凭其累计跨度判定off运行的瓶颈，也不能把交接间隔定量归因给通信。尚不能单凭带观测的短片段确定off运行的因果瓶颈。没有本轮性能收益，不建议立刻扩大EPD模型或做自动资源搜索；若继续EPD，优先在保持卡数公平的前提下检验阶段服务率、批处理和更多图像负载，新增设定另审。

## 同请求的worker与通知顺序匹配

以下只分析阈值内的低EPD、低/高三副本。同endpoint/rid内的128个worker调用与128次API输出按顺序匹配，检查P/prefill一次及127次decode的阶段、CUDA活动、worker/GPU在通知前完成和原始timestamp；未采集显式step ID或逐步依赖标签，不声称已证明依赖链。输出窗口采用实际NVTX marker时钟，同时报告与API timestamp间隔的误差，不将CPU通知当GPU执行。

每行时间分割为：本trace记录的CUDA kernel/copy/memset活动并集＋CUDA外的api.disconnect范围＋未解释余量＝通知间隔。无记录CUDA是补集，不能称物理GPU空闲；CPU worker/API范围可能重叠，不额外相加。三副本未加api.disconnect标记，该列0只表示无此观测范围，其他API处理留在未解释部分，不能称API耗时为0。活动并集不是依赖关键路径，不能据此声称GPU独占成本或CPU因果。EPD稳态行是token3–128，三副本D通知行包含token2–128，不能忽略首步口径差异来相减归因。

| 系统/图/C | 匹配间隔/期望 | 类别 | 数量 | 间隔均值 ms | CUDA并集均值 ms | 无记录CUDA均值 ms | API范围在CUDA外均值 ms | 未解释均值 ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| EPD 1:1:1/1/1 | 2032/2032 | steady_decode | 2016 | 15.7075 | 11.9630 | 3.7445 | 0.4849 | 3.2595 |
| EPD 1:1:1/1/1 | 2032/2032 | first_to_second_notification | 16 | 21.0391 | 12.9574 | 8.0817 | 0.4865 | 7.5952 |
| Three replicas/1/1 | 2032/2032 | D通知（含首D） | 2032 | 14.4713 | 12.0234 | 2.4478 | 0.0000 | 2.4478 |
| Three replicas/4/8 | 2032/2032 | D通知（含首D） | 2032 | 15.8943 | 11.4380 | 4.4562 | 0.0000 | 4.4562 |
| Three replicas/4/8 | 2032/2032 | baseline_other_request_prefill | 21 | 153.1839 | 121.0623 | 32.1216 | 0.0000 | 32.1216 |

低EPD的16条首→次通知另附完整P末→KV→首D窗口：P/首D实际GPU起止、窗口内迁移copy均逐请求保存；16/16窗口含context迁移copy。P GPU末→D GPU首间隔均值/P50/P95为6.6071/6.9602/8.3405ms。此处使用worker内kernel/copy/memset活动边界，原阶段表仅用kernel边界，两处间隔口径不同。copy只有blocks标签，时间重叠并不证明每rid的依赖链；第1→2通知窗口与完整交接窗口分别记录，不冒充同一个区间。

baseline_other_request_prefill只计实际其他请求prefill CUDA活动与既有请求通知间隔相交，是steady_decode的子集，类别数量不能相加为总间隔数；CPU范围相交候选单列。分布、匹配失败原因、具体rid/token/batch IDs、窗口边界和时间分割见notification-analysis.json及notification-intervals.jsonl。此观察不能证明prefill造成了停顿，off运行的因果归属仍未解决。

## 复算、审查与状态

事实统计、阶段CUDA分析、通知间隔分析及受限报告G4和交付G5均APPROVE_WITH_NITS；G5 B1/B2关闭，BLOCKING0。本批按独立批准的受限范围完成，不代表SpaceServe或整体目标完成。审查来源保存在reviews/，含Claude额度耗尽后的独立subagent接替；最终封包SHA/CRC见同级outputs/epd-profile-a-integrity.json。旧reproduction/ZIP保持封存，固定ZIP SHA256：`3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38`。

CPU复算：

```bash
python3 analysis/aggregate.py --root /path/to/epd-profile-a --frozen /path/to/reproduction
python3 analysis/trace_analysis.py --root /path/to/epd-profile-a
python3 analysis/notification_intervals.py --root /path/to/epd-profile-a
python3 analysis/write_report.py --root /path/to/epd-profile-a
```

聚合脚本要求reproduction-h20.zip与reproduction目录同级且SHA匹配；原始测量命令和完整配置见results/formal/used-scripts/run_profile_a.sh、各case/measurement/config.json及runtime.json。绘图使用Matplotlib3.9.2/NumPy1.26.4，在本地CPU渲染，输入均来自qjh000分析JSON。完整原始数据与8份原生nsys报告保留，未重复采集或改写qjh003来源。
