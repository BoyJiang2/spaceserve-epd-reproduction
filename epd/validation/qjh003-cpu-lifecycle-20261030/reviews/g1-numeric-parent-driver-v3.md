# Native36父→driver v3 — 精确独立G1复审

reviewed_at_utc: 2026-10-29T19:29:44Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_CONDITIONS / BLOCKING 0，v2传输B1已在设计中闭合；仅本地源码实现/CPU测试范围。**

精确计划numeric-parent-driver-plan-v3.md SHA `91ffff61ac1e8bf338c2634fd1500b5661fcef0a8104f5933aaf80dd826654c9`。原v2计划及g1-numeric-parent-driver-v2.md REQUEST_CHANGES/B1保持，不覆盖。只读核v3全文、原审及既有numeric_unit/cache/release合同，没有测试/项目运行、网络、SSH、GPU或改实现，仅保存本审查。

## 设计B1闭合

v3明确私有继承socketpair两端先setblocking(False)，4字节network-order长度前缀及1..1MiB严格UTF8 JSON；不再Connection.send/recv或pickle。非阻塞send/recv只推进当前帧offset，EWOULDBLOCK回select，select最长50ms并查同一单调deadline与取消。prefix先验证长度再exact body，不读至EOF才限制大小。相同帧offset续传不是业务operation重试，EOF/坏帧/超时/错scope seq action/状态即FAILED锁定，不再发业务请求。该机制能让实现避免原poll后阻塞整帧/背压的设计缺口。

大小先界定、payload先编码、拒NaN/重复key/非object/尾随数据与严格固定schema合理；G2应实核长度包括UTF8编码字节而非字符数，send返回0/半prefix/body/InterruptedError/BlockingIOError均有限处理，编码解析前后再查取消/剩余deadline。不以本设计批准推定实际实现已经满足。

测试要求明确实际本机非阻塞socketpair分帧/短读写/背压/EOF/超时取消，不再仅Mock poll；这些实际local IO也不是Ray/POSIX目标机生命周期或GPU Gate。现阶段无需执行这些测试，由主导本地实现后形成原件再独立G2。

## partial actor / driver死亡的失败收口

父唯一execute/Claim36计账/release/Node/NVML/WAL保持；逐create_actor前CREATING fsync、真实identity register成功才下个创建。copy父mapping/fsync并再次workcheck后才driver调用，close/known直接父release不依赖transport。这比旧三op登记桥少一套账，符合原v2约束。

v3已明确CREATING未归属/仍可能创建时，不能以driver退出、NVML暂空、父registry空推断无未来actor；只有真实创建quiescent、实际本namespace/name Ray/GCS状态及已验证进程/context全收口才released/停head。driver死亡且无法证明pending终结直接FAILED_RELEASE_UNCONFIRMED，保持真实head/未知事实，不自动启inspector/driver恢复，不无限延期。旧IPC依赖不因本组CREATING而豁免。这闭合了原审提出的关键限制；真实Ray/GCS查询与进程/NVML必须实际验证，不凭名字/状态字符串认领或伪造quiescence。

有限失败不是释放成功也不是继续占用授权：真实剩余context/进程及预约影响必须报告。若未具备实际证明方法，GPU入口保持拒绝，不能为通过而降低条件。

## 后续G2需核的接线条件

1. 原numeric_unit.execute的create_group/call/close/known_identities合同及唯一36实际扣账不变；fixed operation/严格seq/run/nonce，driver不有head所有权、不因finally停止父head。
2. fsync成功之前不发创建/copy；record之后deadline或取消到达时不发新operation，已写mapping继续保留用于保守cleanup。ACK只表示协议响应，完整native回执由原execute核，不构造copy PASS。
3. work1680与cleanup120均用同一claim总期限；driver的实际Ray call/actor创建亦须剩余timeout约束，不能只让父socket有界、driver无界持续新工作。transport FAILED不阻止父直接close既有已知actor，但也不能清空pending/依赖。
4. 真实head后代/proc/NVML/sidecar、官方Worker/numeric probe、完整dispatch与最终release仍待完整接线。小协议/source G2或本机socket测试都不等于native36 executable或公平PD结果。

本G1只允许本地EPD实现/CPU注入与本机非阻塞socket测试，不远端、不Ray/Torch/GPU、不动Space3a3/已审bundle/main/请求预算。真实CPU-only Ray及native36 CUDA IPC/公平性能仍另审Gate，不与Space正式GPU并行。

GATE_RESULT: {"gate":"G1-numeric-parent-driver-v3","decision":"APPROVE_WITH_CONDITIONS","blocking":0,"closed_findings":["v2-B1-bounded-nonblocking-framed-transport-design"],"plan_sha256":"91ffff61ac1e8bf338c2634fd1500b5661fcef0a8104f5933aaf80dd826654c9","scope":"local_parent_backend_and_small_nonblocking_protocol_design_only","GPU_approved":false,"native36_executable":false}
