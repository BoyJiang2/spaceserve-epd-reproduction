独立只读G4（第一部分：正式2400请求统计/观测扰动；CUDA关键路径与最终报告另审）。请先读D:/Documents/codex/AGENTS.md。Claude明确usage_limit_reached，沿用3.2.1独立subagent接替。

测量来自qjh003，8case共2400formal+160warm，已完成不重跑。原始数据在outputs/epd-profile-a/results/formal，实际采集源码/used-scripts/运行身份均已抓回。统计代码analysis/aggregate.py已G2复审APPROVE_WITH_NITS、3项BLOCKING关闭，reviews/g2-formal-aggregation-subagent.md。新用户goal优先000远端分析，已在qjh000执行全量聚合，report/performance.json与.csv标measurement_host=qjh003、analysis_host=qjh000。旧outputs/reproduction封存不改，固定ZIP SHA 3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38。

请独立核对8case原始请求/配置/重复窗口/输出长度128与visual64每图、相同输入/缓存、GPU/显存身份及采样空隙、capture controls/barrier16请求及全部mode差异、旧有效case选择与SHA前后不变。可用本机Python只读CPU计算/SQLite mode=ro，但不运行GPU实验、不改文件、不读取凭据。检查所有真实首尾bookkeeping与最大memory gap；阈值5%是诊断而非显著性。

当前复算事实（请独立验证）：off EPD/三副本吞吐比low .92981894、high .94077836；on/off throughput low EPD -1.0917%、baseline -.7726%，high EPD -5.0027158%、baseline -3.0872%；不能把high结果四舍五入后藏掉越5%诊断。旧off/frozen吞吐差均<.5%。同图processed IDs全部相同，少量high output token差异必须保留说明，不能宣称全矩阵字节完全相同。全部2400成功，现未声称CUDA计算/通信因果。报告待生成，可先批准事实统计或提出问题；G4最终报告/trace另送。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号+原因，NON-BLOCKING及QUESTIONS。不要仅信自动passed字段。
