# SpaceServe：2026-10-27 13:00 窗口的机制预检证据

**313 条预检请求已通过模型 G3，预检报告 G4 通过；正式 0/54，没有新吞吐或时延性能结果。** 本批与旧 48/54 部分性能矩阵独立，不拼接跨窗口时间区组。SpaceServe 完整性能目标与后续公平 PD 目标均未完成。

| 对照组 | 实际模型/机制证据 | 新正式性能 |
|---|---|---|
| 原生 vLLM | cold/restart 正确性对照，各 15 target | 未启动 |
| 编码器解耦 | 独立 encoder；实际 GPU kernel overlap | 未启动 |
| 解耦＋encoder mask | 同 stream 严格 78→64、撤销恢复、重施及首次执行核验 | 未启动 |

共 7 reference＋90 target＋216 diagnostic＝313，诊断含 120 warm＋96 profile。实际 COCO448/每图256视觉tokens、FP16/TP1/eager；decoder 仍含 visual 权重。encoder mask 不代表 decoder 互斥，诊断 overlap 不代表关闭 profiler 时的性能收益或因果瓶颈。

- [可读完整报告](../../outputs/spaceserve-window-20261027-1300/report/preflight-report.md)、[逐请求与诊断原始记录](../../outputs/spaceserve-window-20261027-1300/results/preflight-models-attempt1/)。
- [模型 G3 原文](../../outputs/spaceserve-window-20261027-1300/reviews/g3-model-preflight-subagent.md)、[报告 G4 原文](../../outputs/spaceserve-window-20261027-1300/reviews/g4-preflight-report-subagent.md)、[496 项绑定 Gate](../../outputs/spaceserve-window-20261027-1300/evidence/G3_MODELS_APPROVED.json)。
- [实际运行开始与身份](../../outputs/spaceserve-window-20261027-1300/evidence/MODELS_ATTEMPT1_STARTED.json)、[退出](../../outputs/spaceserve-window-20261027-1300/evidence/models-attempt1-exit.json)、[零请求基础设施失败](../../outputs/spaceserve-window-20261027-1300/evidence/model-launch-failure-0/)、[17:58 自有进程终态复核](qjh000-final-release-check.json)。复核时 GPU 已有其他活动，未发送清理信号。
- [版本与配置](../../outputs/spaceserve-window-20261027-1300/configs/)、[原脚本](../../outputs/spaceserve-window-20261027-1300/scripts/)、[Git-first 代码与复跑入口](../code/h20-window-20261027/)。runtime 为 `83edff6608fc9db33ea90c3d04ce091705ee643f`，独立 collector 为 `6a9dd8c58231a82d0be498b832c85b5ccac7ab35`。原数值 producer 保持实际 pre-Git 来源，不追溯重标。

## 完整证据包（发布候选，尚未验收下载）

本页当前是数据发布候选；Release 尚待独立 G5、指定数据 commit、实际上传和下载核验。以下大小/SHA 是实际本地封包结果，尚不作为远端下载验收声明。

| 文件 | 字节 | SHA256 |
|---|---:|---|
| spaceserve-preflight-20261027-1300.zip | 420758860 | `b58dcefd6b329744422d55880a556e8972fde8e71b613bb6c1601dca71b9eea9` |
| source-files.json | 147005 | `1f87080cf2753478f107b5256b2530b578e30343d368385db51e85ab0ca4b913` |

[逐文件清单](source-files.json)包含完整 566 项路径、字节和 SHA；Git 保留其中 552 项可读文件/固定输入图片，10 份大 trace 和 4 份实际编译 `.so` 仅在完整 ZIP 中。ZIP_STORED 不再次压缩已有 trace；展开到新目录后恢复 `outputs/spaceserve-window-20261027-1300/`，不要覆盖旧封存，再按逐文件清单核 SHA。环境、模型权重与缓存没有纳入。

[封包完整性与筛查回执](package-check.json)记录 ZIP 成员 SHA/CRC、原始字节/相对路径以及 10 份 gzip 完整流的强规则筛查，零匹配；仅做公开交付的保密检查，没有解析 JSON、重算 kernel 或性能结论。此筛查覆盖明示模式，不宣称识别所有可能敏感内容。[发布范围与限制](plan.md)、[独立审查](reviews/)保留。

原批次 README/报告末尾的“待审/待发布”是受审及归档时原文，保留原字节；G3/G4 的实际结论以上述审查原文为准，发布状态以本页及后续真实验收为准。

[返回 SpaceServe 项目及 baseline 对照](../README.md) · [旧批次性能比较](../comparison/README.md)。旧性能数字不归入本批，未验证 decoder 互斥不称完整 SM 分区。
