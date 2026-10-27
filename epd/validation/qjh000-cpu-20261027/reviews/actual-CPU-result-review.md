# Actual target CPU result review — original independent response

Reviewer: /root/profile_instrument_review.

实际CPU结果审查：**APPROVE_WITH_NITS，BLOCKING 0**。UTC：**2026-10-27T14:01:56Z**。

已独立核实：

- 顶层receipt SHA为 f70435c4…21792d，claim、permit、commit及审批链匹配；没有用嵌套mock回执代替实际单元。
- 部署及运行前后51项源码SHA均与批准manifest一致。
- 76项源码测试ID与实际start/success集合完全一致、无重复或缺项：35＋19＋13＋9；零失败、错误、skip。日志包含五项真实POSIX退出场景。
- claim时预约与host probe分别约230.4秒、224.3秒新鲜，均在5分钟内；实际CPU50/nice10及子进程限制检查路径通过。
- 顶层耗时3.583秒，退出0；后续释放记录覆盖父、子及六个登记helpers，全部absent，tracked clean。

**唯一nit：**permit绑定的host probe原字节保存在 cpu-inputs/host-probe-original.json，SHA正确；同目录host-probe.json是另一种格式、SHA不同。请记录明确路径映射，勿将后者称为实际消费原件；不需重跑。

仅确认本次受限目标CPU验证通过。Torch UUID、Ray、vLLM实际布局、IPC及模型机制仍未验证，controller尚未接线；不授予GPU、模型或正式实验许可。可据此准备CPU报告与元数据，发布仍须相应G5。

## Primary disposition

Accepted. evidence-path-mapping.json identifies original remote bytes, the differently serialized stdout projection, and published paths. Published cpu-inputs/host-probe.json is copied byte-for-byte from local host-probe-original.json; the projection is separately named host-probe-stdout-normalized.json and explicitly was not consumed. No tests rerun.

