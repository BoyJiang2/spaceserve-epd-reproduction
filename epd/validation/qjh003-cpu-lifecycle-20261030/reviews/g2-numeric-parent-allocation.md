# Native36实际UUID乱序adapter修正 — 独立G2

reviewed_at_utc: 2026-10-29T21:45:46Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，仅已审G1的本地numeric父adapter分配接线修正，不授Ray/GPU/部署或完整native36。**

独立重算epd/runtime/numeric_parent_backend.py SHA `0d8c66cf288b7e1a108e1064beeb1fbd9c89208e2b55c558bea2db48ba0a045a`、tests/test_numeric_parent_backend_cpu.py SHA `428f7b673a4797c1d2adae9194723b01f30ee038e997ef24dd72497e4e22fa89`，与numeric-parent-allocation-tests.json相符。只读核完整最终两文件、allocation G1/计划、原父backend G2与原execute/release/vector合同和before/after日志；没有测试/项目执行、网络、SSH、GPU或改源，只保存本审查。

## 精确修正与不变量

create_group仍要求fixed三UUID参数、group<12、无未决creating且父release已无上一组未释放身份。逐slot循环恰len(self.uuids)=3，每次先父record(actor_creating)写name/namespace/group/slot/allowed三UUID/scope，保存creating并workcheck后才RPC create_actor。intent不把未观察GPU当实际gpu_uuid。

实际reply先保留returned_identity；提取actualUUID须在允许集合且本组未出现，才调用原release.register，成功后按actualUUID映射并清pending。三次后实际集合恰fixed集合，返回值依原self.uuids固定顺序重排。无第四actor、换GPU、手动覆写CUDA_VISIBLE_DEVICES、重试或根据slot虚构身份。

原execute仍是唯一36向量/claim ledger。copy接线未改：完整transfer_vector行、actual source/importer身份、父mapping_possible/fsync→剩余workcheck→driver RPC；close仍父release.close/known，failed后可只cleanup且不extend总期限。模型0/12组三actor/36KV-VE传输、WAL顺序、importer先释放、旧组未确认不新建和真实quiescence合同不变。

foreign/duplicate UUID或register source/profile拒绝均进入failed，留下实际returned_identity/pending及已注册siblings，不把失败reply抹掉当不存在，也不调用第四create。无真实identity或driver EOF仍保留slot与allowed集合，后续supervisor不能据registry空/NVML暂空签released。

## 实际回归原件

before日志实际11 tests/5 errors，错误Created worker assigned wrong GPU，保留了旧分配顺序假设无法处理其余排列的反例，不改名成PASS。after日志实际13 tests OK/0.003s，JSON after_exit0/13tests/6 permutations与两最终SHA一致。本审未重跑。

新六排列subtests使用不同actual reply顺序，核父known注册顺序等于实际reply、返回统一A/B/C、原vector完全不变、每slot intent三UUID且无假定gpu_uuid、事件顺序仍WAL/RPC/register×3。另foreign/duplicate第二reply拒绝恰2次create、保留A sibling及第二pending；register失败也恰2次调用、保留实际B identity。原mapping/deadline/close/partial/finite vector/旧组拒绝等回归保持。

这些是Windows接口mock，不是真实Ray allocator顺序、Worker/proc/NVML或实际NumericRelease fsync。六排列不能扩写成真实GPU分配已验证；name/slot/allowed集合只意图，不是实际归属证据。

## 后续条件与限制

1. 真实driver handler必须按新intent schema消费slot/allowed集合，同时num_gpus=1、无actor/task retry、私有head仅可见批准三卡，尊重Ray的CUDA_VISIBLE_DEVICES；实际身份还须source/profile/proc/sidecar/NVML，不能以字符串和mock代替。
2. 父creating清空只表示本地reply/register完成，不等于所有Ray/GCS创建已quiescent；真实supervisor仍须v3证明/失败收口，不得借本修正全局kill或绕过旧IPC依赖。
3. 原adapter已列限制继续：实际执行需原execute唯一调用合同；close异常后不得捕获再继续allocate/copy；异常journal自身失败要由外层保存原始错误/实际状态。当前本G2不签这些完整接线已完成。
4. 此两源未发布部署，完整driver/官方Worker/probe/生产dispatch仍待，native36 failclosed。Space冻结24b/main和第三方占用的实际状态由主导独立跟进，本源码不改Space、不新增GPU/预算，不与Space正式GPU并行。

GATE_RESULT: {"gate":"G2-numeric-parent-allocation","decision":"APPROVE_WITH_NITS","blocking":0,"source_sha256":"0d8c66cf288b7e1a108e1064beeb1fbd9c89208e2b55c558bea2db48ba0a045a","test_sha256":"428f7b673a4797c1d2adae9194723b01f30ee038e997ef24dd72497e4e22fa89","scope":"local_actual_UUID_mapping_adapter_delta_only","GPU_approved":false,"native36_executable":false,"deployed":false}
