# NumericParentBackend接线组件 — 独立G2

reviewed_at_utc: 2026-10-29T19:48:03Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，仅父端adapter源码/接口顺序；不授完整supervisor、真实Ray/IPC、部署或GPU。**

独立实际重算epd/runtime/numeric_parent_backend.py SHA `fb580319ef04a1a5b8c5457aada5e16829cfe457adac5faee4ec2266d33dd8a0`、tests/test_numeric_parent_backend_cpu.py SHA `3745317d1bb88c30036e810c882c392b329e833328b6c6d5a9aba4afcc5f8770`，与numeric-parent-backend-cpu-tests.json相符。只读核完整源码/测试、v3 G1、numeric_unit.execute、transfer_vector及NumericRelease实际方法合同和测试日志，没有执行测试/项目、网络、SSH、GPU或改源，仅保存本审查。

## 认可的接线与失败语义

- create_group先限制本次三UUID、最多12组、无pending、父release已无未释放身份。每个UUID先release.record(actor_creating)返回，保留intent，再before_send工作deadline核，RPC create_actor返回后保留returned_identity，核GPU UUID并release.register成功才清pending/下一个actor。所有动作在父，不将driver字典当known；没有另设36授权账。
- copy用完整冻结transfer_vector行和整数ordinal验证，目标UUID与本组source实际identity一致；先父release.mapping_possible（实际方法负责known/live及fsync），再before_send，才发driver call。原execute仍唯一负责claim.admit_transfer、源prepare/geometry/完整copy回执及完成36核验，adapter不自行造copy成功。
- create/call异常将backend.failed置真，阻断新工作；部分创建保留creating及已注册siblings，异常record不伪造身份/release。已fsync intent但未发RPC也保守保留pending，不把缺ACK变成不存在。
- close直接父release.close，不经rpc；cleanup=True允许failed后仅做实际收口，但timeout裁至父claim.deadline，已到deadline拒绝。known_identities返回父真实release表。importer先于exporter由原execute顺序及实际NumericRelease依赖共同约束，driver死亡不抹除父mapping。
- deadline限定有限正timeout；work扣cleanup_seconds并claim.check，WAL后再check确保remaining工作预算未被消耗。原Claim使用同一父单调时间域，实际与NumericRPC采用的时钟域仍须在目标runtime核实（本Linux设计中不能混跨host/自造clock基点）。

## 实际测试材料

日志实际10项distinct CPU接口/顺序mock tests OK/0.001s，JSON10/0fail/0error/0skip及最终两SHA一致。本审未重跑。覆盖逐actor WAL/register先于下一create、copy mapping先于RPC、mapping fsync失败/record后过期不发copy、failed后父close不依赖driver、partial actor返回失败留siblings与pending、原vector bool ordinal拒绝、旧组未释放不新建、creating record失败不联系driver及cleanup截止拒绝。

它们使用fake release/proc/actor/rpc，不是实际NumericRelease journal/pidfd/NVML或本机RPC+真实actor集成。不能把10 mock称为实际fsync/worker创建或生命周期已经通过。

## 非阻塞限制及完整接线条件

1. assert_no_unresolved_creation只核本地creating字段，不能充当v3真实quiescence证明。完整supervisor还须确认实际driver无在途创建、相应Ray/GCS namespace/name状态、真实head后代/proc/NVML/sidecar；driver死/响应丢失/NVML暂空/registry空都不自动released。未知pending须FAILED_RELEASE_UNCONFIRMED，不能据此停head或忽略旧IPC依赖。
2. 原execute作为唯一调用者是本adapter的边界。copy并未维护额外last ordinal/重复账，这是刻意避免双ledger；不得脱离execute对任意call宣称已经限制36实际提交。具体driver还须固定create_actor/allocate/prepare/copy/sync exact字段和官方Worker/probe、source/profile/UUID真实证明，非任意Python调用。
3. close失败时adapter本身不设置failed；原execute会捕获失败并进入只cleanup的finally，不再新工作。完整supervisor必须保持这一合同，不能捕获close异常后继续allocate/copy。可在未来完整接线中加明确fail-stop约束，但当前原execute路径不构成B。
4. create_group异常后release.record(actor_creation_failed)本身也可能失败并遮盖原异常。已创建的pending/父known仍留在对象中，但完整外层终态应同时保存原始失败和journal失败/实际原件，不能将未写成功WAL声称已持久化；也不能因record失败自动retry创建。
5. 真实RPC超时/EOF及driver在返回identity之前/之后死亡、取消、pending创建收口和实际release协作仍要集成测试/实际CPU Gate。当前无实际进程/库初始化，native36 failclosed；官方Worker与完整backenddispatch尚未齐，不能把组件批准当整体完成。
6. 不发布部署、不动Space3a3/main/bundle，不与Space正式GPU并行。后续Git-first/实际Gate/原始证据仍逐项完成；不改变三卡36/0模型/1680+120或公平PD目标。

GATE_RESULT: {"gate":"G2-numeric-parent-backend","decision":"APPROVE_WITH_NITS","blocking":0,"source_sha256":"fb580319ef04a1a5b8c5457aada5e16829cfe457adac5faee4ec2266d33dd8a0","test_sha256":"3745317d1bb88c30036e810c882c392b329e833328b6c6d5a9aba4afcc5f8770","scope":"parent_backend_interface_and_ordering_component_only","GPU_approved":false,"native36_executable":false,"deployed":false}
