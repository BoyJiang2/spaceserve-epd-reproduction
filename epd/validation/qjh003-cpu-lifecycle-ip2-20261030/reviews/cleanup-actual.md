# 失败CPU批次：清理与补充释放观察独立G3

reviewed_at_utc: 2026-10-30T01:29:08Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，仅认可补充观察时点1793323320139的六原PID不存在、本run范围空且无未分类候选。cleanup实际exit1、CPU验证实际exit1均保持，不改terminal、不签四场景通过或新运行许可。**

本人仅本地只读实际input/command/FD/PID记录、readback原件、已保存观察和Git对象并算SHA；未执行项目、测试、网络、SSH、信号、Ray或GPU，未改原件。

## 精确执行链与真实失败

唯一 `numeric-cpu-lifecycle-cleanup/` 的实际approval与独立G1/G2 JSON语义相同，base64真review SHA `fa226e18a1d516147be9f91d254812239920ab8c6ee3e8802adfee6a582bce95` 与原文相符；input实际FD SHA一致。实际argv解码operator SHA `3aa92cc467d75b3ca0bd44c462c35ac43990610175edbe6a6c8d1337250e053e`，不是旧612草案，已绑定commit529d/原journal/同run。controller、stdout、stderr和outer exit原件保留。

readback stdout的claim/cleanup.jsonl/terminal实际raw_base64逐解码，大小/SHA均与记录及本地保存原件全同。claim的真review、原journalSHA、实际fresh booking与input一致，六原登记身份保留，没有按名字/UID收编。actual原身份断言、源码/HEAD/manifest、CPU50/nice10/boot及窗口guard来自精确获审operator的真实成功前序，不宣称另做全机probe。

实际journal顺序与受审范围相同：

| PID | 实际处理 |
|---|---|
|501363 driver|已不存在，无signal|
|501249 raylet|实际TERM intent→sent→outcome，未KILL|
|501307、501309|已不存在，无signal|
|500697 dashboard|实际TERM intent→sent→outcome，未KILL|
|500416 GCS|最后实际TERM intent→sent→outcome，未KILL|

driver absent后日志现场复读只preimport_verified、无create WAL，再进入head收口的事件已保存。所有signal对象只在原六PID集合，无新driver、actor或GPU。资源不存在的outcome没有被写成发送了信号，符合实际。

但cleanup最后/proc扫描在 `/proc/500337/cwd` 触发PermissionError，terminal实际exit1、error原文保留、CPU_validation_passed false；stdout与terminal语义全同，outer exit1与stderr堆栈一致。完成时1793322596003、elapsed0.836139秒。**不能把这份cleanup原terminal改成成功。** 当时500337的具体服务身份没有在该失败terminal中闭合，本审不追认它为PAM/sshd；后续观察用其自身新身份独立核验。

## 补充只读观察的独立闭合

第一readback observed1793322780939已经确认原六PID都不存在，但仍有两个cwd权限未知候选，所以那一份不能单独证明run scope完全清空。最终 `numeric-cpu-lifecycle-cleanup-scope-verification2/` 是新增只读观察，command exit0、stderr空，没有再次cleanup、signal或改运行代码。

最终observed_ms **1793323320139**、boot `65f52a67-afe4-4919-8646-4694255b48ee`，原六PID目录全部false；remaining_run_scope、unknown_candidates、older_owned_processes均为空。与cleanup完成相隔724136ms，这只能证明**该补充时点**释放，不补造cleanup当时的成功terminal，也不证明当前或未来无限期状态。

补充观察对cwd PermissionError没有按名称猜测或通用忽略：

- 实际input的user-service源码SHA `48fe3fc2bf9d4070f48db6b60b44671c40761850014f650a0f54b82678c357fd`，本人与Git24b的tools/space_user_service_guard.py原字节核同。
- 实际SSH源码SHA `8ffccf7061b2ebc8ac90543d0d60c79efaf7ff87552cef8fcf1bd6555dbd0c0c`，与Git24b的tools/materialize_assets_cpu.py原字节核同；观察代码只AST提取其中原ssh_snapshot/ssh_exception两函数，没有执行旧资产迁移main或更改例外规则。
- 实际user-service PID602214→602213→root PID1链，固定boot/UID、cmdlineSHA、cgroup、parent exe及PID1/ticks anchor按原函数校验；实际SSH PID602249→root600989→daemon7347链，child cmdlineSHA/session cgroup、root UID/parent与daemon PID7347/start19660/system cgroup anchor按原函数校验。两函数都真实双读snapshot全等才返回，输出各自snapshot SHA本人重新计算相符。不能夸大为原SSH函数对所有parent/daemon cmdline都采用固定SHA白名单；它记录这些值，明确固定的检查以原函数为准。
- 两个例外仅表示当前不可读cwd候选匹配既有窄服务身份，不授这些服务signal或项目资源许可。其它身份仍未知就进unknown；FileNotFound时PID仍在也进unknown。最终unknown确为空，非删除未匹配项得到。

观察代码限制UID2147、/local/boyjiang/epd root、精确EXP_ROOT/REPRO_RUN_ID与原六PID。此前更早进程列表也为空，不凭相同UID推定均属本项目；这里只签**原六进程及这个run在该观察点的范围**，不是全机或所有EPD历史head无资源。

## 结论与边界

可在状态中记：本失败CPU批次原登记六PID已在补充时点确认消失；本run时点scope空/unknown空，资源收口证据接受。必须同时展示CPU验证exit1、cleanup exit1和补充只读观察，不把它们折叠为“CPU生命周期成功”。static迁移与529源码部署结果仍是各自原结论。

不授权重跑、修地址后自动启动、换run/port/资源、Ray/IPC/native36、GPU、模型或性能实验。任何下一单元需既有流程及真实新范围/源码/窗口证据。所有原失败、66MB journal、terminal、封包和本补充原件保持不变。

GATE_RESULT: {"gate":"G3-numeric-cpu-cleanup-actual","passed":true,"decision":"APPROVE_WITH_NITS","blocking":0,"scope":"original_six_registered_CPU_PIDs_and_exact_run_scope_at_supplemental_observation_only","resources_release_observed_ms":1793323320139,"original_six_PIDs_absent":true,"same_run_scope_empty":true,"unknown_candidates_empty":true,"cleanup_exit_code":1,"CPU_validation_exit_code":1,"actual_four_scenario_lifecycle_passed":false,"new_execution_approved":false,"GPU_approved":false}
