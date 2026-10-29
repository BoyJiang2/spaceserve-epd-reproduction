# Local controller/server bootstrap — FD绑定修正后G2

reviewed_at_utc: 2026-10-29T18:44:28Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，初审B1已闭合；仅源码批准，不授发布/部署/实际phase Gate/GPU或formal执行。**

保留初审space-20261030-controller-G2.md REQUEST_CHANGES/B1，不覆盖。独立重算实际最终源码tools/control_space_window_20261030.py SHA `908c8dfd46f6a02343fab54108c65c65dca37cc92bc90dab05bc31dabcef9ce9`、test_control_space_window_20261030.py SHA `83a6b70cede3ce3dcfadb24bcaad2b3dcf9b51d202c7cd9df0353450ab2c51de`，与final-tests及all-cpu-tests原件相符。只读核完整最终源码、测试、前后G2与日志/JSON，未运行项目/测试、网络、SSH、GPU或读取凭据，仅保存本审查。

## B1闭合

最终main在真实input.json已打开为SSH stdin的同一FD上调用verify_payload，顺序为：os.fstat→regular-file检查→读取实际内容SHA→再次fstat核device/inode/size/mtime均未变且实际SHA=预期wire→seek(0)→排他创建input-file.json，记录device/inode/bytes/实际SHA。此后才将同一个FD传给Popen。不是检查另一个按路径重新打开的副本，亦没有写后不核直接发送；保留了原transport的核心来源绑定，并未复用其固定390秒等待。

非regular在读取前直接拒绝，因此pipe fixture不会阻塞；错SHA/读期间metadata改变会在生成input-file和Popen前失败；证据文件已存在则open x拒绝，不覆盖旧回执、不改payload、不自动重试。源中Popen明确位于verify_payload成功返回之后，B1所需实际FD绑定成立。该修正不承诺防御能在核验后持续写入相同UID FD的一切恶意并发者；当前既有独立新output和单controller约束应继续保持，不扩展威胁模型。

## 测试材料实况

controller-final-tests.log有6项distinct测试实际OK/0.008秒；JSON exit0/两sourceSHA准确。3项原bootstrap构造/拒绝/单phase测试，新增3项调用生产verify_payload并使用真实本机regular FD（核SHA、seek0、保存inode）、错误SHA拒绝且不写回执、真实pipe拒绝且不读取。不是只增加字符串断言。没有直接模拟整个main/Popen或Windows FILETIME/SSH运行，本审不外推。

统一all-cpu-tests.json记录21 distinct、exit0、source前后不变及7文件SHA；数量与9 window＋6 launcher＋6 controller相符，不把早期重复discovery15当新测试。该统一结果仍仅Windows本地tests，不是目标机Linux/POSIX/信号/Ray/CUDA验收。本审未重跑测试。

## 其余边界和后续条件

初审其余认可保持：指定commit/HEAD与公开GitHub逐源码blob核验含controller、credential仅内存/curl stdin、snapshot限字段、review原文SHA、server clean Git/hostUID/CPU50nice10/policy后排他owned phase-inputs、指定Git launcher执行，实际entry/G2/G3 Gate不由controller构建。修正未改变单phase、UNKNOWN不杀不重发、真实PID/FILETIME、work+120远端timeout与观察total+150策略。

时间安全依赖已审launcher在bootstrap/refresh/源核之后、真实supervise前再次完整policy.validate，以及各phase真实Gate与END120；不能将外层timeout/kill-after视为延期或已释放证明。观察超时/SSH255须查同一实际PID/终态，不重跑。当前controller测试不证明所有main异常/cleanup，实际执行前的Git-first/G5、指定commit部署、04后fresh双lane与全SHA、execution approval以及新CPU/numeric/model/formal Gates仍必要。

候选清单若仍为旧hash不可发布，必须按本最终源码/测试及复审原文更新后作精确G5。旧代码/失败/初审和两次修正日志保留，不能追溯改写已封存730批次。此最终G2不是发布或GPU执行许可。

GATE_RESULT: {"gate":"G2-space-20261030-controller-final","decision":"APPROVE_WITH_NITS","blocking":0,"closed_findings":["B1-actual-SSH-stdin-FD-identity-and-SHA-binding"],"source_sha256":"908c8dfd46f6a02343fab54108c65c65dca37cc92bc90dab05bc31dabcef9ce9","test_sha256":"83a6b70cede3ce3dcfadb24bcaad2b3dcf9b51d202c7cd9df0353450ab2c51de","scope":"controller_and_bootstrap_source_only","GPU_approved":false,"formal_approved":false,"deployed":false}
