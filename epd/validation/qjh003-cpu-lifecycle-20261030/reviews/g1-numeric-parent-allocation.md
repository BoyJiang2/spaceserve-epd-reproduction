# Actor实际UUID乱序分配校准 — 独立G1

reviewed_at_utc: 2026-10-29T19:56:26Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_CONDITIONS / BLOCKING 0，仅本地父adapter/fixture内部接线校准。无实际Ray/GPU、远端、发布或完整backend许可。**

精确numeric-parent-allocation-amendment.md SHA `4208f6db84611e1e758b70e929963fef0d3a9512b52a5e777ef974d0213877a2`。只读核计划、numeric_driver_interface_inspection及既有execute/cache/parent backend合同；独立逐本地Git3a3对象确认inspection列Worker/config/numeric_cache三原件SHA和工作区字节全部相同，没有导入Ray/Torch、执行项目/测试、网络、SSH、GPU或改源，仅保存本审查。

## 认可理由与接口保持

Worker的ray.remote(num_gpus=1)、ray.get_gpu_ids与实际CUDA设备初始化代码只说明Ray会分配一个设备，不能证明create顺序一定为请求的A/B/C UUID。原逐预期UUID断言虽保守拒绝，却可能因无依据顺序假设使真实可用实现失败；不能用手动覆写CUDA_VISIBLE_DEVICES或重建actor掩盖。

改为每个slot先父WAL/fsync记录允许的固定三UUID集合，创建恰好3 fresh actor、逐次用真实identity验证actualUUID属于允许集合且本组不重，并原release.register成功后才继续，是更小且准确的校准。实际集合完整后按原固定UUID列表返回，numeric_unit.execute仍按UUID建立valid映射、使用原transfer_vector，36实际计账/源目标方向/kv-ve/repetition/seed不变。父不把期望slot称为实际分配，也不另增ordinal账或第四actor修补。

## G2必须落实

1. 保留逐创建CREATING/fsync→RPC→真实returned_identity（含失败时原件）→allowed/duplicate/原scope/source/profile/proc/NVML核→release.register→下个slot的顺序。不能只从driver返回的gpu_uuid字符串证明真实分卡，原sidecar/proc/NVML/Worker身份要求不变。
2. 任一duplicate/foreign UUID/错scope/source/profile/EOF/未返回创建即fail-stop，不再创建、allocate/copy、重试或换GPU；pending intent要保留slot/allowed集合及已收到的实际identity，不因不符合预期就抹掉可能已活的actor。旧siblings/依赖留父真实表，未知归属按v3失败收口。
3. 三次实际身份全部注册后才要求集合=固定预算集合并重排返回；没有“缺一个再补一个”的分支。实际head仅可见三张已审批卡、driver actor num_gpus=1、max_restarts/max_task_retries=0与Ray的CUDA_VISIBLE_DEVICES实际设置，仍由后续源码/实际Gate验证，本设计不证明它们已运行。
4. 本地回归至少使实际UUID返回顺序与slot相反/乱序（建议覆盖六种排列），断言父register顺序遵从实际reply、最终返回/identities按固定UUID稳定、原vector完全不变；duplicate/foreign/profile不符时不能出现第四次create，且pending/已注册siblings保留。mock仅证明adapter合同，不称Ray allocator真实证据。
5. 原同一Claim/36 ledger/三GPU/0模型/1680+120/无重试、copy前父mapping fsync/close依赖/真实创建quiescent证明全部保持。不能用本组乱序校准豁免旧IPC未释放组，不能据NVML暂空或映射表空签released。

这是创建顺序的内部接线校准，不改变实验请求/模型/性能预算或资源数。只先本地实现/CPU反例，独立G2/Git-first及实际CPU-only Ray/IPC Gates仍需完成。Space3a3及04窗口部署/正式优先，本源不改Space、不发布main、不占远端CPU/GPU，不与正式GPU并行。

GATE_RESULT: {"gate":"G1-numeric-parent-allocation","decision":"APPROVE_WITH_CONDITIONS","blocking":0,"plan_sha256":"4208f6db84611e1e758b70e929963fef0d3a9512b52a5e777ef974d0213877a2","scope":"local_actual_UUID_mapping_adapter_amendment_only","GPU_approved":false,"native36_executable":false,"experiment_budget_changed":false}
