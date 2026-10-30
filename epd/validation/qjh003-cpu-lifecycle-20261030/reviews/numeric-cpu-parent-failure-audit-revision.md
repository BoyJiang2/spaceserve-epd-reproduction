# CPU 父/driver失败路径：冻结revision复核

reviewed_at_utc: 2026-10-30T00:10:35Z
reviewer: /root/gpu2_report_g4

**REQUEST_CHANGES / BLOCKING 2。原B2时间窗口问题关闭；原B1仍有absent/no-signal反例，且同一根因影响controlled driver退出。**

只绑定候选 `numeric-cpu-parent-revision-candidate.json` SHA `37f43b17dee4bd155c45555e0ba9b0e66e301a891c9b3682044ddc54dc62f0d4`。本人逐12文件实际大小/SHA与manifest相符，未追随新修改混版；关键parent SHA `aba0e7560ddb2edafd7eca5538b525b48ddef1d4c81ccfe1715a5d6971a19c2a`、driver `8d064960d39fbdd16e2dee4fb041a9ef86055a25ea43bebab66e89312f95f5e2`、receipt helper `8976ae523d7b86d9d12ef0a7b7b274e80de5a856917f48c94fd634e710332544`。不覆盖原失败审计，不替fallback_g3完整源G2，仅本地只读/解析/SHA，不运行项目、测试、网络、SSH、GPU或改源。

## 原B2：时间窗口已作实质修正

actor真实constructor facts增加同机monotonic_s与delay15，fsynced receipt后才sleep；父仅允许remaining在[2,15]秒，并将同一window_check交给terminate，后者在TERM/KILL前再调用。超窗失败保留pending，不依靠driver-ready文件缺失推断时间。ScenarioTests的过窗反例确调用真实scenario循环，constructor_start减14秒后拒绝且不调用terminate。此项关闭；不把fixture当实际Ray/POSIX时序成功。

## B1仍未关闭：detached ALIVE滞后＋PID已无时仍可假成功

新代码在final DEAD前检查actor_stopped，修掉“首个state即DEAD直接成功”的旧反例。但detached分支只检查GCS state ALIVE、pid字段等于原identity，然后调用terminate并无条件置actor_stopped=True。

terminate对“原PID已不存在”会记录CPU_registered_process_absent后正常return，没有发送任何信号。因此存在真实生产可达时序：driver已退出→GCS尚报ALIVE但原PID已absent→terminate走absent/no-signal返回→actor_stopped=True→下一次GCS变DEAD且PIDabsent→scenario成功。这仍没有证明实际跨driver存活，更没有父受控释放。normal ACK已有collector.observe/stable核当前PID，detached路径没有这项核验。

最小修正：detached存活证据须GCS/PID绑定加实际identity双读；terminate结果须明确区分原本absent与确实受控发送signal，detached成功不能接受absent/no-signal。如果PID在核后、信号前自然消失，也应按实际失败/无法证明受控释放处理。新增反例应运行真实scenario＋真实terminate决策（proc为fixture），令GCS先ALIVE后DEAD而proc初始absent，禁止清pending/报成功。

现新增positive `test_detached_actual_survival_and_parent_release_required` 仍mock整个terminate且proc.exists默认False，仅核两次mock调用，恰未覆盖上述反例。它证明接线调用顺序，不证明actual survival或signal发生。

## B3：controlled driver本来已退出，也会记录为父受控退出

controlled分支在terminate(driver)之前没有要求driver.poll为None或结果含实际父信号。若driver已自然退出，terminate同样走absent/no-signal正常return，stopped=True；non_detached随之GCS DEAD且actorPID absent时可判controlled场景成功，实际并未做父受控driver死亡。当前ScenarioTests.prepare返回的driver.poll直接0，正例也不排除此情形。

同一窄修即可解决：受控driver路径要求原driver尚活且terminate回报真实受控signal，原本absent或自然退出视为场景失败。GCS在控制前已DEAD也不能算创建窗口内有效控制（例如constructor发receipt后异常退出；缺driver-ready文件并不排除失败）。增加“driver在控制前已退出”和“actor已DEAD/ctor失败”真实scenario反例，不把自然死亡当控制实验。

## 其余delta

共同25行atomic helper先独占pending→完整写/fsync→硬链拒覆发布→目录fsync→删pending；读者不会读取半JSON，已存在target/pending拒绝，不重试覆盖。parent spec/ACK与driver submitted/constructor/ready使用同一helper，普通5秒ACK仅当父已核GCS ALIVE/PID及实际collector双读才发布；比原缺文件推断严格。目录fsync失败发生在link后时，文件仍可见、writer会失败，必须按失败原件保留，不能把单一可见receipt当writer完整成功。当前失败fixture如实说明该边界。

late scope只读inventory拒绝未知，不自动杀未知；pending/无ActorID、identity未知、DEAD但PID在时仍保守拒绝head释放。合作式180/300秒及真实Ray/Node阻塞/部分启动问题仍须完整源G2和未来执行监督审查，不因本次delta变成实际硬上限成功。

本人核整合日志SHA `518e006ed600c9b26fff68f0f51283491c7b33e3917f18c04eeb45b781a9a1f7`，161唯一测试ID逐项等于manifest，PASS/0skip；未重跑。这是Windows fixtures、本机socket/NTFS发布顺序及mock目录fsync，不是Ray/真实Linux父子/IPC/GPU。原first错误及原REQUEST_CHANGES保持。

GATE_RESULT: {"gate":"numeric-cpu-parent-second-view-revision","decision":"REQUEST_CHANGES","blocking":2,"original_B2_window_closed":true,"original_B1_closed":false,"manifest_sha256":"37f43b17dee4bd155c45555e0ba9b0e66e301a891c9b3682044ddc54dc62f0d4","remote_CPU_execution_approved":false,"GPU_approved":false}
