# Claude 额度耗尽后的独立审查接替

用户于2026-10-23明确要求在AGENTS.md记录：Claude额度耗尽时使用subagent接替。主执行者已更新 `D:\Documents\codex\AGENTS.md` 第3.2.1节。

失败依据：`reviews/claude-availability-20261023.json` 和 `reviews/g1-g4-h20-adoption.json`，均明确usage_limit_reached，而非仅凭HTTP429推断。

此次接替实际任务：

- `/root/fallback_g1_g2`：G1与G2，依据 `g1-h20-plan-focused.md`、`g2-h20-code-focused.md`。
- `/root/fallback_g3`：G3，依据 `g3-h20-mechanism-focused.md`。
- `/root/fallback_g4`：G4，依据 `g4-results-focused.md`。

三个subagent均以独立上下文启动，不传递聊天原文或凭据；每个均被明确要求先读AGENTS，且不得改文件、运行实验、访问GPU、SSH、发送外部消息或读取凭据。仅通过本地读取、目录查看和文本匹配完成证据审查。结果回报主执行者，由主执行者逐字归档，不让审查者修改实现。

原提示词中Claude字样指优先审查者，此次实际审查者为subagent，必须按真实身份标注；G1/G2补审不冒充事前批准。审查格式、BLOCKING处理和G5批准标准不变。该接替安排本身不是任何Gate批准。
