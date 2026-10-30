# Native36 父监督器 backend → 独立 driver（v3 有界字节传输）

替代numeric-lifecycle-rpc-plan.md候选中的driver→父三操作桥，旧候选与G1补充裁决保留。继承backend v2/Node v3、三卡36原生copy、0模型、1680工作+120清理、零重试/Git-first/真实Gates。只申请本地实现和CPU注入测试；Space3a3及已审bundle保持冻结，不GPU或远端。

## 唯一状态与接口

numeric_unit.execute始终在父监督器中执行。它是纯Python，numeric_cache顶层无Torch；父保留真实Claim和唯一36计账、NumericRelease.known/dependencies/released、head Node/已登记后代、NVML采样与WAL。独立driver只连接本次loopback地址/namespace并持有Ray actor refs，不拥有head，不调用shutdown/head cleanup。父backend实现原create_group/call/close/known_identities接口，不能另增授权ordinal账或driver finally清空父状态。

create_group由父逐UUID向driver发create_actor RPC，而不是等待一次不可观察的三actor集合。每个创建请求前，父先fsync记录本次namespace/name/group/UUID/预期stage/source/profile与CREATING状态；driver的实际actor身份返回后，父NumericRelease.register成功（含实际proc scope/WAL）才发送下个actor创建。三个已注册且UUID一致的fresh身份才返回原execute。仅name不是归属证明，actor的source/profile/真实UUID/PID/sidecar/实际NVML仍需现有独立验证。

backend.call仅接受allocate/prepare/copy/sync固定operation。copy时先从已经登记的source/target真实identity取依赖，核transfer source_uuid/target_uuid及原prepared source，父直接release.mapping_possible并fsync；再次检查剩余work时间后，才发driver call(copy)。失败/无ACK/EOF不重发、不重建actor。copy完整native回执仍由原execute验证；ACK不当copy PASS。

backend.close直接由父release.close核pidfd/proc/NVML，遵循importer先于exporter，不交driver finally，不用ray.kill/head.shutdown代替。known_identities直接返回父release表。父的finally仍走原execute/全supervisor收口，不因为driver退出丢失mapping记录。

## 有界RPC与不明partial actor

父→driver仅用私有继承socketpair，每端在交付使用前setblocking(False)，不用multiprocessing.Connection.send/recv或pickle。固定4字节network-order长度前缀＋UTF8 JSON，长度1..1MiB，固定scope(run_id/nonce)、严格递增seq、限定action和payload键。父request先写既有WAL，再以select最多50ms周期检查全局单调deadline与取消；每次非阻塞send/recv只推进当前帧offset，EWOULDBLOCK返回select，不能阻塞等待完整帧。半帧/背压可在同次操作剩余预算内继续字节offset，这不是业务operation重发；断链、错长度、EOF、超时、错scope/seq/状态或JSON异常则锁定transport FAILED，不再发任何新业务请求。payload先编码并在最大长度内，读取先限前缀，再限该长度的exact bytes；不得读到EOF才决定大小，不接受NaN/重复JSON键/非object/尾随数据。close由父直接执行不依赖driver。

driver actor创建与identity返回之间无法靠Python保证无缝。父CREATING原件及持续owned-head后代/proc/NVML/sidecar采样必须覆盖这个窗口。发生未返回创建时立刻禁止下个create/allocate/copy，此时本组还未进入任何allocate/IPC，不能伪造缺失identity或把CREATING当已注册。仅对实际已证原父链+root/RUNID+UID/boot/start的本次进程可走无IPC bootstrap pidfd清理；未知归属不信号、不签released。CREATING未归属或仍有可能继续创建时，单次NVML空不证明安全；必须有真实创建quiescent证据（已知driver无在途创建、实际Ray/GCS对应本namespace/name状态与所有已验证进程/contexts均已收口），才能签released并停本次已验证daemon。driver死亡而未能证明pending创建被终止时，直接FAILED_RELEASE_UNCONFIRMED；不能以driver PID退出/NVML暂空/父字典无记录推断无未来actor，也不自动启新inspector或新driver恢复。正常三actor身份已逐个确认且无创建在途之后，仍须所有已确认PID/context实际释放。若归属/context无法确认，则FAILED_RELEASE_UNCONFIRMED并保留head/进程事实，按原1800边界退出与通知，不无限延期，不通用kill兜底。上一组importer/exporter未确认时本来就禁止进入新create_group，不能用本组CREATING豁免旧IPC依赖。

## 验证与边界

本地测试须核原execute调用合同、每actor创建前WAL、register后才下一create、mapping WAL前失败不发copy、record后deadline到达不发copy、driver死后父表仍在、close不经过transport、错误scope/seq/action/超限/EOF/timeout后无重发、partial actor明确失败且不伪造release。只先实现可接完整backend的父端适配与有界小协议，不凭mock称完整生产路径已齐。

后续必须继续接实际driver官方Worker/numeric probe、Ray身份/并发NVML/head后代及完整生产dispatch；本地mock/source G2只代码证据。真实CPU-only Ray生命周期Gate与真实native36 CUDA IPC另审新窗口，GPU仍failclosed；不改Space请求/源码/预算，不与Space GPU正式并行。

本v3修复v2审查中的Connection半帧/背压阻塞B1，并明确CREATING quiescence失败分支；原v2和审查原文保留。新增传输测试必须以真实本机非阻塞socketpair验证分帧/短读写/背压/EOF/超时取消，不能只用Mock poll当作有界证明；仍无Ray/Torch/GPU或远端。
