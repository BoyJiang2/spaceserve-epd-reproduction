decision：APPROVE_WITH_CONDITIONS
BLOCKING：0（设计范围；实际执行前置仍未完成）
reviewed_at_utc：2026-10-29T05:50:13Z
审查者：独立 Codex subagent /root/handoff_cpu_review

已只读核space-temporary-bundle-recovery-plan.md、原prepare_space_temporary实现、既有临时scope G1、当前AGENTS及原deploy三文件与readback。没有测试、外网、SSH、GPU、凭据读取或源码修改，仅保存本审查。以下原失败证据结论与新G1设计批准分别成立，不把其混为恢复已成功。

一、actual失败证据：APPROVE / BLOCKING0，仅认可实际失败性质。

三原件逐bytes/SHA与readback嵌入text完全匹配：claim1915B/SHA834b61fb5bbef99921993a029e9902c93e0e097047616b5da69cacbbf2226e65；log2105B/SHAe4a921ed4d13a1dc78d36ddcc2a6080616a93b3aefeab09bd80afd55667635dd；terminal819B/SHAb4dda733def170f1d7a840e4ee9160648b7f02c5dedaccac96c3972b78097584。terminal明确实际deploy exit1/TimeoutExpired、runtime9754419d570c97c08d40b7a7f674cead8707618b/config ebe8ae33a2bebd80da88328ef268900c459853bbb913857a311a88059acd1c8f，不是仅本地观察超时导致UNKNOWN。

log实际HTTPS git fetch在60秒TimeoutExpired，exit-15/elapsed60.4138616秒、输出fatal early EOF，并记录对自有session1194829/1194832及其startticks/UID的TERM。可确定“本次fetch超时且受控终止”，不能进一步确定网络/TLS/服务端的具体根因。原terminal的GPU_requests=0且deploy控制流没有prepare/CPU suite调用；GPU只读metadata不等于CUDA工作。

readback记录实际hostqjh003/UID2147/boot65f、HEADbeadff9c4cc4693cd2ea8675020f757e313659e8、status空、run/candidate不存在、GPU2 UUIDc005及0MiB/0利用率/compute空；仅代表该次观测，不可作为恢复时fresh资源状态。cleanup日志发TERM不单独证明所有进程现已退出，roothelper1194798终态仍须先只读重核；未确认前不并发恢复，也不按名称猜测清理。

二、新G1设计：允许本地维护实现与CPU-MOCK，条件通过后一次bundle传输/一次deploy-recovery。

该方案用固定本地bundle替换已失败的目标GitHub HTTP，保持Git来源与精确commit，比再试目标网络更小且可审计。原失败版本975、原claim/log/terminal和原窗口不能覆盖；新增C1只修改维护源码/tests与配置source_commit元数据，GPU source84及shared source须逐字节等同原已审版本。新C1必须先G2/G5/public push并核实际原字节；不能把尚不存在的C1记为已部署或把975失败追溯重标。

执行前须完整闭合下列条件，不需要重复索取用户已授权的例行准备许可：

- 保持原13:40:34.579–14:40:34.579绝对窗口和END-120，不刷新start或重置60分钟。CPU每unit原240+120及model原1800完整余量不变；不够则停止留断点，不挤压机制测试。实际GPU numeric/model仍须各自CPU/numeric及独立实际Gates，formal明确不允许。
- 本地生成精确C1 HEAD且以beadff为prerequisite的增量bundle；本地验证bundle、base/HEAD与SHA/大小后，固定路径排他传输≤16MiB。目标先核owned ancestry/无link/regular/UID/size/SHA、base存在、bundle verify和实际HEAD等于C1，再仅fetch该本地bundle/checkout/fsck/Gitclean。不能因bundle有额外ref或checkout失败而回退HTTP、换source或删除partial自动再传。
- recovery须精确绑定旧失败terminal/config/log/claim及原975身份，HEAD仍beadff clean、run/candidate不存在、原helper和fetch子孙实际退出、无本项目活动。旧文件全不变，新deploy-recovery证据排他；远端固定stage不复制vN或删除来绕guard。失败/UNKNOWN停止。
- prepare接受恢复成功链时须匹配C1与新config SHA，并保存旧975失败→C1恢复的关系；没有恢复的原deploy成功路径保持独立，不能泛化成任意失败terminal可跳过。新config除source_commit外逐字段与旧原件相同，第一次prepare/CPU冻结全C1，不继承旧run/PASS。
- fresh resource、hostUIDboot/CPU50nice10、真实GPU2空闲与原direct辅助scope全部保留。此设计不放宽foreign/unknown监督、PID/startticks/UID/session归属或未知拒杀；必要时先做已允许的只读终态核验。不得把其他用户票改成自己的许可。
- G2须覆盖bundle错误大小/SHA/HEAD/base、旧terminal/log/config不符、重复恢复/存在run/candidate、config非source变化、过期窗口和prepare链断裂；真实文件传输另保留精确argv、实际bytes及两端SHA。无需新增通用发布或进程框架。

本G1批准最小CPU恢复设计，不代替即将实现源码的G2/G5或目标实际结果审计，不授当前GPU执行许可。原失败已明确记录、旧guard不绕且新attempt独立，因此可作一次明确恢复；这不是对旧fetch的自动重试。

GATE_RESULT: {"gate":"G1","decision":"APPROVE_WITH_CONDITIONS","blocking":0,"scope":"single_CPU_Git_bundle_transfer_and_exact_deploy_recovery_design_only","actual_prior_deploy":"FAILED_EXIT1_FETCH_TIMEOUT","execute_now":false,"GPU_approved":false,"formal_approved":false}

未执行测试或远端检查；helper1194798终态、最终C1/bundle及fresh实际前置仍需后续验证。

补充只读释放证据复核 reviewed_at_utc：2026-10-29T05:51:29Z。
计划原字节SHA256：58fef2af37b0a4c2c9de63555f1604784f64df55c66692f31e4219c79bf54b42。
已读新增temporary-gpu2-deploy-process-release.json：observed_utc=2026-10-29T05:50:39.302272Z、原生只读/proc命令exit0，boot同65f；原helper1194798与fetch1194829/1194832三个实际/proc路径均exists=false。本轮旧原进程终态待核项据此关闭，依据是独立后读而非TERM日志；不将其扩大为全机无其他进程或恢复时fresh资源证明。最终C1/bundle/G2/G5及执行前fresh条件仍待闭合，设计结论不变。
