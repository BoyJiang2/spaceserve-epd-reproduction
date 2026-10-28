结论：APPROVE_WITH_NITS（仅无MPS的有界native兼容诊断G1）
BLOCKING：0
reviewed_at_utc：2026-10-28T21:01:39Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

已只读复核最新sm-driver13-port-plan.md。同意简化为无MPS的独立native CUDA进程；此最终范围不要求启动MPS或创建intent/token/pipe。旧失败run只读，原probe与assets原库字节不改，日志写独立staging。

固定官方README确实提供MASK_OFF端口探测方法，但这不证明CUDA13已受支持。该机制写CUDA stream内部布局，错误offset可能破坏当前上下文，必须保持下列边界：

- 仅指定空闲GPU0、原UUID/boot及有效本人CPU/GPU票；候选0,8,...,248最多32个，每候选新进程/新上下文、最多3秒，单元180秒工作加120秒收口；不并行、不扩大搜索。
- 超时、SIGSEGV/abort、CUDA错误、异常GPU占用或释放不确认时，停止整个诊断，不继续跳过挂起offset。只有明确普通数值/SM集合不符合且上下文正常释放的失败才允许下一候选。
- 每候选结束确认自有进程退出及GPU0显存/compute为空；TERM/KILL仅用于实际已登记并二次核验PID/startticks/UID的自有进程。未知身份不清理，不重启GPU、driver或共享主机。
- 首个成功仅为候选offset，随后最多三次独立native复验，严格验证子集、清零恢复全SM、重施同subset及真实释放；任一失败停止，不把退出码0代替机制证据。
- 每次保存offset、原始stdout/stderr、PID/startticks/ctime/exit/SMsets、boot/UUID以及库/probe源码和二进制SHA；旧失败、claim和运行源码不改写。

本G1只批准上述设计范围。实际运行前仍需绑定精确工具/库/probe、boot/UUID及停止规则的新G2和真实批准。native候选通过也不证明MPS或服务encoder stream；相关MPS三次与服务mask仍须后续新numeric/model及独立实际G3。模型与formal不在本次批准范围。

后续传播MASK_OFF须另审最小runtime/config变更，重新进行numeric实际验证，不追溯将首次失败记PASS。201分钟formal入场及08:58清理边界不变，不能为赶时间缩矩阵或降低机制要求。

NON-BLOCKING：将异常立即停止规则作为后续G2的明确实现检查项。QUESTIONS：无。

本次只读检查文档及历史源码说明，没有执行诊断、测试、SSH、网络或GPU操作。按主代理明确请求仅保存本审查文件。

GATE_RESULT: {"gate":"G1","scope":"bounded_native_MASK_OFF_diagnostic_without_MPS_with_abnormal_exit_stop","decision":"APPROVE_WITH_NITS","blocking":0}
