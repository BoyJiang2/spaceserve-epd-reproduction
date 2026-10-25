> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/epd-profile-a/reviews/g2-cuda-analysis-prompt.md) SHA256 636d16cd40c15ecbf3ffd7f43c8b07ce59eb5d844abed18e2adf74c7221aea8a。原数字及解释不变。

独立只读G2：本批额度耗尽接替沿用，先读D:/Documents/codex/AGENTS.md，不改文件、不访问GPU/实验、不读凭据。

新增analysis/trace_analysis.py，复用已批准aggregate.py的digest/stats/runtime pin；tests/test_trace_analysis.py与evidence/trace-rules-cpu.txt。只读003已完成的8 SQLite，在qjh000运行CPU分析，测量来源仍003。2400正式统计另已G4第一部分批准，本次不是GPU新测量。原先pilot worker/API打点G2/G3批准过，源码results/formal/used-scripts/observe.py及实际SQLite可核对。

核对：同进程correlationId、CUDA runtime完全落在同线程同步worker NVTX内建立launch关联；GPU kernel可能结束晚于CPU范围，不能用CPU await当GPU。按末16正式请求(index84–99,rep2)的端点+rid选择，baseline三端点ID命名空间不可合并；128 API输出与原始server stamps逐项对齐、选定kernel全在capture内、实际workerPID/三物理GPU与G3pin核验。kernel时间合并取union，批量共享kernel只是每请求曝光，禁止求和成独占成本；baseline prefill含vision不分造E。E末→P首及P末→D首仅GPU间隔，含通信/排队，不标纯通信。migration worker label仅blocks没有rid，因此whole-capture总copy数/bytes/union，不能按请求分摊或称带宽。C8另有之前77–83边界请求，单独列出extra boundary IDs不混入16完整请求。

G2审逻辑、原始schema与测试，不仅信passed；可CPU只读检查实际SQLite，禁止写入。输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING文件行号+理由、NON-BLOCKING、QUESTIONS。全量执行结果随后G4另审。
