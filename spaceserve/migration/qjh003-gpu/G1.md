结论：APPROVE（correctness客户端连接策略修复设计G1）
BLOCKING：0
reviewed_at_utc：2026-10-28T22:30:17Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

已只读查看model-http-failure-timing.json及现行correctness_suite.run。原始时序支持连接层失败的观察：C8首提交后约32ms记录ServerDisconnected、无HTTP状态；其余14项有HTTP200，服务计数14。该证据不能证明keepalive超时为唯一根因，也不能单独证明mask数值错误。

批准本地实现一次窄CPU loopback故障注入回归，以及仅correctness_suite客户端统一force_close=True的最小修改。reference与三组采用相同策略，不改请求顺序、C4/C8并发、prompt、图片、token、正确性阈值、313上限；不改profile/formal benchmark、server、模型或性能协议。

CPU回归仅允许自有127.0.0.1临时端口、有限请求与有界自有server fixture，禁止外网、模型与GPU。应明确验证连接身份/接受数：强制关闭模式每POST新连接、预定POST恰好一次；server故意断开时仍保留错误、不得自动重试。若通过故障注入重现pooled连接失效，只能称验证该故障类别，不宣称已经重现真实环境的全部因果。

G2须核实force_close只控制连接复用，保持原timeout、错误日志、取消传播和请求数限制；不能通过重发、吞异常或删除旧负例使结果通过。新增CPU测试及本机loopback实际执行需具体受审命令、时间上限和fixture终态证据。

实际恢复顺序必须为新G2及窄回归复核→G5/commit/push→新producer指定commit部署与源码SHA核验→新唯一cohort prepare及完整CPU60→新numeric精确G2与实际G3→新模型consumer/输入与代码G2→一次完整原313模型预检及实际G3/G4。预算、fresh本人资源、09:00结束/08:58清理均不变。

旧model失败、124尝试/123响应、远端exit1与本地transport4294967295及人工关闭本地挂起SSH的身份原件分别保留；不将远端失败改写为传输成功，不自动重试旧请求或旧model attempt。新成功也不能抹掉旧失败或将连接复用假设升级为已证明根因。

本窗formal201分钟入场期限已过，不启动formal、不缩矩阵、不拼旧48/54。当前只批准修复设计，不是直接GPU执行许可，各实际Gate须重新成立。

NON-BLOCKING：无。QUESTIONS：无。

本次仅只读本地材料及依明确请求保存审查原文，没有测试、HTTP、SSH或GPU操作。

GATE_RESULT: {"gate":"G1","scope":"uniform_correctness_POST_force_close_and_CPU_loopback_regression_new_producer_CPU60_numeric_complete313_subject_to_Gates","decision":"APPROVE","blocking":0}
