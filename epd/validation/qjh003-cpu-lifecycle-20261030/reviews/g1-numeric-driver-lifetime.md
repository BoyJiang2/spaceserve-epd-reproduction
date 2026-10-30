# Driver生命周期候选/最小取证范围 — 独立G1

reviewed_at_utc: 2026-10-29T22:11:53Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_CONDITIONS / BLOCKING 0，仅本地0GPU生命周期取证实现/CPU反例准备。未冻结GPU driver策略，不授远端Ray运行、GPU或native36。**

精确numeric-driver-lifetime-proposal.md SHA `653064df47b556d6079ff11a67fc42a604b5277534623711c02bb5d6527860b0`。只读核候选、v3/原backend合同及本地官方Ray2.10 worker.py/actor.py/namedactors原件，独立逐三文件重算raw SHA及Git blob均与source-evidence/driver-lifecycle-source-pins.json相同。没有网络、SSH、测试/项目执行、GPU/凭据读取或改代码，仅保存本审查。

## 策略裁决：不能直接用non_detached＋事后unconfirmed替代既定依赖控制

原backend v2已规定三个fresh actor使用lifetime=detached，以让driver退出不拥有actor释放顺序。worker.py1795–1851确有解释器退出shutdown hook，调用disconnect/shutdown_driver并处理_global_node；namedactors文档明确detached越过driver生存期且不按普通actor自动GC。这些是源/文档事实，不是任何实际host的存活或quiescence结果。

在现有“父保存唯一mapping/按importer先于exporter释放”合同下，改为non_detached并允许driver死亡自动owner-GC，不是严格等价简化：自动GC可能在父有机会确认importer退出之前让exporter终止，事后标FAILED_RELEASE_UNCONFIRMED不能逆转发生的顺序，也不能把未知GC当父按序释放。正常路径先由父收口再driver退出可成立，但不能据此证明异常路径保持原设计。故**不批准直接将默认non_detached作为已合规GPU路径**；它可作为0GPU行为对照，其异常结果如实记录，但后续若想改变GPU故障合同必须重新明确裁决，不能隐式放宽。

更小的优先方向是显式detached＋普通连接既有私有head的driver，不先修改/注销Ray原atexit hook。连接既有head的Node是connect_only语义，shutdown出现kill_all_processes这一行本身不证明会杀父head；需要核该driver实际Node是否持有进程及真实退出结果。不要为“没有显式shutdown”承诺伪造安全，也不要在没有必要证据时新增hook monkey patch。detached只解决driver ownership存活的一部分，不证明pending创建取消/最终quiescence。

## 最小取证工作是否必要

真实CPU-only Ray lifecycle Gate本来就是v2/v3必需，不存在仅凭默认Ray语义/源阅读就同时证明正常退出、driver故障、pending创建和父pidfd收口的更小等价方案。建议把本候选落实为**既定生命周期Gate中的有限场景**，复用现有Node/registry/collector和父身份清理，不创建新常驻研究系统/额外自动任务/通用RPC框架。

候选normal-exit与创建返回窗口受控退出×明确non_detached/detached共四个CPU场景，单次无业务重试、合180秒工作+120清理，范围合理。可以源码/文档优先确定detached为待验证首选，但不因这样就跳过其真实创建窗口证据；non_detached场景只作说明行为的对照，不升级为GPU许可。实际预算耗尽/状态无法确认则保留失败，不自动延时或减少验证等待。

## 实现G2/实际CPU前置条件

1. Ray导入前用包元数据/固定路径读取实际worker/actor/node/services/parameter pins，不用find_spec(ray._private.worker)等会先导入父包的方式假装pre-import核验。源码不符拒绝，不修改安装Ray文件；实际运行环境/relocation/pth/interpreter/根路径也需单独核，不能套用Space env验证。
2. head num_gpus=0/CUDA_VISIBLE_DEVICES空，actor num_gpus=0，禁止Torch、EPD Worker、CUDA IPC、权重/model和NVML初始化。Ray自身硬件发现/导入分支须源审并记录；不能只用0配置宣称根本没有任何硬件查询。本CPU取证不抢Space GPU，不触UID2071或他人任务。
3. 唯一私有Node/address/namespace/root/run/nonce、create前WAL、实际ActorID/namespace/GCS状态/真实父链PID/UID/start及前后原件，持续观测迟到创建。不能凭名字或单次字典/NVML空替代身份；原head无reaper/driver不创建新head，既有registered-spawn原件保留。
4. CPU probe不直接复用要求GPU UUID/NVML的NumericRelease来造CPU释放PASS；可复用已审稳定pidfd/原父进程归属合同，但具体CPU actor及daemon收口接线必须源码G2。普通/故障两条路径的driver内置atexit、Node all_processes、actor/GCS及实际子进程原件均保留。
5. pending创建未知时不能启动额外inspector/新driver接管或ray.kill通用兜底来伪造quiescence。父可用经审的既有GCS只读元数据与持续proc/sidecar证据；必须指定真实调用接口/超时/来源，不接受“GCS状态已核”标签。无法确认归属/将来创建即FAILED_RELEASE_UNCONFIRMED，记录真实残留/预约影响并按300总界失败，不将失败当继续占用授权。
6. 实际进程终止/查询须可验证UID/root/run/start/父链、稳定pidfd、同一单调deadline/取消，不能全组清理或按同UID/进程名清理。每scenario一次；不清其他head或本项目其他旧批。
7. 单核CPU50nice10/工作180+cleanup120且实际窗口fresh有效。该计划本身不授远端操作，须本地实现/有意义CPU反例、独立G2/G5/Git-first/指定commit部署/实际执行审批与CPU生命周期G3。当前不触服务器，不变Space24b/正式54/201或模型三卡/36预算。

候选明确不把0GPU探针替代完整backend/native36/PD性能目标，正确。后续只有真实生命周期证据审查后才能最终冻结driver策略、官方Worker/probe/handler/连续collector/dispatch和GPU Gate；本G1仅允许本地准备。

GATE_RESULT: {"gate":"G1-numeric-driver-lifetime","decision":"APPROVE_WITH_CONDITIONS","blocking":0,"plan_sha256":"653064df47b556d6079ff11a67fc42a604b5277534623711c02bb5d6527860b0","scope":"local_zero_GPU_lifecycle_evidence_design_only","default_non_detached_GPU_approved":false,"Ray_shutdown_hook_patch_approved":false,"remote_CPU_execution_approved":false,"GPU_approved":false,"native36_executable":false}
