# G4 全量报告、图表与renderer两行delta

实际审查者：独立只读 subagent /root/profile_plan_review。接替本次真实Claude usage_limit_reached（g4-full-report-claude.json，reset03:50）；未访问远端/GPU、改文件或marker。

结论：APPROVE_WITH_NITS。BLOCKING：0。仅批准实际18配置报告范围，不替代独立数据G4、G5或归档验收。

实际核对：

- 查看六负载PNG：柱顶数字旋转90°后可读，无明显重叠/裁切，颜色、单位、mean±样本SD及P50/P95线型正确，SVG有效。两行renderer delta不改变统计。
- 18行表格全部数值与JSON逐项舍入一致；六行百分比和显存范围一致。unmasked/native −6.32%至＋5.86%，mask/native −7.52%至＋6.29%；新增四点mask/unmasked −7.33%、−6.98%、−1.09%、−2.94%，负值未隐藏。
- 新增四负载全部320配对图片序、processed IDs与输出差异key核对一致。Space差异62/54/0/93，mask49/60/0/96；抽查原文未见明显错图，不能保证全量语义质量。
- TTFT改善同时TPOT退化、低点TTFT退化及mask尾延迟保留。机制限定、额外visual驻留、固定顺序/时间漂移限制、EPD高扰动仅路径用途准确。未提前宣称全交付完成。

NON-BLOCKING：

1. 完整报告正文建议增加新增四点mask无吞吐收益的说明，或直接链接final-summary.md。
2. final-summary.md:16“解耦使TTFT”建议改为“解耦组TTFT相较原生”，符合因果限定。

QUESTIONS：无。

主执行者：两项建议均采纳，增加完整结论链接并改为组间观测措辞；统计/原始数据不变，文字delta另请同审查者复核。
