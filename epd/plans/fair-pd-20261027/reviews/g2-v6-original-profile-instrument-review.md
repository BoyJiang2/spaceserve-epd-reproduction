# G2 v6 independent review — original response

Actual reviewer: /root/profile_instrument_review. Read-only; no tests or compilation. Primary saved original response, 2026-10-27.

G2 v6：**REQUEST_CHANGES，BLOCKING 1**。v5 两项阻塞已关闭，CPU runner 尚需补退出保护。

已核验49项源码 SHA 全匹配 manifest `cfc9b65e…07791a5`，未执行回执 SHA 为 `329be215…ba3d2ef`；没有运行测试或编译。

两项修复成立：

- `selected_g3.py:25–60,215–243`新增实际 API→worker 身份映射、逐请求 response 身份及角色路径核对；baseline 冷启/重启各要求三个端点20/20/20及完整 round-robin。
- `preflight_guard.py:283–300`持久化实际 claim 双时钟与截止；`selected_g3.py:137–178,285–339`核有限时间、同 boot 锚点、会话/采样/release边界及跨系统释放顺序。

**B1 — 父 runner 被中断或异常时可能遗留独立子进程。**
`work/epd-pd-followup-20261027/v6/cpu_target_runner.py:233–270`启动 `start_new_session=True` 子进程后，仅处理 `TimeoutExpired`。父进程收到 TERM、INT，或等待/日志读取发生其他异常时，没有统一 `finally` 清理；子进程及已登记 helpers 可继续运行，且不产生终态回执。

最小修复：父进程捕获 TERM/INT并转入统一、有界清理；异常分支同样进入 `finally`。仅在 PID/UID/startticks/cwd重新匹配后处理自有子进程/helpers，保存实际退出或身份未知状态。新增真实CPU TERM/INT及等待异常回归，检查无遗留和回执归属。

NON-BLOCKING：描述中的 nice10 尚未在 runner 中设置或验证；执行前应明确由启动命令设置，并记录实际值。

当前 handoff/release 原件不齐，仍不得执行。修复后可再审条件性远程CPU验证入口；不批准GPU、模型部署或正式实验。

