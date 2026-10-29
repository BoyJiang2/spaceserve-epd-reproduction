结论：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-29T02:49:12Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

本次G1绑定numeric-orchestration-plan.md SHA256 6730137b450a94815012e47a3f0a22e86c09a60bf518db8ae5656a331a51e4b9。已只读核设计及相关identity/allocate入口；没有实现、测试、SSH、网络、GPU或Ray/Torch/NVML初始化。按明确请求仅保存本审查文件。

批准本地numeric_unit有限编排核心、numeric_cache窄接线及针对性CPU-MOCK源码。修改范围符合停止vN复制及不改普通资格/校准/通信路径的要求。身份独占sidecar与allocate二次调用的矛盾确实存在：numeric_cache.allocate当前再次调用worker.qualification_identity；限定numeric-only缓存是可行的小修复。

后续G2必须核实：

- 12个pair/载荷组严格来自原36有限向量，每组3次copy且三个fresh actor真实UUID一一映射；每次先admit_transfer、持久化submitted，再prepare/copy。发生任何失败不得进入下一次transfer/group，不能退款或重试。
- 一个durable claim和共同1800秒deadline，identity/分配/同步/退出/清理均计入；后端调用必须接受剩余时限，不能只在调用返回后检查deadline。GPU/资源预算及.65上限不改。
- identity缓存只接受同一worker自身实际capture的原始身份，绑定PID/startticks、UID/boot/run/source/deploy等原字段；不接受外部传入身份替代实际capture。显式identity动作重复拒绝，allocate内部只读复用已有numeric身份；sync在登记之后。普通qualification_identity和模型路径不缓存、不放宽。
- 原生source/target geometry、完整checked_elements/seed、身份及36项向量关联仍需严格核验，不能仅凭backend布尔成功。完整原件和失败原件均保留，不生成G3或生产PASS。
- 正常结束按同步、importer真实退出、source退出、unused第三actor退出顺序确认。失败清理须继续处理所有已验证兄弟身份；未知身份不信号，release不确认则阻断，不把Ray actor句柄消失视为PID/context释放。
- 当前backend只为可CPU验证的窄操作契约，模块导入无GPU依赖；真实Ray/NVML adapter与GPU授权、fresh预约、source/deploy及durableClaim前端另接、另G2。fixed_unit numeric/selected继续fail-closed。

允许在当前用户授权的纯本地范围内准备对应CPU-MOCK验证；实际执行需精确测试成员/时限及源码绑定，不运行远端或旧87套件、不伪称真实Ray/native机制覆盖。具体源码发布仍须独立G2/G5及Git-first。

本结论不批准目标CPU、GPU、预算扩大、完整controller放行或selected360。当前目标CPU被他人占用的写前拒绝保持，不据用户“nongpu”要求推导远端CPU许可。公平PD整体仍未完成。

NON-BLOCKING：无。QUESTIONS：无。

GATE_RESULT: {"gate":"G1","plan_sha256":"6730137b450a94815012e47a3f0a22e86c09a60bf518db8ae5656a331a51e4b9","scope":"local_finite_numeric_orchestration_and_numeric_identity_cache_CPU_MOCK_only","decision":"APPROVE","blocking":0}
