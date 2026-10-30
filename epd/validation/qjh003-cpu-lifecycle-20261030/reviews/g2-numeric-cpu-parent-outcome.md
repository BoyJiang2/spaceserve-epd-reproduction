# CPU 父入口 outcome 版本：独立最终源码 G2

reviewed_at_utc: 2026-10-30T00:14:00Z

reviewer: 独立 Codex subagent `/root/fallback_g3`，按 AGENTS.md 3.2.1 接替；本人未实现受审源码。

**APPROVE_WITH_NITS / BLOCKING 0，仅源码级批准。原四B初审与37f修订REQUEST_CHANGES原件保持；本次单独审查新outcome冻结版本，不追溯改写旧结论。不授发布、部署、远端CPU/Ray执行、GPU、实际生命周期G3或native36资格。**

候选 `numeric-cpu-parent-outcome-candidate.json` 实际SHA256 `57dbae6669d22a87645b8a795f7e25304ad69d3b6281516829e8ed382493c582`。已逐12份实际源码/测试重算大小和SHA，与候选完全相等；完整12项绑定在本审查JSON。相对37f只变父入口与对应测试，driver/receipt和已审支持组件字节保持。

|本次变化文件|字节|实际SHA256|
|---|---:|---|
|`epd/runtime/numeric_cpu_lifecycle.py`|18146|`a37684b1c6f7cfff26956dfbdcfa596d498c6bdc0584e1c154fee683c4b7ce30`|
|`epd/runtime/tests/test_numeric_cpu_lifecycle_cpu.py`|13842|`25ad0cedc1e8bdb39bff9a2386115966030ef93ceab50232b1c796d7a420adde`|

## 剩余R1关闭：真实signal outcome不再与already_absent混同

父入口24–53行保持registered identity与稳定pidfd前后复核；PID已不存在返回 `controlled_signal_sent=False,already_absent=True`，不发信号。TERM/KILL路径在内核signal调用成功后分别记录CPU_TERM_sent/CPU_KILL_sent，再返回实际outcome；仅intent/WAL返回、函数无异常或已absence都不算动作成功。记录/身份/取消检查失败仍抛出，pidfd finally关闭。

controlled分支162–177行要求driver poll仍活、GCS非DEAD、无ready、真实constructor monotonic窗口有效，再受window_check约束调用terminate；只有outcome.controlled_signal_sent严格True才设stopped。driver自然死亡或absent outcome失败并保留pending，不再伪称受控退出。时间窗口沿用真实15秒构造延迟及至少2秒余量，在每次signal前检查，不用缺文件单独证明命中窗口。

detached分支189–198行在精确GCS PID相等之后，对登记PID observe/current identity/stable双读，保存前后原件；仅实际actor signal成功outcome才设actor_stopped。已消失PID、GCS ALIVE但当前身份不符、无signal返回都失败；最终DEAD+原PIDabsent不再绕过survival和父释放门槛。

## 剩余R2关闭：明确driver退出之后的新GCS/活PID观察

185行先poll确认实际driver终态；187行重新read精确GCS，不复用161行的退出前state。detached的CPU_detached_survived_driver记录绑定这份GCS_after_driver_exit及双读活PID原件，随后才父释放，再199–205行观察最终DEAD+原PIDabsent清pending。这样“driver退出前ALIVE、退出后已DEAD”只会失败，不能被后来的DEAD回执修饰成存活通过。

normal分支仍要求driver自然exit0，先前ACK的ALIVE/GCS精确PID/当前身份双读合同不变。non_detached仍按其独立owner退出行为取证，不把detached的存活逻辑混用。创建前父WAL/pending、唯一提交、unknown/缺身份拒绝head清理、四种场景各一次及180工作+120清理均未放宽。

## 原四B的最终状态

1. **B1关闭**：父/driver继续共用 `numeric_cpu_receipts.publish`，文件fsync后hard-link拒覆原子发布，目录fsync及pending保全。没有恢复直接写最终名的半JSON竞态。
2. **B2关闭**：normal parent-observed之前保留精确GCS PID与当前observe/stable原件，不从known历史推出活PID。
3. **B3关闭**：detached必须有退出后新GCS ALIVE、当前绑定活PID、真实父signal outcome及最终终态；直接DEAD、PID消失或无动作不能PASS。
4. **B4关闭（源码合同）**：controlled必须活driver/非DEAD、真实构造monotonic窗口、每signal前余量检查及实际signal成功；错过窗口或已有自然退出失败，不以ready缺失替代正证据。真实时钟/信号/退出时序仍待实际CPU四场景Gate核验，源码批准不是该结果。

## 已有测试证据

`numeric-cpu-lifecycle-outcome-final-tests.log` 实际SHA `46af8961197f4dc9229a2de234ef5cf7048cebdf6764edf645cc9e97137b10c9`。本审逐testID核166条、166不同ID、顺序与冻结候选一致，全部ok/0skip，日志0.861秒；未重新执行测试。相对161版增加5个状态ful场景反例：GCS仍ALIVE但实际PID消失、actor absent outcome不得算父释放、driver absent outcome不得算controlled、自然driver退出拒绝、GCS已DEAD不能算受控退出。原detached意外DEAD正反例改为明确退出前/后GCS序列，driver状态只在模拟signal时变化，避免旧无状态Mock预先退出。

同时核实际terminate fixtures区分absence/TERM_sent、PID复用拒绝、fsync失败不信号及reap；共享receipt的5例仍包括真实NTFS文件/硬链接先后，目录fsync是Linux适配mock。166是本地不同组件回归总数，不能称166个真实Ray场景；不对这12项之外的全部baseline模块作新增完整审查。原10例fixture环境错误、旧四B和37f拒绝日志保持，不混作本版通过。

## BLOCKING

无（精确候选57dbae66的源码范围）。

## NON-BLOCKING / 实际执行前后的边界

1. 源码已具备有限四场景入口，不等于实际Ray/Node/GCS/driver行为已通过。后续仍须精确G5、独立EPD分支Git-first发布、指定commit部署逐字节核、freshCPU预约/现场、实际env/解释器/pth/17pins及minimal分支核验，再单独具体execution G2。当前无发布/部署/执行许可，不改Space24b或GPUbackend策略。
2. 实际G3应核真实ActorID/job/namespace、source/boot/UID/root/run、constructor时间、driver真实退出、退出后GCS与活PID双读、signal intent和sent顺序、pidfd归属、最终DEAD+PIDabsence及全部pending终态。signal sent不单独证明死亡/释放，GCS DEAD亦不单独证明quiescence；不得从本地outcome布尔推断目标已经释放。
3. 共享目录fsync、Ray初始化/atexit、真实/proc权限与竞态、Linuxpidfd/TERM/KILL/reap、port/session fresh及第三方阻塞行为未由Windows fixtures覆盖。合作式check需要后续外层有限监督合同，完整180+120/票结束前余量不变。constructor窗口实际信号与时钟顺序须在真实原件中证明，错过就保留失败，不延时或重试。
4. pending/unknown拒绝head清理表示FAILED_RELEASE_UNCONFIRMED，不能当释放或继续占用授权。最终leftover scan仅在同UID/root/run范围做时点检测，未知从不signal；命中迟到PID拒绝成功。它不证明整个host、其他head或未来无限时段清空。实际残留须保留身份和有限监管交接，不以UID/名字/进程组清理替代。
5. 不导入Torch/EPD Worker/IPC/model，不授NVML/GPU或native36。已有17份目标文件静态SHA记录仅是原件字节前验，不是Ray运行结果；实际min-dashboard及潜在硬件发现分支仍按原G1核。Space现有单元不因本源G2被重跑/改变，其正式预算和优先级保持。

## QUESTIONS

无阻塞性问题。可以据本源码G2提交精确发布候选G5；真实CPU执行命令与实际四场景结果须分别另审，不能用本报告替代。

本审仅通过本地Node文件API读取/计算SHA与解析已有日志，未运行shell命令、项目、测试、Ray、信号、网络、SSH、GPU，未修改源码，仅新增本报告和JSON；初审及37f拒绝原件未更改。

GATE_RESULT: {"gate":"G2-numeric-cpu-parent-outcome","decision":"APPROVE_WITH_NITS","passed":true,"blocking":0,"candidate_sha256":"57dbae6669d22a87645b8a795f7e25304ad69d3b6281516829e8ed382493c582","closed_original_findings":["B1","B2","B3","B4"],"closed_revision_findings":["R1","R2"],"source_level_approved":true,"existing_distinct_CPU_tests_verified":166,"publication_approved":false,"remote_CPU_execution_approved":false,"actual_four_scenario_lifecycle_passed":false,"GPU_approved":false,"native36_executable":false}
