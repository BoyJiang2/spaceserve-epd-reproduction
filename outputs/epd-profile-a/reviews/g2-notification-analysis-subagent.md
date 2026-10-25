# G2：逐通知间隔离线分析

实际审查者 /root/profile_plan_review，只读，Claude明确额度耗尽依AGENTS3.2.1接替。实际提示prompts/g2-notification-analysis.md，源码analysis/notification_intervals.py及tests/test_notification_intervals.py。未跑GPU或完整数据。

首审REQUEST_CHANGES/B1：第1→2通知并不包含第1通知前P或KV，不能命名完整handoff；其他prefill需实际GPU重叠而不只CPU候选。
修复：通知准确命名first_to_second_notification；另P_to_first_D保存完整P与首D GPU边界/窗口、窗口内迁移copy（包括第1通知前）、不宣称rid依赖；CPU候选和实际GPU重叠分列。新增KV早于通知、CPU相交GPU不相交回归，5项通过。
第二审REQUEST_CHANGES/B1剩余：GPU筛选仍以CPU候选为前置，遗漏异步CUDA晚于CPU。修复：CPU与GPU独立从全部其他prefill worker筛选，追加CPU已结束GPU仍相交断言，5项仍通过，evidence/notification-cpu-tests-fixed2.txt。16索引/端点重复/缺trace未匹配理由补齐。

最终复审原结论：APPROVE_WITH_NITS，G2 B1关闭，未解决BLOCKING0。已核实际CPU与CUDA独立集合及新增异步断言、PASS日志。允许现有数据CPU分析；真实三类窗口覆盖率、未匹配原因和归属仍须G4；高EPD数值归属排除，不关闭G5实际数据项。
Codex落实：批准后qjh000启动CPU PID3853570，输入旧SQLite只读，code SHA和Linux单测日志保存；不新增测量，不改旧raw/吞吐JSON。输出待G4。
