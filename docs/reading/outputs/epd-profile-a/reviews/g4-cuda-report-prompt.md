> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/epd-profile-a/reviews/g4-cuda-report-prompt.md) SHA256 dabbd5e550e0e0122e31308fe2164cda39dc468622c7b7659826a803bab7736e。原数字及解释不变。

你是Claude独立只读审查者。先读D:/Documents/codex/AGENTS.md。G4：EPD方案A的CUDA关联分析与最终简短报告，不涉及新GPU实验，也不是SpaceServe验收。禁止改文件、GPU/实验、凭据；SQLite必须mode=ro。允许只读CPU Python -c复核，不能写文件或调用CUDA。

本批outputs/epd-profile-a。qjh003原始8配置2400formal+160warm已完成不重跑，分析实际qjh000。事实统计G4第一部分由独立subagent批准（此前Claude明确usage_limit_reached后的接替），reviews/g4-formal-statistics-subagent.md含其逐项独立复算及限定。新trace代码G2同样APPROVE_WITH_NITS/BLOCKING0，reviews/g2-cuda-analysis-subagent.md；4项CPU测试含真实SQLite fixture验证同correlation跨进程不串、GPU完成晚于CPU范围合法，evidence/trace-rules-cpu.txt。Claude现在已恢复返回其他审查，故本新G4优先请Claude。

请审analysis/trace_analysis.py与report/cuda-analysis.json、analysis/write_report.py及report/report.md、throughput-latency.png/svg、performance.json/csv。原始8 SQLite在results/formal/on-*/traces，各测量原始JSONL/summary/config、RGB/runtime同目录。必要时只读Python可用C:/Users/23520/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe。不要仅信passed字段。主执行者已完整CPU运行trace分析，4case64完整选定请求/8SQLite通过，测量与分析主机分开，实际raw .nsys-rep均保留。

核对：端点+rid命名空间；128api.output逐项对应raw timestamps；E/P/D或baseline prefill/decode真实CUDA关联为同进程correlation、runtime完全位于同线程同步workerNVTX；GPU可以晚于CPU结束。全部选定kernel在capture范围，Nsight进程局部deviceId=0不可当物理GPU，共用已验收runtime PID→UUID。每请求kernel union含共享batch，只能称已关联活动曝光，不是独占成本。整个capture迁移copy统计不分rid、不声称带宽。高C8有77–83边界请求，选定84–99共16完整，跳过活动计数已输出；高baseline三trace开头分别88/354/346 kernel在第一worker范围之前，不当完整GPU总成本。6个baseline实际无mixed prompt批，代码已明确拒绝混合。

报告必须保留：off EPD/三副本low .9298189434、high .9407783602无加速；on/off EPD高-5.002715819%越5%诊断阈值，不是显著性；capture start计入第三重复吞吐，但在末16提交前，stop不计；不能说纯profiler开销、不从分母事后扣除。高并发不同有效output token对数保留，不能说全矩阵字节相同。采样峰值显存与实际间隙明示，不做SLO。阶段交接gap含通信/排队调度，不当纯传输；CPU await不当GPU；GPU因果只有限假设。不得拼旧硬件数据作同机排名。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号与理由、NON-BLOCKING、QUESTIONS。批准范围为本EPD方案A报告，G5另做，不将整体goal标完成。
