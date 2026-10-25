> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-mps-status-subagent.md) SHA256 cfb6cd77a4a9ab098507febf00686e9099bd040a39a2b682a038dfead61cfafa。原数字及解释不变。

# G2：空MPS状态兼容修复

实际审查者：独立subagent /root/profile_runner_review；接替原因Claude明确usage_limit_reached，见g2-model-runner-claude.json和epd-profile-a/reviews/g4-cuda-report-claude.json。提示g2-mps-status-prompt.md。

实际结论：APPROVE，BLOCKING为0。

已只读核对实际delta、五项CPU测试及Linux通过日志：
- 仅idle调用可接受完全匹配的Server not found；带API PID的加载后检查仍拒绝。
- 数字PID混合、未知错误及坏列继续拒绝。
- 解析前保存原始status；UID、root/runID、私有pipe、物理UUID及加载后非空客户端守卫保留。

本次仅批准该兼容修复及冻结预检链cold/restart诊断重试；不批准formal，不代表服务G3。审查者未改文件、运行代码或访问GPU。
Codex落实：失败cold目录及启动日志另名保留，重试前核查停止状态和GPU空闲，重新冻结代码SHA；模型、输入、profiler诊断范围与基准设置不变。
