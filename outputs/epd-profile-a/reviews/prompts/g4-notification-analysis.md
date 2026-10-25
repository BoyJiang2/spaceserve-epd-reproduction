# G4：逐通知间隔实证与受限报告

先读D:/Documents/codex/AGENTS.md，只读，不改文件、不跑GPU/实验、不读凭据。Claude明确usage_limit接替依同批证据。
G1受限范围、通知分析G2、报告生成G2均APPROVE_WITH_NITS/BLOCKING0，相关reviews/已保存。已G5首审REQUEST_CHANGES/B1通知归属缺失、B2高EPD越5%处置，不能由本执行者自闭。
新analysis/notification_intervals.py在qjh000 CPU PID3853570实际完成cases3/matched6096/expected6096，无重跑GPU。report/notification-analysis.json、notification-intervals.jsonl；evidence/notification-tests-linux.log、notification-approved-code.sha256、notification-analysis-epd.log。旧SQLite只读SHA前后相同并绑定已有G4 accepted traceSHA/API PID。原吞吐/逐请求不改。

请实证G4重点：
- 48请求*127通知间隔=6096，每case2032/2032，无未匹配。按同endpoint/rid每128worker顺序和128outputs、stage/GPU完成/原始timestamp核对；不将只有顺序条件叫显式stepID。
- 实际trace CLOCK,CPU范围/launch/PID/correlation、全部kernel/copy/memset并集与API disconnect外部分/未解释加和，marker与API时间误差分布，有无把重叠或空白归因CPU。baseline无disconnect标记0是未观测，不是API耗时0。EPD稳态token3–128与baselineD通知token2–128明确不同，不相减归因。
- 三类实际覆盖：低EPD2016稳态+16首→次；16独立P_to_first_D完整P和首D GPU窗口均含contextcopy；copy blocks无rid依赖，只时间重叠。高baseline21个输出间隔与其他请求prefill CUDA重叠，是其D通知2032的子集。CPU候选/实际GPU类别独立。
- 从raw至少独立重算时间归属及覆盖率，核handoff全部仅低EPD、16rid唯一、capture窗口与copy覆盖。例高baseline index86/to_token16/rid3f708d662ac94156bee78f24d670c643，155.988019ms，其中全traceCUDA并集120.667839ms、他请求prefill110.499053ms、未解释35.32018ms；不解释为prefill已证明因果。
- 高EPD -5.0027158%只路径存在，定量阶段表排除，高profiled raw/旧诊断计算保留用途范围；未缩窗仍明确。报告和生成器report/report.md、analysis/write_report.py已落实类别子集、含首D口径和无baseline API标记限制。
- 原主要性能/图不改事实：off EPD<三副本、扰动/输出差异/采样峰值/边界事件限制保留。此G4有效后还需G5复审两项闭环和新归档，不宣布整体goal完成。

输出结论APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING具体文件行号、NON-BLOCKING、QUESTIONS，明确实际核验范围。
