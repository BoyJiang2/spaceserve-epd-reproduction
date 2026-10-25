> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-report-tradeoffs-prompt.md) SHA256 016226c871a1780128af4ee88b36c04ee98a26d51c5f113a22ac4d11411f9e08。原数字及解释不变。

# G2：仅本地报告文字生成delta

独立只读，先读AGENTS。Claude同批明确额度失败，依3.2.1接替；不改文件、不访问GPU、不运行实验。只审当前analysis/write_space_report.py新增“首轮低／高两点的具体取舍”一段（既有G2生成器已批准），及真实report/space-points.json字段来源。远端正式/分析冻结代码完全没改，driver仍G4暂停。

为什么：实际高点TTFT P50改善但TPOT P50变差，低点TTFT P50也比原生差，mask vsunmask仅低-0.56%/高+0.41%。G4审查者建议显式写取舍，不能只给表格。新增仅用已有indexed字段动态格式化mean ratio百分数和TTFT/TPOT P50，第一对1/C1、4/C8在points和all都已测且都存在；不修改统计、raw或图形。

请核百分数分母、P50单位ms、正负号、两点/三roles范围和报告条件是否准确。固定描述高TTFT改善/TPOT变差是本已冻结首轮数据事实（all复用相同两点），不是预言其它四点。是否存在生成器误称稳定/显著收益、丢失原输出差异/失败范围等。可读旧g2-report-renderer-subagent.md与G4 prompts。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING、NON-BLOCKING、QUESTIONS；正文回复主执行者保存。不得写批准marker。只批准文字生成delta，实际文字由G4独立审查者再核。
