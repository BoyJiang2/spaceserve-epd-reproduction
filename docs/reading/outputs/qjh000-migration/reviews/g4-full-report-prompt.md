> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g4-full-report-prompt.md) SHA256 83f87ff2b8f8fb9cfde1523838d51eb6cffaac772a07d93add1fdf93698ac4fd。原数字及解释不变。

# G4 全量SpaceServe报告与机制边界（在真实全量报告生成后调用）

独立只读审查。先读 D:/Documents/codex/AGENTS.md，不修改文件/marker、不访问远端/GPU、不运行实验。可本地CPU只读核数据。正文回复主执行者保存。

范围outputs/qjh000-migration：report/space-all-report.md、report/final-summary.md、performance-all.png/svg、space-all.json，以及README.md/status.json、G3原始机制证据及真实reviews。另有独立数据审查，不由本范围替代。

检查18配置5400formal+360warm的图表/表格/正文与JSON/原始数据一致，均值±样本SD、pooled P50/P95、失败率、128输出、进程合计采样显存均表述准确。核图表可读性和所有负载的改善/退化，无只挑有利点。重点核新增四负载，三组公平输入/设置/单卡预算，三重复并非显著性或到达率SLO。

确认机制只声称已证的FP16同GPU驻留、cold/restart固定90正确性案例、实际编码/语言CUDA重叠、同实际encoder stream mask 78→64/恢复/重施/首执行64；mask不是decoder互斥分配/完整论文SIS，LM仍含visual、另有encoder显存。正式期间关闭profiler，不能将预检重叠比例解释为正式加速或利用率。

输出IDs差异保留，不无证归因FP16或保证全量语义/逐token一致；检查raw是否足以支持现有路由表述。TTFT为服务端首token−客户端提交，非首token回传；高点TPOT和低点TTFT退化、尾延迟、额外mask收益小及三次波动必须保留。

区分旧4090/L20 2B、qjh003 MiniCPM EPD三卡、qjh0007B单卡，不拼跨硬件/模型绝对排名。EPD A已2400+160受限G5封存：off低/高0.930/0.941×三副本，高EPD观测扰动5.0027158%超阈，仅路径存在；不要求重跑、不定量解释off因果瓶颈。旧失败和采样失败独立保留。

报告应回答可运行/机制、各负载收益退化、显存/通信/兼容/调度可证与不可证边界、下一轮是否值得扩大（不实际新增PD/DistServe/模型）。主goal仍active直到fullG4/G5/归档完整性，不能在G4前宣称全交付完成。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，列出具体核对范围与数字、BLOCKING文件行号理由建议、NON-BLOCKING、QUESTIONS。不是最终G5或ZIP验收。

实际全量已收齐并技术passed，archive9,301,339bytes/415payload，SHAd7d75ef664e750ba87b3810ba43ccc3b06ff0f159814d28cba59a8ac9f0e6814；本地全SHA/gzipCRC/EOF/唯一成员集合核验通过。主执行者发现全六点柱顶数字重叠，已仅将all图bar_label旋转90度，points图不动，并将“SM额外变化小”文字限定为首轮两点，避免误概括新增四点的负值。请一并只读核这两行本地renderer delta（不改统计、不触远端冻结代码），实际新PNG已主执行者目视无重叠/裁切。全文结论应突出新增四点掩码吞吐均下降、未划分4/C1 −6.32%与4/C8 +5.86%，保留固定顺序/时间漂移未独立排除的限制。
