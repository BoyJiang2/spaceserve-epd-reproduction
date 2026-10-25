> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-export-cleanup-subagent.md) SHA256 c4b41785268e4a2fa9086fcce24ce168faaba76935ddb6d17cf28ce4d23bf249。原数字及解释不变。

# G2：导出完成等待与pidfd兼容清理

实际审查者 /root/profile_runner_review，只读，quota接替同批；提示g2-export-cleanup-prompt.md。
结论APPROVE_WITH_NITS，BLOCKING0。读取代码及Linux日志，确认stop请求后/服务终止前等待实际worker数量、唯一gzip、稳定size、完整CRC/EOF和SHA；缺失/重复失败，2项CPU测试覆盖延迟footer/缺worker/重复。stop_server有界poll保留全体身份校验及TERM/KILL前复验，3项实际身份测试通过。
NON-BLOCKING建议返回前再整体查唯一性，防另worker等待期间迟到duplicate；Codex已采纳返回前对全部PID检查唯一文件/同path/同size，其他行为不变。实际trace内容仍须后续分析/G3。本次可cold/restart，formal仍须G3/SM并重冻结SHA。审查者未改文件/运行代码/访问GPU。
