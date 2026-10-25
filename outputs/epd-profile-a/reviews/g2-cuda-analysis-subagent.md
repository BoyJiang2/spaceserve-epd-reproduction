# G2：CUDA时间线CPU分析

实际审查者：独立subagent `/root/profile_plan_review`，本批明确Claude额度耗尽后的接替。只读源码、3 CPU测试及日志，抽查真实SQLite；未执行完整分析、GPU实验或修改文件。

结论原文：**APPROVE_WITH_NITS。G2 BLOCKING：0。**

关联规则正确：同进程correlationId，runtime调用完整位于同线程同步worker NVTX内，允许GPU结束晚于CPU范围；每请求kernel时间取并集，共享batch只是曝光，不能求和成独占成本；baseline prefill不造独立E；交接间隔不称纯通信；迁移copy不按请求分摊。真实schema支持关联键，抽查EPD高负载kernel/copy均有runtime；六baseline trace无mixed prompt/decode批。

EPD三worker CUPTI deviceId均进程局部0。通过已批准runtime逐PID→物理UUID，再核trace PID集合，属于间接物理身份，不将局部0当同一物理GPU。

NON-BLOCKING：输出无runtime/无worker范围/未完全包含等跳过计数供G4检查；输出逐PID物理UUID及局部编号语义；补CPU SQLite fixture验证跨进程同correlationId不会串联且GPU可晚于CPU结束；拒绝mixed prompt批避免后续误用。

Codex已增加跳过计数、逐worker UUID与局部deviceId说明、mixed批拒绝。完整64请求/8 trace及最终解释G4待审，不批准因果结论。
