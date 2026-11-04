# 隔离MPS独立机制诊断G1

独立审查者subagent /root/official_epd_runtime_review_1104，2026-11-04。主执行者转送：官方66de079含enbale_mps.sh与两个EngineCore/EncoderProcess进程；NVIDIA MPS文档的跨context时间片边界；原无MPS诊断不改写。新方案为单卡/原模型与正式协议不变，在既有run内0700独占pipe/log、UUID限定daemon/client、先无模型两client数值与安全收口，再独立Nsight机制采集。不使用全局/tmp或sudo/系统配置，不操作未知daemon。代码尚未实现。返回原文：

调整后的独立机制诊断 G1 **条件式 APPROVE / BLOCKING 0**。不继续把无MPS trace当作跨进程并发验证，方向合理；原C4结果仍按其实际无MPS配置保留。

**现有条款不要求为此诊断再取一次用户确认。** AGENTS.md §1列明需确认的是模型、精度、GPU预算、正式负载协议或基线定义的实质变化；本次仅补足官方MPS执行条件、用于独立机制预检，未改变这些项目。旧“本诊断不启停MPS”的批准不能复用，须以本次新G1及后续精确G2为准，当前尚不授权直接启动daemon。

G2需明确：

- 独占0700 pipe/log、UUID可见性、daemon/server/client身份与出生记录，启动前检测冲突；发现未知服务或客户端不能quit。
- shutdown只作用唯一自有pipe，并确认其中客户端均为本run已登记对象；异常及截止前收口有明确预算。
- MPS下NVML可能不能直接反映每个客户端的GPU归属，应结合control查询与身份链，不以server驻留代替两client执行证明。
- 两client数值预检通过不等于计算重叠；后续Nsight仍须实际请求窗口、角色归属及kernel证据。不可用或归属不足就降低结论。
- 不以MPS替代mask，也不把新诊断追认成旧数据或正式baseline配置；正式矩阵的MPS条件另行冻结。

以上仅依据转送方案，未核官方文档或实际进程；代码、GPU预检及Nsight配置仍分别待审。
