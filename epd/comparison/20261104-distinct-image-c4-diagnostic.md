# EPD 不同图片 C4 并发诊断（2026-11-04）

EPD 与完整模型参考各完成四个不同图片的单图请求；逐索引请求字节相同、输出正文逐字相同，本次未观察到串图或串响应。**这是正确性与采集预检，不是正式性能对照。**

| 项目 | EPD c4e | 完整模型参考 c4d |
|---|---|---|
| 硬件 | 同机 H20 三卡，E:P:D=1:1:1 | 同机 H20 单卡，完整模型 |
| 模型 | MiniCPM-V-2_6 / FP16 / TP1 | 同左 |
| 请求 | 客户端 C4、4 个不同 COCO 单图 | 相同请求序列 |
| 生成 | greedy，强制 128 生成事件 | 同左 |
| 结果 | 4/4 HTTP200，逐个128事件 | 4/4 HTTP200，逐个128事件 |
| client / work / cleanup / outer exit | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| 资源终态 | 三卡显存0、已登记run进程无存活 | 单卡显存0、已登记run进程无存活 |

两组串行运行。EPD实际请求日志为 `enable_irp=False`。官方基线 `9b111f710dfb4724072b603d626a1e4dad93ef1f`，适配 `06fbcb6f3f3b931950077077c9a040e9c238deee`；工具发布 `15765b7fa2db6649cb8309cc3e0b61820c274c1f`。使用现有 CUDA IPC 二进制，其完整构建来源尚待闭合。

| 图片尾号 | 人工核对主体 | 请求字节相同 | 输出相同 |
|---|---|---|---|
| 328 | 长椅上的军装人物 | 是 | 是 |
| 400 | 船上的狗 | 是 | 是 |
| 623 | 抱巨大玩具熊的女子 | 是 | 是 |
| 1146 | 戴眼镜、黑衣绿领带男子 | 是 | 是 |

输出中的重复结束符、坐标框及无关尾文均保留。强制输出长度下的这些现象不能解释为自然结束的高质量回答。原始 batch 中语义状态仍为运行当时的 pending；本报告的核对是随后进行的独立步骤，不改写原件。

## 逐请求采集值

下列数值仅供复算采集口径。三卡与单卡预算不同、每组仅四个冷请求，无预热与重复，**不据此计算加速比、正式吞吐或性能优劣**。

| run | 图片索引 | 服务端 TTFT/s | 服务端 TPOT/ms | 客户端 E2E/s |
|---|---|---:|---:|---:|
| c4e | 0 | 1.2400 | 31.011 | 6.0426 |
| c4e | 1 | 1.2576 | 45.732 | 7.9323 |
| c4e | 2 | 1.2749 | 60.460 | 9.8222 |
| c4e | 3 | 2.0741 | 16.359 | 4.1582 |
| c4d | 0 | 2.6864 | 15.154 | 5.8004 |
| c4d | 1 | 4.6533 | 15.075 | 7.7598 |
| c4d | 2 | 6.6109 | 15.138 | 9.7277 |
| c4d | 3 | 1.9028 | 15.122 | 3.8298 |

服务端 TTFT = 首生成事件 − issued，排除 API 图片加载，不是客户端流式 TTFT；TPOT = (末事件 − 首事件)/(事件数−1)。客户端 E2E 截止完整 JSON 响应读完。实际视觉 token 数未采集，为 null，不以 processed prompt 差值替代。客户端峰值 inflight=4 仅证明 HTTP 请求重叠，不证明服务端执行或 GPU 计算重叠。NVML PID/UUID 样本支持设备放置，不证明计算重叠，也不是连续峰值显存证明。

## 证据与复跑入口

- [逐图输出及配对](../validation/official-c4-20261104/paired-comparison.json)
- [EPD 原始 batch](../validation/official-c4-20261104/c4e/batch-result.json)、[完整模型 batch](../validation/official-c4-20261104/c4d/batch-result.json)；各目录保留 request、intent、response、record、终态、解释器来源和清理输出。
- [EPD 完整日志清单](../validation/official-c4-20261104/c4e/server-manifest.json)、[完整模型清单](../validation/official-c4-20261104/c4d/server-manifest.json)、[设备放置选样](../validation/official-c4-20261104/placement-samples.json)。大日志保留于清单所列服务器路径，本次未上传 Release，不将清单当作已上传证明。
- [EPD 启动脚本](../tools/official_epd_concurrent_four.sh)、[完整模型脚本](../tools/official_d_concurrent_four.sh)、[客户端](../tools/official_c4_client.py)、[超时收口](../tools/official_c4_finalize.py)。先按脚本固定资源、环境与哈希检查准备，再在本人有效窗口执行；不要复用旧预约凭据。
- [此前单请求基线链路](20261104-official-pd-single-request.md)、[四图同请求失败及修复](20261104-four-image-diagnostic.md)。历史失败没有被本批覆盖。

尚未完成：embedding/KV 数值传输验证、启用 IRP 路径修复、真实 GPU 计算重叠、同三卡三完整副本/PD/EPD 的公平正式矩阵。本批不能替代这些验收。
