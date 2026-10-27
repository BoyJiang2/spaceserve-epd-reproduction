# H20新窗口：机制预检通过，正式矩阵未启动

本批完成同单H20、Qwen2-VL-7B-Instruct、FP16/TP1/eager的三组正确性与机制预检，独立模型G3为 **APPROVE_WITH_NITS，BLOCKING 0**。没有新正式性能请求：54单元完整矩阵未启动，不能据此给出新的吞吐加速比、TTFT、TPOT、端到端延迟或显存优劣结论。

旧48/54批次的[baseline性能对照](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/4500d059988eb5e7ffb4e352d5f7319d83290958/spaceserve/comparison)独立保留，本批不补入旧时间区组。

## 三组实际验证

| 系统 | cold/restart服务 | 与对应reference一致的target请求 | 每次服务诊断请求 | encoder SM证据 | GPU kernel并发证据 |
|---|---:|---:|---:|---|---|
| 原生vLLM | 2 | 各15 | 各20 warm＋16 profile | 原生对照 | 不宣称编码器解耦 |
| 编码器解耦 | 2 | 各15 | 各20 warm＋16 profile | 78→78，首次执行78 | 两次均观察到encoder/decoder overlap |
| 解耦＋encoder mask | 2 | 各15 | 各20 warm＋16 profile | 78→64严格子集；clear恢复78、reapply及首次执行64 | 两次均观察到overlap |

共7条reference＋90条target＋216条诊断＝313条实际请求；诊断包含120 warm与96 profile，全部诊断输出长度为128 tokens。90条target处理后输入IDs、输出IDs和文本均与对应reference一致；单图、COCO多图主题顺序和C8实际并发检查通过。cold/restart是服务生命周期正确性检查，不是磁盘或OS缓存冷却性能实验。

六次服务均实际FP16、TP1、eager、context4096、seq8，prefix/MM processor cache关闭。解耦encoder为独立进程，加载675,759,104个visual参数；decoder仍保留visual与language权重，因此不能宣称消除了decoder视觉权重驻留。

10份trace经完整gzip CRC/JSON、大小、SHA和worker PID核验。四组kernel overlap独立复算与原件一致，但它们来自启用诊断的片段；overlap存在不等于吞吐提升，也不能解释关闭诊断时的因果瓶颈。

## 版本与证据

| 阶段 | 实际版本关系 |
|---|---|
| 数值预检 | 新目标生效前实际运行，原producer `b7670dfe3ed165bde43b720fb7e2faeafb07c5a2b9b04105f5b5bc2f39bbd60d`；99项producer归档，不追溯称由后续Git commit生成 |
| 模型预检 | runtime commit [`83edff6608fc9db33ea90c3d04ce091705ee643f`](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/83edff6608fc9db33ea90c3d04ce091705ee643f/spaceserve/code/h20-window-20261027)；服务器61项实际部署与Git blobs一致；75项动态模型manifest `d542d1acbf078ee2cebe466df732a6f1f0c618851931960a3597845eab49a138`绑定实际Git部署回执 |
| 终态采集 | 独立collector commit [`6a9dd8c58231a82d0be498b832c85b5ccac7ab35`](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/6a9dd8c58231a82d0be498b832c85b5ccac7ab35/spaceserve/code/h20-window-20261027/tools)，不修改模型ROOT或其checkout83 |

模型实际运行于北京时间15:24:42–15:41:18，controller3624713/child3624718，exit0。实际终态原件确认父子消失、owned为空、GPU4零显存/零利用率、compute为空、专属MPS stopped且100%。启动前预约、输入与实际设备身份均经核验；这些快照不作为后续新GPU执行的权限。

261项采集原件共384,109,378字节，已下载本地并逐SHA核验；同时核对75项producer、170项numeric consumer及collector五项Git blobs。审查使用的26份数据与4份集成源副本，明确记录旧本地不可变来源，并逐SHA对应本批实际CPU核验的2564项输入，不沿用历史PASS。

- [独立G3原文](../reviews/g3-model-preflight-subagent.md)与[496项绑定Gate](../evidence/G3_MODELS_APPROVED.json)：仅模型/固定输入/机制，不授权formal或新GPU。
- [逐文件采集清单](../evidence/model-attempt1-files.json)、[本地传输核验](../evidence/model-transfer-local-verified.json)、[实际终态](../evidence/model-attempt1-terminal.json)。
- [实际Git部署](../evidence/GIT_DEPLOYED.json)、[collector版本与命令](../evidence/collector-git-identity.json)、[实际运行开始](../evidence/MODELS_ATTEMPT1_STARTED.json)与[退出](../evidence/models-attempt1-exit.json)。
- [数据及集成源实际pin映射](../evidence/model-frozen-data-source-mapping.json)、[原零请求启动失败](../evidence/model-launch-failure-0/COMPLETED.json)。

此前一次批准文件SCP失败后主执行未先检查传输结果就调用启动器，在模型guard放行前因缺失G2文件退出，产生模型请求0。原四文件及exit1均保全；经独立G1/G2批准才执行上述唯一313接续。此前CPU输入回执刷新不是额外模型重试。

## 未完成项与解释边界

1. 正式计划54单元、5400 formal＋1080 warm；本批实际正式单元0、正式请求0。模型G3完成前已错过201分钟正式入场门槛，不降低门槛或缩矩阵。此项是“未启动”，不计为系统失败率，也不能归因于显存、通信或调度退化。
2. `min_pixels/max_pixels` kwargs被忽略；证据针对实际448×448 COCO输入、每图256视觉tokens。固定主题与reference一致性不构成通用自然图理解质量保证。
3. encoder mask不证明decoder互斥或完整SM分区；MPS边界快照不能排除所有瞬态外来client。
4. 无新正式性能结果，不把诊断时延或kernel overlap当作off性能、SLO、瓶颈定位或严格收益上限。
5. 后续需要足够有效窗口与版本冻结后完成独立完整矩阵；EPD/公平PD继续独立准备，不能与Space正式测量并发，不能拿不同模型/卡数直接排名。两个项目完整目标均未完成。

本报告为待数据/结论G4审查版本；模型G3通过不等于本报告已审、数据已发布或项目已交付。
