# CPU 父入口：冻结修订37f43b17的独立 G2

reviewed_at_utc: 2026-10-30T00:10:32Z

reviewer: 独立 Codex subagent `/root/fallback_g3`，按 AGENTS.md 3.2.1 接替；本人未实现此修订。

**REQUEST_CHANGES / BLOCKING 2，仅针对candidate37f43b17。原四B初审MD/JSON保留；新修改正在主导准备，本报告不审查或批准下一字节。不能仅源码批准本修订进入执行。**

## 精确冻结与已核测试

候选 `numeric-cpu-parent-revision-candidate.json` 实际SHA `37f43b17dee4bd155c45555e0ba9b0e66e301a891c9b3682044ddc54dc62f0d4`。本审逐12项重算大小/SHA，全部与候选一致，完整列表绑定于本报告对应JSON；关键新版本为：

|文件|字节|SHA256|
|---|---:|---|
|`numeric_cpu_lifecycle.py`|16915|`aba0e7560ddb2edafd7eca5538b525b48ddef1d4c81ccfe1715a5d6971a19c2a`|
|`numeric_cpu_driver.py`|7020|`8d064960d39fbdd16e2dee4fb041a9ef86055a25ea43bebab66e89312f95f5e2`|
|`numeric_cpu_receipts.py`|873|`8976ae523d7b86d9d12ef0a7b7b274e80de5a856917f48c94fd634e710332544`|
|`tests/test_numeric_cpu_lifecycle_cpu.py`|10858|`73b4e3e938eb0fe8af8fd621d791d3d46d72ec7d2c9bc2d2d110425f4b315a45`|
|`tests/test_numeric_cpu_receipts_cpu.py`|3009|`49bca74856dfff6919b85880ecab858369851beffb87c9df9267f832a577d212`|

其余既有Ray/GCS/descendant与driver fixtures SHA同候选所列，并非重新运行其测试。本次日志 `numeric-cpu-lifecycle-revised-integration-tests.log` 重新算SHA `518e006ed600c9b26fff68f0f51283491c7b33e3917f18c04eeb45b781a9a1f7`；逐testID核161条、161不同ID、顺序与候选一致，全部ok、0skip，实际日志0.703秒。没有把旧多轮重复fixtures相加。这是Windows mock/local file/socket及已列组件回归，不是161个真实Ray场景，也不证明新父入口实际运行过。

## 原四B的修订判断

- **B1源码关闭**：共享publish先O_EXCL写`.pending`、flush/fsync完整文件，再os.link拒覆原子发布，目录fsync后移除pending并再次目录fsync；父与driver都使用该实现。5个receipt fixtures含真实NTFS文件/硬链接次序、旧target/pending拒覆、文件fsync失败不暴露final、目录fsync失败传播；Linux目录fsync适配器为mock，不能称目标Linux实际耐久性已验证。
- **B2 normal ACK源码关闭**：父173–179要求GCS ALIVE且PID相等，再observe/current identity相等/stable双读，保存前后原件后发ACK。新增known stale和GCS PID错误反例确实不产生parent-observed。已known历史仍保留，没有通过删除历史规避。
- **B3仅部分关闭**：新增actor_stopped门槛可拒绝直接DEAD路径，但actor_stopped并不保证实际signal；且所谓survival可引用driver退出前的GCS状态。以下R1/R2仍阻断。
- **B4时间判断已明显加强，但“确由本次控制导致退出”仍未闭合**：constructor回执携真实同host monotonic与delay15，父每次signal前check剩余≥2秒，并拒绝已过窗口。它不再仅凭ready不存在推断时间；然而driver可能本已退出，terminate无signal返回仍标stopped，见R1。新晚窗口反例不覆盖这个分支。

## BLOCKING

### R1 — terminate的正常返回不代表发过信号，调用方却据此宣称受控停止

位置：`epd/runtime/numeric_cpu_lifecycle.py:24–50,159–172,183–190`。

生产terminate在34–38行发现已登记PID已absent时记录事件并正常return，未发TERM/KILL；实际signal路径同样不返回区分outcome。场景171行/186行调用后无条件设stopped/actor_stopped=True。因而：controlled driver若已自然/异常死亡，可被当作本次受控退出；detached actor若在GCS尚ALIVE时已实际消失，terminate可只做absent返回，actor_stopped仍真，最终DEAD+absent可以PASS。新增正例把terminate整体mock为空返回，所以不能证明生产路径真的发了父信号。此前要求的“父释放”语义仍可由没有动作的函数返回伪替代。

最小处理：terminate提供明确、持久记录的already_absent与实际TERM/KILL成功outcome（含绑定identity/实际时点），不能将intent当signal成功。controlled分支先核driver实际尚活、GCS非DEAD和有效constructor窗口，仅在实际本次signal成功后标stopped；detached survival前做当前稳定PID双读，并只以本次实际actor信号结果满足父释放门槛。already_absent仍可用于普通cleanup，但不得充当该场景要求的正证据。增加driver早死、actor已消失但GCS ALIVE、terminate无signal的stateful反例，确保保守失败且不清pending。

### R2 — driver退出后的survival使用的是退出之前读取的GCS状态

位置：`epd/runtime/numeric_cpu_lifecycle.py:158,180–188`。

state在158行读取；之后driver可在本次RPC之后退出，180行poll才首次观察其退出。183–185行却复用原state=ALIVE来记录CPU_detached_survived_driver。该原件并不证明actor越过driver生存期：它可能在driver死亡之前ALIVE，随后与driver一起死亡。后续final=DEAD只证明后来死亡，不能修复survival观察的时序。即使R1使signal真实可核，也不能用一次过早的GCS数据支撑“driver退出后仍ALIVE”的结果。

最小处理：先记录本次实际driver终态/观测时点，再重新单次读精确GCS元数据；detached须在该退出之后的ALIVE+精确PID和实际稳定活进程观察成立，才记录survival并进入父释放。重读是既定持续观察的下一次查询，不是业务重试/重建actor。新增GCS第一次ALIVE、driver恰退出后已DEAD或PID消失的反例，禁止沿用前态作PASS；normal/controlled两类均使用明确事件顺序。

## 新leftover扫描与未覆盖边界

1. 最后扫描先UID，再cwd在本root下才读EXP_ROOT/REPRO_RUN_ID两键；同run迟到PID只记录/拒绝成功，不登记授权或signal未知。新增late-scope返回值反例覆盖调用方不报成功，方向认可。scanner本身及/proc权限/消失/复用竞态仍未真实Linux执行；PermissionError候选路径保守失败不是释放。该扫描是时点探测，不能扩大为全host清空或完整未来quiescence证明。
2. pending从Popen前WAL直到精确DEAD+原PIDabsent才清、未知/缺身份拒绝head清理、registered链稳定pidfd与直系reap、180+120与四场景单次均保留。FAILED_RELEASE_UNCONFIRMED仍须真实残留交接及外层有限监管，不等同于释放或延时占用授权。
3. receipt完整final在link后可见；若随后dirfsync失败，publisher会失败且保留partial，这不重新引入半JSON，但不能声称已完成所有持久化步骤。当前本地证据只mock目录适配，实际Linux文件系统/解释器/17pins/minimal分支/真实private GCS仍须部署后Gate。
4. 合作式check不能替代所有第三方初始化、文件系统和callback阻塞的外层deadline监督；真正CPU entry命令须Git-first/精确发布部署与独立execution G2/freshCPU票/cleanup边界，当前未获授权。没有真实Ray/信号/GCS或GPU运行，不能称生命周期已验证、driver策略已冻结或native36可执行。

## QUESTIONS

无需用户更改设定。请按上述窄outcome/时序修正提交新candidate与stateful反例原始日志，另做delta复核；初审四B及本修订结果原件保持，不覆盖重标。本报告只审冻结37f43b17，不审批主导已提出但尚未提交的下一修正。

本审仅用本地Node文件API读取/计算SHA与解析日志，未运行shell命令、项目、测试、Ray、信号、网络、SSH、GPU或修改源码，仅新增此审查及对应JSON。

GATE_RESULT: {"gate":"G2-numeric-cpu-parent-revision","decision":"REQUEST_CHANGES","passed":false,"blocking":2,"candidate_sha256":"37f43b17dee4bd155c45555e0ba9b0e66e301a891c9b3682044ddc54dc62f0d4","closed_original_findings":["B1","B2"],"partially_closed_original_findings":["B3","B4"],"remaining_findings":["R1-no-proof-of-actual-bound-signal","R2-pre-exit-GCS-state-reused-as-post-exit-survival"],"source_level_approved":false,"remote_CPU_execution_approved":false,"real_lifecycle_passed":false,"GPU_approved":false,"native36_executable":false}
