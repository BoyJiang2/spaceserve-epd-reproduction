# CPU Ray/GCS 支持组件与 descendant 窄修：独立 G2

reviewed_at_utc: 2026-10-29T23:52:13Z

reviewer: 独立 Codex subagent `/root/fallback_g3`，按 AGENTS.md 3.2.1 接替 Claude 额度耗尽后的审查；本人未实现受审源码。

**APPROVE_WITH_NITS / BLOCKING 0，仅本地组件源码与已有fixtures证据。实际独立父/driver/四场景入口尚未实现；不授发布、远端CPU执行、Ray生命周期通过、释放/quiescence、GPU或native36资格。**

候选 `numeric-CPU-lifecycle-support-candidate.json` 实际SHA256 `4f3aaa75059d87f80afa3b49c7c9c37db240995937abfefe5b34c80e75bb59b9`。已读独立 `g1-numeric-driver-lifetime.md`（仅本地0GPU实现）、proposal、descendant两G1与既有最终G2，未改变detached/非detached策略或原GPU故障收口合同。

## 精确源码

以下均从实际checkout逐字节重算，与候选大小/SHA完全一致：

|源码|字节|SHA256|
|---|---:|---|
|`epd/runtime/numeric_cpu_ray.py`|4346|`24d129bec5d883a398d79a613253c0bc43e2b0e67c0a255ce969cd61222c4352`|
|`epd/runtime/numeric_gcs.py`|5468|`c31b6eb781bf93d4e1539e8ea2b0fe57812e96e3a8f84976b5742f0c4f8a1b53`|
|`epd/runtime/numeric_descendants.py`|8048|`6e33b325e77af6a4bde8abe43ab028c6427c69c033fe1d8bcabd0bae9cef37b6`|
|`epd/runtime/tests/test_numeric_cpu_ray_cpu.py`|4239|`28dc95d89b13ade5bff9f0a651418a93b8ed93c791f375c6544700d3b44ad1be`|
|`epd/runtime/tests/test_numeric_gcs_cpu.py`|5594|`70f22f69949524abaa20d6f85d7fb17218f1238f6e6d39b937516e4237ed09b5`|
|`epd/runtime/tests/test_numeric_descendants_cpu.py`|11877|`7615049e15fc9ad899f4f49f30755b2ace164901c0bf69f24a1456c765ec78f5`|

## 来源与实现核对

1. **pre-import顺序有效但不是完整安装闭包。** `numeric_cpu_ray.py:51–66`先拒绝非空/缺失CUDA visibility及已加载Ray/Torch/epdserve，使用distribution元数据固定Ray2.10.0位置/版本，随后按实际文件校验16项pins，最后才 `import_module('ray')`，并复核导入包路径/版本。未使用会先导入父包的find_spec子模块。`verify_sources:29–48`要求canonical绝对包路径、无链接/越界、指定UID、常规且≤2MiB文件及精确SHA。本审独立核20份本地source-evidence原件的raw SHA和Git blob（extra14、driver3、head2、parameter1），16项installed pins均有对应原件；这证明本地源码来源一致，不证明目标安装包当前已经逐项核过。

2. **dashboard/NVML判断限定恰当。** loader在任何head启动前实际调用已pin的check_dashboard_dependencies_installed并只接受False，返回receipt明确head/actor/GPU/lifecycle均未批准。官方utils1336–1350通过导入optional_deps判定；reporter的NVML初始化在_get_gpu_usage内，其is_minimal_module=False。官方resource_spec167–224在明确num_gpus=0的GPU分支跳过自动count/type路径；num_gpus缺省则会发现硬件。仅空CUDA或0GPU配置不能概括全部Ray行为：dashboard/utils108–145先遍历导入模块再过滤minimal，accelerators管理器选择亦有AMD/Intel发现分支，且Ray自身加载本地扩展。组件没有启动head，不在此伪称真实进程全程无硬件查询；未来完整入口须按G1继续核实际选择与进程原件。

3. **GCS是限定单次元数据，不是释放协议。** `numeric_gcs.py:22–50`限定127.0.0.1端口、再核pins和Ray2.10导入位置、要求父上下文ray.is_initialized=False；直接创建GetActorInfo stub，禁grpc retries、接收≤1MiB，核方法名及protobuf关键字段号。官方两proto的GetActorInfo request/reply及ActorState0..4与实现一致。`read:57–87`要求精确ActorID/job/namespace/name/lifetime，先record再实际RPC，单次timeout为min(0.25s,剩余deadline)，没有业务重试；reply迟到/错误/空身份/foreign/restart/GPU资源均拒绝并不产生finished成功记录。raw protobuf及SHA保留。ALIVE、PENDING、DEAD均仅返回raw_GCS_metadata_not_release_or_quiescence，PID0/pending和DEAD不授释放，代码没有released/passed推论。

4. **descendant修正保留历史且不伪造闭包。** `numeric_descendants.py:110–116`只对已known PID的snapshot FileNotFound/ProcessLookup捕获；还须proc.exists实际False才记head_known_pid_absent，明确release_or_quiescence_granted=False，保留known历史继续核其他进程。字段缺失但PID目录仍在、PermissionError和其他异常传播。已读继承NumericProc.exists，只将/proc/PID本身stat的FileNotFound当不存在；它不是NVML/未来创建/全部后代为空证明。

5. 原直接Popen/精确session flags、UID/boot/PID/start/root/run/ppid/exe、每TID children父链、前后稳定原件、WAL返回后登记、4096上限及deadline检查保持。可变argv仅在跨时刻identity比较中排除，实际raw仍记录；源根首次argv仍与held Popen.args逐项一致。未知孤儿不采用、已知孤儿阻断新闭包，不能按名字/env/同UID接管。当前组件没有发信号或pidfd清理动作；真正父监督器仍须提供已审身份清理、持续采集和异常原件。

## 已有fixtures与严格边界

已读原始日志和对应现有JSON，没有运行任何测试。Ray/GCS final日志18 tests/0failure/0error/0skip/0.035s，SHA `2fc4a5cab5bd4db0e3061fa8d96d7d080580f61c1a2113c2cd443dd961ad1c79`；对应JSON SHA `16429b9678e890971dc0bc8743063d6a6f77b76788fdc4cf31dba3eb73d8632e`，四源码SHA与本次一致。

descendant exit-before日志25例中known exited leaf为1 ERROR（SHA `becc5346193005fcd117c437ee6411ef003a55de64bf43e0e05d99ae4df01f05`）；exit-final同25例全OK/0.035s（SHA `e4b4307c3af6c91eeeaea3fca4b5f26412d426c075d10e6654cc4dedcfd0e0fe`），对应新测试保留历史、absent不授释放，existing PID字段缺失仍UNKNOWN。较早numeric-descendants-cpu-final.json只有19例/旧SHA，既有G2是23例/旧SHA，不能称它们覆盖当前25例；本审明确以本候选六SHA、当前测试源码和exit-final原日志为准。

这些是18+25=43个不同Windows fixtures/local-file模拟，真实Ray/grpc/NVML没有导入；不能证明实际/proc竞态、真实GetActorInfo、driver退出、迟到创建、head释放、四场景或CPU生命周期已成功。DEAD不授释放为本次源码静态核查结论，不虚构已有单独DEAD运行测试。

## BLOCKING

无（仅上述组件精确源码范围）。

## NON-BLOCKING / 接真实入口前必须落实

1. 完整父必须强制先调用pre-import loader，再创建其唯一私有head；GCS.connect自身只能核loopback和未连接driver上下文，不能单凭端口证明服务属于此head，也不能补证此前导入顺序。实际address/namespace/ActorID/job应来自同一已验证Node和create前WAL，不允许另建inspector driver接管。选定grpc/generated模块和native扩展的实际安装来源、env/pth/解释器及动态加载路径仍须运行入口审查；16个选定Python pins不等于全包传递闭包。
2. check/record/fsync、connect/import/channel建立没有独立的强制中断器；read的RPC虽≤0.25秒，整个单元有界仍依赖未来父的单一deadline、身份监督及180+120全场景预算。真实0GPU/head/actor参数和Reporter未构造路径须在完整接线与CPU Gate核，不把loader的False判定当无NVML活动证书。
3. known absent是一个时点的历史事件。collect仍返回known历史，可能含已消失PID，不是live列表；不能将其空/非空或GCS DEAD转为quiescent/released。未知新子、孤儿、pending/迟到创建与GPU上下文必须按既有合同持续观察，无法确认则FAILED_RELEASE_UNCONFIRMED。实际cleanup仍需稳定pidfd/UID/start/父链及按序释放，不能靠本collector自动授权信号。
4. 继承既有descendant G2限制：register根数量须由父约束；children先枚举排序后判4096不是对任意/proc输入的绝对内存/时间界；record/check真实WAL与异常保存尚未接线。保留旧B与失败材料，不把25fixtures当目标Linux验证。
5. 独立父、真实driver、四种normal/creation-window×detached/non_detached场景及终态仍未实现。后续完整G2、精确G5/Git-first/部署、fresh合法CPU窗口和单独执行批准、实际CPU G3均不得省略；不patch Ray atexit，不隐式冻结non_detached GPU策略，不授native36/三卡GPU/model/性能。Space当前静态verify按其独立批准继续，本审不重复或扩大该范围。

## QUESTIONS

无阻塞性问题；下一范围应提交真实父/driver/四场景完整接线，不能把本组件审查改名为生命周期结果。

本审仅通过Node文件API读取本地文件、计算SHA/Git blob，未运行shell命令、项目模块或测试，未联网/SSH/GPU/读凭据，未改源码，仅新增本审查MD/JSON。

GATE_RESULT: {"gate":"G2-numeric-cpu-lifecycle-support","decision":"APPROVE_WITH_NITS","blocking":0,"scope":"local_CPU_support_components_and_descendant_absence_delta_only","candidate_sha256":"4f3aaa75059d87f80afa3b49c7c9c37db240995937abfefe5b34c80e75bb59b9","source_evidence_files_verified":20,"preimport_pins_backed":16,"existing_fixture_tests":43,"real_parent_driver_four_scenarios_implemented":false,"real_lifecycle_passed":false,"release_or_quiescence_granted":false,"remote_CPU_execution_approved":false,"GPU_approved":false,"native36_executable":false}
