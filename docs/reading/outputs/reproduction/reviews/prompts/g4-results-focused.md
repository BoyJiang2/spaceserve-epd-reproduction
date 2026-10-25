> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/reproduction/reviews/prompts/g4-results-focused.md) SHA256 40acfe03845aecab3d0a87f6956d9a6e9d782778796aa2d53e6204107866dd2e。原数字及解释不变。

独立只读审查，仅Read/Grep/Glob，不改文件，不运行命令、实验、SSH、GPU或访问凭据。项目根 D:\Documents\codex\2026-10-23\new-chat-2，先读 D:\Documents\codex\AGENTS.md。

仅G4统计/报告审查。读 outputs/reproduction/report.md、scripts/summarize.py、audit_matrix.py、compare_outputs.py、report/summary.json、report/output-comparison.json（只读统计段，差异索引无需全读）、report/delivery-audit.json、reviews/h20-fairness-facts.json。必要时抽查003/005一个baseline/EPD config、三重复summary及requests小片段；不要读取全部逐请求文件或epoch日志。

全目录46配置13800正式/920矩阵内预热；旧L20 EPD1800仅诊断，12000测量通过技术检查。H20新增16配置4800正式，失败零；003吞吐比0.89–0.99，005低高0.93/0.95，均不宣称加速。5400有效配对+1800诊断配对，输入IDs相同，正式输出不全同；固定服务134中包含7个旧EPD，3个Qwen语义oracle失败不算语义通过。TTFT为非流式server首token减client提交，TPOT首末/127；P50/P95合并300，吞吐三重复mean±sampleSD，NVML100ms采样峰值非瞬时峰值。sapphire3裸机DMA-FQ与损坏共现但未证唯一因果。

已知公平性疑点：首个单图配置20全局预热使EPD RGB缓存20，baseline三副本7/7/6，第一正式重复可能补充40个副本/图片对。其余配置继承前序缓存。源码策略相同不等于初态相同；没有额外开销实测，不允许据此定量归因。请判断这对哪些结论构成BLOCKING，是否需针对性补测或限定结论；用户固定协议不可自行变更。不要把technical passed当作最终验收。

最多18次只读调用；若无法验证具体说缺口，不循环请求未授权工具。输出G4 APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING（文件:行、证据、最小处理）、NON-BLOCKING、QUESTIONS。本次不替代G5。
