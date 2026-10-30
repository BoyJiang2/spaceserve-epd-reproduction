# CPU loopback与final scope窄修：独立源码 G2

reviewed_at_utc: 2026-10-30T01:48:16Z

reviewer: 独立 Codex subagent `/root/fallback_g3`，按 AGENTS.md 3.2.1 接替；本人未实现候选。

**APPROVE_WITH_NITS / BLOCKING 0，仅冻结候选的源码级批准。允许提交下一精确发布G5；不授发布、部署、新CPU/Ray运行、GPU或native36。旧529d真实CPU失败仍为exit1，不能由本G2改成PASS或复用其实际G3。**

候选 `numeric-cpu-ip2-source-candidate.json` 实际SHA256 `4626e500aee2b7933a742fee8f22829e1a2e9a4451f79db438c7783653ef9212`。本审独立逐10项大小/SHA核对全部一致；对应机器JSON绑定完整清单。

## 精确受审10路径

|文件|实际SHA256|
|---|---|
|`epd/runtime/numeric_head.py`|`cf959e00da957944fb8759be33ed05500e958f475f3ddef156e203361f7bec72`|
|`epd/runtime/numeric_gcs.py`|`a9ab7ad366c55198dc1a08bc435030d54b7b9fc32c6b7284b6551f56f5c66341`|
|`epd/runtime/numeric_cpu_driver.py`|`9ab4e12fe770e7365e43c412bc34beea91754fa476f67871ecd2f3aa98b36733`|
|`epd/runtime/numeric_cpu_lifecycle.py`|`96b52e72845ee1fb5ba6c4c874ad5b8f2c6d9549adfe893c53babb91bb60b8cb`|
|`epd/runtime/tests/test_numeric_head_cpu.py`|`829038fc48253be403ccc4da4aa747c3eca8dacbe663e9acb2a4fcbc1e7c3298`|
|`epd/runtime/tests/test_numeric_gcs_cpu.py`|`ac766777750e70311d1554d4ef15ab84a41ac163dc6df411ec8ea10b3b6f8f0a`|
|`epd/runtime/tests/test_numeric_cpu_driver_cpu.py`|`a0a85c868f18903742c64ab1f66d1594b766c2e03d225f9a82caa95fdf7c11b9`|
|`epd/runtime/tests/test_numeric_cpu_lifecycle_cpu.py`|`7a8c0d595874e06f350e221acba4cb349950eb2a94da0f428c92479d53b5adb7`|
|`tools/space_user_service_guard.py`|`48fe3fc2bf9d4070f48db6b60b44671c40761850014f650a0f54b82678c357fd`|
|`tools/test_space_user_service_guard.py`|`ad3e238d2c62f6774cd569916b92a7b9b39e141ae7dba675eaaa17dcfd80d8e8`|

## 原生地址/API与GPU隔离

1. 共享head的node_parameters仅在gpu_count==0选127.0.0.2；gpu_count==3仍127.0.0.1，其他dict字段/校验完全保留。已与529d实际部署capture中的原head逐字节差异核查：除这个固定地址选择及construct_node按精确parameters核expected address外，原源码相同；参数仍须等于node_parameters生成的完整dict，故不是放宽任意地址。新增GPU3 fixture核完整原dict，不只核num_gpus。
2. CPU父scenario地址、GCS reader endpoint、driver spec限制均同步固定127.0.0.2，未扩大为整个loopback、任意host、auto或外部head。driver新connect_existing使用原生ray.init(address=spec,address namespace/log参数及 `_node_ip_address='127.0.0.2'`)，随后仍要求connect-only非head、all_processes空且实际Node.address精确等于spec；普通Ray退出hook没有改动。main在调用前仍进行完整spec/source/env核验。
3. 已读官方services源码及原重现实录 `numeric-cpu-loopback-canonicalization-reproduction.json`，SHA `85be66963a1d16714afc325a36564eee2bd3ebf05b2339d9eb77ad8d5c2745af`；其绑定的官方services raw SHA385604d4保持。原生两AST函数重现127.0.0.1→172.31.35.35并调用物理IP provider，127.0.0.2原样保持且不调用该provider。与本审此前独立读取的官方worker1564/services517/599机制一致；本审没有重跑AST或导入Ray，不把它当实际GCS连接成功。
4. GCS/GetActorInfo单次deadline/精确ActorID/job/namespace/PID及DEAD非释放语义、原子JSON发布、父活PID双读、真实signal outcome、driver退出后fresh GCS、pending保全、四场景/180+120/30秒等原合同不变。没有Ray安装文件、driver hook、模型或GPU分配策略修改。

## final scope的严格未知处理与published来源

`numeric_cpu_lifecycle.py:109–130`的范围仍是只读探测：先UID，再可读cwd在本root下才读EXP_ROOT/REPRO_RUN_ID两键；迟到同run PID只保留snapshot并拒绝成功，不登记signal许可。现在PermissionError仅调用精确control_service_exception，None/异常就拒绝，**不再按非python/ray名字跳过**。FileNotFound/ProcessLookup须再核PID目录确实不存在才接受时点消失；原PID目录仍在则UNKNOWN失败，不将字段丢失当空scope。

helper入口19–31行在使用前核三份工具原SHA/非链接，再通过普通非main模块导入只读exception/ssh_exception。独立核来源如下：

- PAM48fe及11fixtures的Git blob分别70fa044c2484961fff903a166a9c27d33a9dff62 / f2dd7da9854abe53de2c7716b8f46b146a1cd29f，与已验证Space24b原tree/index中的精确原件一致；复制进EPD分支不是修改Space。
- materialize_assets_cpu.py为8ffccf7061b2ebc8ac90543d0d60c79efaf7ff87552cef8fcf1bd6555dbd0c0c / Git blob3fa4687494040f918d5c0d1a049b336553107601；migrate_code_cpu.py为9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405 / bloba44d4888daf61174f3caf90ef5c16f89bd55be89，均与529d已验证tree成员一致。
- PAM仅接受boot65f、UID2147 child(sd-pam)/parent systemd用户service/init PID1三链，固定exe/cgroup/cmd SHA/init start856/启动先后及前后完整snapshot一致。非PAM才进入原SSH规则：指定boot/UID、child comm/cmd SHA/session cgroup、root parent与固定daemon7347/start19660及双读一致；未知身份不会因名字看似服务而通过。
- 两旧工具CLI/run/booking均位于显式入口函数及`__name__=='__main__'`下；此接线未调用它们，只引用只读定义。旧票据/资产复制/部署代码不因此运行，service proof只豁免这一次cwd不可读，不授项目归属、released/quiescence或信号许可。可读project cwd不会进入该例外。

## 原始fixtures与旧失败状态

新before日志保留12个head fixtures中的1 FAIL（旧CPU地址.1不符合新.2期望），SHA `90162c847c1dce706785c421d826be9e8f90fe28e2a513ad3bbda75d714f33af`；不是伪称旧GPU3失败或真实Ray探针失败。

本审逐实际日志testID/顺序/去重/字节/SHA核验：

- `numeric-cpu-ip2-final-tests.log`：175不同ID，全部ok/0skip，0.865秒，SHA `d3cded5473946f4114a80afb89dd5abaa2fdbaefd09419319b3cec41cfc2c0ce`。
- `numeric-cpu-ip2-service-guard-tests.log`：11不同既有service fixtures，全部ok/0skip，0.001秒，SHA `6126767a8d263ab0dfa819d9c259e8ef6f5602aaf94cb9eab3642afc9451fc52`。

新增driver参数、CPU/GPU3分支、foreign address/owned head拒绝，以及final scope unknown PermissionError、真实PID消失和目录仍在拒绝均有fixture。scope集成测试注入service proof；三链双读和每字段拒绝来自原11个guard tests，不把这个组合说成真实/proc测试。没有新增真实Ray/网络、实际127.0.0.2 bind/connect、Linux目录fsync/pidfd或GPU证据。

已核独立cleanup G3与原文SHA `e56f04fcef444b5a6513b2e773fde0b79ea177054552bba2967400566539af86`一致：其通过范围仅补充时点1793323320139原6PID已absent/同run scope与unknown为空；cleanup本身exit1和CPU validation exit1仍原样保存。不能把资源补证转成四场景PASS，也不将这个旧时点当新执行fresh现场。本G2不重审其所有原件或改变其范围。

## BLOCKING

无（此精确10路径源码范围）。

## NON-BLOCKING / 下一发布部署执行前置

1. **物理tools是新增执行闭包，不能复用旧86份manifest。** 原EPD checkout为cone sparse，tools未物化；当前source会严格失败而非fallback。下一具体部署须经独立审查明确`git sparse-checkout add tools`、checkout新发布commit，并对runtime＋tools全部物理Git成员/大小/SHA/owned/非链接/clean核验，包含上述三helper及其import依赖。新运行须绑定这份真实新部署manifest/G3；旧529d部署G3不能套用。
2. 新源尚未发布/部署。需精确EPD分支G5/Git-first、新CPU deploy执行G2及实际部署审计，再新唯一run/session/namespace/config和单次CPU执行G2/freshCPU票/完整预算。不要直接改server文件、原失败run或重发旧命令，也不因CPU票临近结束缩验证/自动续窗。
3. source pins校验是对精确文件及受控入口的约束；实际运行还要核真实解释器/site/包17pins、helper物理位置和新commit。普通module导入不得被未知预加载同名模块/其它sys.path替代；本批准不覆盖任意脏Python进程上下文。
4. service例外有固定boot/daemon/init anchors，现场不符必须拒绝并保留原件，不能泛化为所有systemd/sshd或按名字跳过。只读scan是一个时点的本run范围观察，不是全host/无限未来quiescence；unknown仍不授权kill。进程消失/复用/权限异常的真实Linux竞态尚待实际Gate，不由Windows175+11推导。
5. 地址原生分支及fixtures只证明源级最小修复方向。实际Node advertise/driver canonicalized bootstrap/_node_ip_address/private GCS/PID与四场景须在新实际原件中核；不同loopback不自动证明所有listener网络隔离或连接健康。原真实失败不能被此源G2补成PASS，GPU3/native36/模型仍未获新许可。

## QUESTIONS

无阻塞性问题。可提交精确发布候选；本审不执行任何新部署或Ray单元。

本审仅本地Node文件API读取源码/已有日志/Gate、比对来源Git成员身份和计算SHA；未运行项目/测试/shell命令、Ray、信号、网络、SSH、GPU或修改源码，仅保存本审查MD/JSON。

GATE_RESULT: {"gate":"G2-numeric-cpu-ip2-source","passed":true,"decision":"APPROVE_WITH_NITS","blocking":0,"candidate_sha256":"4626e500aee2b7933a742fee8f22829e1a2e9a4451f79db438c7783653ef9212","paths_verified":10,"source_level_approved":true,"CPU_loopback":"127.0.0.2","GPU3_parameters_unchanged":true,"existing_CPU_fixture_tests":175,"existing_service_fixture_tests":11,"physical_tools_deployment_required":true,"publication_approved":false,"remote_CPU_execution_approved":false,"actual_new_Ray_lifecycle_passed":false,"GPU_approved":false,"native36_executable":false}
