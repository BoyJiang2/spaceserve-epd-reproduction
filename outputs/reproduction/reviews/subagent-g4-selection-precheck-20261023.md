# G4 选择器代码预审（不含实际数据批准）

实际审查者：独立subagent `/root/fallback_g4`。Claude额度耗尽按AGENTS3.2.1接替；原始提示词 `prompts/g4-cache-fix-selection.md`。以下为审查结果存档；本阶段不是实际G4批准。

代码预审完成：未发现必须重跑补测的确定性逻辑错误；不作实际G4数据批准，原B1继续开放。

来源选择及计数自洽：summarize成对替换两台四角色低负载，另存旧行；compare_outputs同时切换基线和EPD，避免新旧交叉。verify_delivery区分15矩阵/50配置/15000正式的全归档与46配置/13800最终选用，旧低负载1200保留且被替代；有效配对5400、诊断1800、新低负载600一致。audit_cache_fix独立解码RGB SHA，检查实际缓存、PID、设备、boot ID和版本，设计足以检验RGB初态修复。

NON-BLOCKING：报告生成器应断言低负载输出配对精确来源集合，避免新吞吐混旧匹配率；加载cuBLAS应比较旧实际路径集合，不能仅以库数量称身份认证。

主执行者处理：两建议已在实际数据复审前落实。make_report及verify_delivery断言两target/case精确集合与600条；audit_cache_fix比较旧快照库路径集合。无新增GPU运行。

正式G4仍须检查实际四配置、16缓存快照/PID、摘要与输出配对同源以及原后续负载服务连续性证据。模板完成式文字受实际验收证据约束，本身不判为伪造。
