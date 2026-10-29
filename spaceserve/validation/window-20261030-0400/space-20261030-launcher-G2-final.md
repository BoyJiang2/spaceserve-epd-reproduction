# 单phase launcher — B1修正后的精确G2复审

reviewed_at_utc: 2026-10-29T18:34:10Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，初审B1已闭合；只批准此本地launcher源码，不授部署、实际phase Gate或GPU/formal执行。**

初审原文space-20261030-launcher-G2.md的REQUEST_CHANGES/BLOCKING1保留，不覆盖。独立重算最终源码tools/run_space_window_20261030.py SHA `6d3663be79bc71a0eeeaa5967e597a23ae6062f40eb0217cfdb89c2566c0ad07`、test_run_space_window_20261030.py SHA `d3e2b9de33681758de89ac49b5525605d1f95c81f785c75ab78ad39541310d13`，与final-tests.json精确一致。本审只读完整最终两文件与原审、policy、final日志，不测试、网络、SSH、GPU或改实现，仅保存本审查。

## B1修正核验

原B1是源核/SITE/资产SHA/refresh20秒之后缺少最后完整预算与freshness复核。最终新增supervise_phase，在调用既有supervision.supervise前，以实际time.time毫秒重新policy.validate同一原始proof、精确cfg/phase；得到完整work+120和fresh<=300秒等约束后，才传该work_seconds启动。没有重标proof.observed_ms，没有缩短工作预算或放宽清理。

main仍保留最初准入以阻止不合法窗口先写phase资料；完成所有源/identity核、claim、environment、GPUphase refresh并open新log后，才调用上述末次准入。该调用在原try/except/finally内，末次准入失败会写实际exit1/error而不进入supervise/Popen，无自动retry。成功terminal记录实际admitted_ms/limits；phase运行和清理仍由原监督器与END120检查约束。修正小且与问题直接相关。

因此06:37最迟formal点不能因refresh/准备时间自动越过：若原clock在边界通过而实际spawn前已晚1ms，末次policy拒绝，不启动；09:58仍为停止工作/预留清理界而非故障时绝对释放保证。formal底层自身201分钟Gate也保持，并未用末次策略代替其实际G2/G3/锁/idle。

## 实际测试材料范围

final-tests.log实际6项distinct launcher tests全部OK，JSON exit0/源码SHA一致：原3 argv＋新增3真实supervise_phase调用边界（完整12060秒预算传给supervision、首次通过后1ms过界不调用supervise、snapshot跨300秒不调用supervise）。通过Mock/clock调用的是生产末次校验函数，不是测试中重新实现逻辑，针对B1有效。之前discovery15包含另9个imported window tests，已如实单列；不能报15个新测试。本审未重跑。

6项不覆盖main所有IO异常、真实SIGTERM/POSIX pidfd清理、MPI/Ray/CUDA或远端部署行为。初审其余认可与边界保持：exact commit/clean/root/hostUIDboot/GPU2严格0、snapshot+approval、独立phase claim、原runtime Gate而非marker复制，canonical Git helper加载、新RUN/nonce及已有pidfd监督器，单phase/无串行自动Gate/无retry/无延期。

## 后续明确条件

- 精确G5/Git-first发布并部署指定commit、全文件SHA、具体本地SSH controller/外层超时与PID创建身份及phase execution审批，仍须另审；本G2不替代它们。
- 原5ef源码/测试与first/final失败资料应保持可追溯，可用精确原源码或修复patch保存，不追溯抹除初审B1。
- 前述新run实际CPU/numeric/313和每阶段G2/G3必须完成，不能把本组件源码APPROVE当runtime PASS。04前不执行远端phase；不足全预算不启动，失败/UNKNOWN不重试。

GATE_RESULT: {"gate":"G2-space-20261030-launcher-final","decision":"APPROVE_WITH_NITS","blocking":0,"closed_findings":["B1-final-full-budget-and-freshness-revalidation"],"source_sha256":"6d3663be79bc71a0eeeaa5967e597a23ae6062f40eb0217cfdb89c2566c0ad07","test_sha256":"d3e2b9de33681758de89ac49b5525605d1f95c81f785c75ab78ad39541310d13","scope":"single_phase_launcher_source_only","GPU_approved":false,"formal_approved":false,"deployed":false}
