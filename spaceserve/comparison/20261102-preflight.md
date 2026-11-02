# SpaceServe 2026-11-02：313 请求模型与机制预检

**模型和机制预检通过，正式性能为 0/54。** qjh003 单张 H20（GPU2），Qwen2-VL-7B-Instruct、FP16、TP=1。独立[实际模型 G3](../data/space-20261102-G3.md) 为 APPROVE / BLOCKING 0。本页与 10 月 27 日 48/54、10 月 31 日预检分别保留，不合并为一个完整性能批次。

| 检查（冷启动／完整重启） | 原生 vLLM | 解耦 | 解耦＋encoder mask |
|---|---|---|---|
| 正确性 HTTP 200 | 15/15；15/15 | 15/15；15/15 | 15/15；15/15 |
| processed prompt 和输出 token IDs 与同轮原生 reference 一致 | 30/30 | 30/30 | 30/30 |
| 每组诊断请求（含20预热、16 profiler请求） | 36/36；36/36 | 36/36；36/36 | 36/36；36/36 |
| 实际同卡 FP16 worker 数 | 1 | 2（含独立 encoder） | 2（含独立 encoder） |
| 实际 encoder stream SM 探针 | 不适用 | 78→78；78→78 | 78→54；78→54 |
| 对齐 CUDA 时间的 encoder/decoder kernel 重叠 | 不适用 | 两轮均观察到 | 两轮均观察到 |
| 本批正式性能单元 | 0 | 0 | 0 |

本批含7条原生 reference、90条分组正确性请求和216条诊断请求，共313条，请求失败为0。实际C4/C8并发峰值分别为4/8；诊断四图实际视觉token为1024，输出均为128 tokens。全部逐请求输入、输出 token IDs、时间及来源SHA保留于[可读JSONL](../data/space-20261102-requests.jsonl)。[结构化对照](../data/space-20261102-summary.json)区分正确性、诊断和正式数据。

## 这批回答了什么

同一GPU上，原生路径与解耦路径都能完成固定图像问答和并发路由检查，冷启动与完整重启后输出IDs均对齐原生reference。解耦两worker实际驻留同一物理GPU、参数为FP16；四个解耦服务的真实trace复算均观察到encoder/decoder kernel重叠。mask服务的实际encoder stream探针由78个SM变为54个，而无mask解耦组保持78个。

这些结果支持“当前硬件与实现的解耦和encoder mask机制可运行”，不证明decoder互斥分区、完整论文调度或吞吐收益。LM仍保留visual参数，另有encoder，不能宣称已复现论文的encoder容量收益。诊断请求带profiler，每轮每组为20条预热＋16条profiler样本，且为固定启动顺序，**不能替代54单元的吞吐、TTFT、TPOT、E2E、显存与波动对照**。本批不据此发布性能加速比。

## 版本与真实终态

- Runtime commit：`03688f823d145dcab925b30f6f73423f7cc1b354`。本地、GitHub及原服务器repo的103源码闭包核同，run内冻结88成员；不复制权重或环境。
- Model manifest SHA256：`1c49ab455b31a752c51b32be1df278a2db4b4206724d3d451ea987d2a1543111`。
- CPU套件114通过／0跳过；GPU numeric FP16和三轮mask探针已独立验收。工作负载NUMA0 CPU0–89／OMP4，监督器CPU50、nice10。
- 实际模型控制器PID2625966于北京时间20:08:34启动，20:24:21正常退出；远端phase与launcher均exit0。[释放原件](../data/space-20261102-release-check.json)确认386登记PID及executor共387原PID均不存在，GPU2 UUID匹配、显存0、util0、compute apps空。
- 外层SSH观察器2070秒超时，local controller exit1，不能改写为local exit0。确认远端已结束后，仅凭原PID40692、精确Windows创建时间及OpenSSH路径绑定的进程句柄收口本地观察器，见[清理记录](../data/space-20261102-observer-cleanup.json)。未对他人或远端任务发送信号。连接异常根因未定位。
- 首次模型派发在写phase intent前被fresh snapshot校验拒绝；恢复只在原API快照返回后真实等待2秒，原时间戳、policy及remote项目源码不改。模型实际消费输入时仍在原900秒有效期内。最初collector的Python3.10压缩参数错误与后续成功流式回收分别保留。

六服务的像素覆盖参数警告保留，不能声称`min_pixels/max_pixels`覆盖参数实际生效；本批输入一致性依据实际processed IDs、token计数和原图内容校验。退出时NCCL与semaphore警告也保留；释放结论依据原PID和GPU实查，不把“无警告”当标准。

## 原件、复跑与未完成项

完整run和本批stage共550个regular原件已流式回收到本地：[归档校验](../data/space-20261102-archive.json)。压缩包351867489字节，SHA256 `57204d3bb27babf73672fbd4999b2db4b41b9a2c4f36eecbf24e46fe9a8d8a0c`；全部成员SHA匹配，含完整trace、请求、worker/SM/MPS/CPU放置与成功失败日志，不含环境、权重或缓存。**Release尚待发布，本页不把本地归档冒充远端下载。**

指定版本的[统一入口](../runtime/entry.py)、[配置](../runtime/configs/qjh003-20261030-0400.proposed.json)、[Windows阶段控制器](../../tools/control_space_window_20261030.py)、[模型预检](../runtime/scripts/run_models.py)、[trace分析](../runtime/scripts/analyze_trace.py)均可审阅。准确执行命令、审批、快照、manifest及退出记录在原件中。重跑须为新run绑定有效预约及当前资源，并使用该commit的prepare→CPU→numeric→model原顺序；历史窗口的审批原件不是新窗口运行许可。

暂停后恢复时间已超过完整正式矩阵18:37最晚入场，本窗不缩矩阵、不拼旧48/54、不重新跑模型。下一有效完整窗口仍需完成平衡顺序54单元、5400正式＋1080预热，形成与baseline的正式性能对照。EPD公平PD、两项目最新完整交付亦尚未完成。
