# G1 CPU展示补充：不完整矩阵的逐次散点图
先读D:/Documents/codex/AGENTS.md，outputs/spaceserve-revision-20261027/plan.md及已有g1/g2-report-renderer审查。独立只读subagent接替Claude限额；不GPU/网络/凭据/改文件。
本批正式54cell仍按冻结顺序运行，实际raw尚未抓回/分析；已G2的renderer在partial时目前不画任何图。原G1 plan的限制是“缺项则全清单/原始逐次/不生成完整三重复总体CI或完整矩阵加速结论”，并未要求禁止逐次原始点图。用户明确要求GitHub尽可能展示baseline对照及图表。
请审一个事前CPU展示补充（不改model/load/budget/order/protocol/GPU设置）：partial时若无global_errors且valid_cells>0，可生成一张2x3按六负载分面图；横轴时间区组0/1/2，三role彩色点分别表示每次实际成功req/s，固定轻微水平偏移。只画通过单cell全部输入/身份/显存/时序校验的原始值；不连线/不平均/不拟合/无CI、不填零，坐标从0起。每panel明确valid/9及未执行/invalid具体block-role文字；全部54计划单元的状态及54原始配对表继续完整保留。主标题醒目“PARTIAL / per-run observations / no aggregate inference”。global冲突则不画；full54仍保留原mean±SD与paired df2 CI图区分。
在见正式性能数值前固定此规则，不按收益筛点；gain/regression同样显示。README明确partial，不能称全部顺序平衡实际已达成，不能解释机制因果。合成CPU图必须大字SYNTHETIC，不上传成实测。
请G1判断是否符合原目标且不放宽实验/统计门槛；是否仅CPU展示调整而无需新增GPU预算/实验设置确认。若不合适请REQUEST_CHANGES并说明。此轮只审方案，尚未改renderer代码，无真实图。输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES与blocking/nonblocking，主agent落盘。
