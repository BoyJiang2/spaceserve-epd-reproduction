# mp1隔离MPS数值诊断G3/G4

独立审查者subagent /root/official_epd_runtime_review_1104，2026-11-04；主执行者转送精确代码发布核验、fresh资源/旧MPS清点、两个client数值/UUID、真实control membership/身份、quit前空client列表、实际退出和post进程/NVML清点。无模型或Nsight执行。返回原文：

mp1窄范围 G3、拟报告 G4均 **APPROVE / BLOCKING 0**。

转送记录支持：两个指定client实际隶属唯一自有MPS server，在同一目标UUID上完成各自FP16数值操作且结果精确匹配；确认client列表为空后才quit，所有相关退出为0、GPU释放，另有post进程清点为空。该释放结论不再仅依赖controller退出推测。

报告可声明本次隔离MPS两client可用性与受控收口通过；不能据membership、驻留或数值正确推断计算重叠，也不替代模型、mask或正式性能验证。RPC本次日志完整与未实测超时分支的限制应分开写。

下一模型/Nsight诊断仍需新代码G2、精确发布及fresh准入，不能复用已退出的server身份或把本次预检当并发机制通过。

本审查仅依据主执行者转送证据，未独立读取、重算SHA或核验远端；发布G5仍待后续。
