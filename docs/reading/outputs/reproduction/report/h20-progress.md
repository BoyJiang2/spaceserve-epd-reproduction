> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/reproduction/report/h20-progress.md) SHA256 0831dcb256f79e7acd516950abaf6727f8fca2a56038214798cb994ddc39c104。原数字及解释不变。

# H20阶段最终进展

G1–G4独立subagent审查通过，G5 Claude APPROVE_WITH_NITS，BLOCKING为0。B1缓存公平性问题已关闭，收尾条件已落实，交付目录完整性核验通过；最终ZIP再校验后交付。最终选用H20的4800正式请求，另保留1200旧低负载；全归档及统计口径见report.md。

以下按发生顺序保留原测量及修复记录，较早的待审查状态不是当前状态。

# H20 阶段进展（测量与技术审计完成，独立审查待完成）

两台机器均为 8×H20、约 96GB/卡、NVLink；各选 GPU 0/1/2 做独立单机实验。qjh003 全矩阵及 qjh005 低、高两点和各自三副本基线均完成。新增4,800条正式请求和320条矩阵内预热已归档，技术审计通过。独立 Claude 审查因会话额度耗尽未完成，项目尚未最终验收。

已完成并保存证据：

- 两台各六个方向的 16MiB CUDA P2P 校验通过，源、目标完整 SHA256 一致。
- 原始 KV IPC 操作在两种缓存形状、六个方向、各三次复制中均数据一致，共72次；按两台实际服务缓存形状（60553 blocks）在压测后各补测三次，共78次，全部一致。
- 两台的原始 embedding IPC 操作分别连续三次复制四张 MiniCPM 图片的 embedding，均数据一致。
- 旧 cuBLAS 12.1.3.1 在 H20 上的单 token FP16 线性层异常可独立复现，GDB 栈停在 libcublasLt 算法选择。仅更新 cuBLAS 至 12.4.5.8 后，两台各四组矩阵乘法及数值校验通过；PyTorch 2.4.0+cu121、vLLM 0.6.1.post2、Transformers 4.44.2 保持原版本。NVIDIA 的 CUDA 12.4 Update 1 发布说明记录了相应 Hopper FPE 修复。[官方说明](https://docs.nvidia.com/cuda/archive/12.4.1/cuda-toolkit-release-notes/index.html#cublas-release-12-4-update-1)
- 两台各完成 45 个服务正确性用例，共 90 个；包括完整模型参考、8 并发参考、两轮 EPD 冷启动的单图/多图与 8 并发检查。处理后输入 IDs 和输出 token IDs 均与参考一致，路由检查通过。
- 实际三个阶段的 GPU UUID 与已加载 cuBLAS 路径已采集，修复后的版本同时用于 EPD 与基线。

qjh003 六个配置的 EPD/三副本基线吞吐比为0.89–0.99；qjh005两点约0.93、0.95。全部新增正式请求失败率为零，未观察到吞吐加速。图表、离线配对和合并报告草稿已生成。此前 sapphire3 的1,800条EPD正式记录继续保留为诊断数据。剩余验收为独立审查、处理发现、G5批准及最终归档。

缓存问题后续处理：经用户授权subagent接替独立审查，G2批准纯RGB初始化修复。两台已各成对补测单图/C1，新增1200正式与80预热；前后16份缓存快照均与20张归档源图的像素SHA一致，协议仍为全局20推理预热、100正式×3。旧1200低负载记录保留并标记为已替代，当前选用摘要来自补测。G1/G3通过，G2修复代码获APPROVE，B1仍待G4数据复审关闭，G5未批准。见report/cache-fix-acceptance.json及reviews/处理记录。

版本、探针和正确性原始记录位于 `evidence/qjh003` 与 `evidence/qjh005`。当前 `report.md` 已合并H20与SpaceServe，标明独立审查待完成；历史报告保存在 `report/sapphire-stage-report.md`。逐项验收见 `report/completion-audit.md`；`reproduction-peer-diagnostic.zip` 属于历史诊断归档，不能当作本轮最终交付。
