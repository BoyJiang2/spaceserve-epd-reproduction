# G4：首六配置实际报告与图表

实际独立审查者/root/profile_plan_review，范围g4-points-report-prompt.md；按同批额度失败/AGENTS3.2.1接替，只读，未操作远端/GPU/marker。

结论APPROVE_WITH_NITS，BLOCKING0；仅首6配置1800formal+120warm，非全矩阵G4/G5。

已实际看PNG：图例/单位/吞吐mean±样本SD/P50实线/P95虚线正确，无明显裁切，SVG有效；六行表值与JSON逐项舍入一致。encoder-only、额外visual驻留、同机比较、固定并发非SLO与因果范围准确。

四类输出差异原文及首次分歧抽查未见明显错图；正式差异Space低5/300、高79/300，mask低6/300、高81/300，与含warm5/320、82/320、8/320、85/320相符。不据抽查保证全量语义，也不归因FP16。

状态初读滞后，已窄核修正为实际完成1800、技术1800/120/6、独立验收0、G4 in review/G5 pending，含义明确。

NON-BLOCKING：建议突出高点TTFT改善但TPOT P50由19.27升至22.03/22.21ms；低点TTFT也退化，不能说全面改善。Mask/unmask低约−0.56%、高+0.41%，仅三次均值差，不称显著/稳定。高点mask E2E P95也略高于native，应与中位收益同读。

另一数值范围仍须实际通过。本审查未写marker/操作远端/GPU。

Codex处理：计数已同步，正式/G4数量分别标记。取舍段落本地renderer新增delta经独立G2 APPROVE/BLOCKING0后才生成；表中全部退化保留，E2E P95等文字窄核后另记。原始数据及远端冻结代码不动。

同审查者对已实际生成取舍段窄核：APPROVE_WITH_NITS/新增BLOCKING0，原G4有效。新段与JSON一致，准确说明高TTFT改善/TPOT P50退化、低TTFT退化与mask−0.56%/+0.41%不证明稳定收益。建议段间空行。尚未生成的变异/E2E P95文字未预先批准；待实际生成后再窄核。

实际生成后的最后三项文字G4补充：APPROVE/新增BLOCKING0，原首轮报告G4有效。已核当前稿低/高段空行、与数据G4一致的输出变化/原因未定位/全量语义限定，及高点mask3987.63/native3974.69ms E2E P95与表一致。仅这三项delta，不扩大到全矩阵/G5。
