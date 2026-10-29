decision：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-29T04:48:32Z
审查者：独立 Codex subagent /root/handoff_cpu_review
范围：EPD CPU资产重定位16–17点恢复设计；当前仅本地实施准备。

绑定计划 epd-relocation-resume-plan.md SHA256 0d98ae7211bd0bc0fe01d2cdbf0529e218ba079f4480370bff114d509cbdd4a2。已只读核原维护工具、七项测试源码、配置、原G2与actual apply审查，以及旧attempt五份原件摘要。未测试、SSH、网络、GPU、读凭据或修改实现；仅按明确请求保存本审查。

原工具17101B/SHA d403e7df8ab3b87406a5e841a3f41ff487f5f76a0ec7843c88786d1327604363，七测试源码SHA 363c88a106492a663646557d4d41e0cc5079bd7ca882463755040200c2b6bac2，旧配置13591B/SHA afab6795c25600d7fdfa3de215e30ab97ae367d81deb3897cc2a7f29f3e09a66。当前这三份仍是旧12点版本，本G1不是新16点源码已实现或G2已通过的证明。

旧失败性质核对一致：cfbfef09184d015d3dd137abc7ffdcf0800179d7 attempt exit1，原stderr在cpu_permission的其他CPU/整机预约冲突检查拒绝，早于stage/claim/资产写入。五份command/input/stdout/stderr/exit当前SHA与actual-review列值全部相同，stdout为空。认可“该attempt控制流写前拒绝”，不将其扩大为独立事后现场证明全部目录未变；未verify、不得覆盖旧失败或自动重试。

批准的最小变更是维护同一工具/config/controller的明确时间范围、not-before、源码pin和新本地attempt标签。配置61文件/56文本变换/3解释器链接、nested原IPC保留、flat副本改RUNPATH且NEEDED不变、固定stage排他、未知startup拒绝、终态fallback、CPU50/nice10/1GiB、原生-I-S-B及原120/60工作+30外层限制均应保留。不要借改窗口扩大为软件加载、导入环境、GPU/NVML、native36或selected360。

新G2必须核实的具体条件：

- 16:00–17:00北京时间硬编码成精确整数窗口，valid_from_ms=1793260800000、valid_until_ms=1793264400000；拒bool/非整数、反向或非预期窗口，now<valid_from写前拒绝，旧12点授权永不再次有效。END-120与完整单元预留仍同时成立，不能仅检查开始时落在窗口内。
- apply和verify各自fresh实际API无他人CPU/整机冲突、host/UID/boot/CPU与原进程/目录前置核验；16点空闲不能由当前或旧read推导。若资源或记录UNKNOWN则拒绝；本人17–20票不用于越过16点冲突或延长本阶段。
- 新controller的每phase输入、command、stdout/stderr、exit与源码/config SHA都使用新专属本地attempt；旧controller执行字节和旧原件保留。远端仍使用同一固定stage，已有stage/flat或源pin改变时拒绝，不删除/另建stage绕过，不将旧write-before拒绝当当前现场证明。
- 保留七现有测试，增加开始前、精确起点、类型、结束/完整清理余量边界的纯mock回归。新源码与config/controller精确闭合后须独立G2/G5、Git-first push及实际公开字节核验，之后才有条件在16点启动一次apply；仅实际apply成功且新鲜条件仍满足时首次verify，任何失败停止保留，不自动再开新attempt。

无需再向用户索取这项例行CPU维护的重复批准：既有用户“虽然后面的cpu没有预约 但是你可以随便用”覆盖合法空闲CPU准备，计划没有新增实验设置、GPU或他人资源使用。旧12点是原执行scope的自限，必须由新明确窗口与独立Gates替代，不能把原回执外推成未来许可。本G1批准设计与本地实施准备，目标执行仍取决于上述条件；此刻不授目标操作。

实际成功最多称静态资产重定位完成，不能称环境加载就绪、CPU suite通过、CPU_STAGED、native36/G3或fair-PD完成；17点Space优先及formal预算约束保持。当前没有需要新增框架或扩大到整套环境重建的理由。

GATE_RESULT: {"gate":"G1","plan_sha256":"0d98ae7211bd0bc0fe01d2cdbf0529e218ba079f4480370bff114d509cbdd4a2","decision":"APPROVE","blocking":0,"scope":"local_preparation_and_conditional_single_EPD_CPU_relocation_apply_then_verify_20261029_1600_1700_CST","execute_now":false,"GPU_approved":false}

未执行任何测试或远端检查；16点实际资源、最终新实现与目标结果均尚未验证。
