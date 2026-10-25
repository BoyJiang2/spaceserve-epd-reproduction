> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g4-points-report-prompt.md) SHA256 20dd7d06527b11364f762f41f95ea03ae5842c9907d52e220748cc5ecfd219b5。原数字及解释不变。

# G4：首轮实际报告、图表与机制范围

独立只读审查，先读D:/Documents/codex/AGENTS.md、同目录g4-points-prompt.md和draft。Claude额度失败按3.2.1接替。不得改文件、访问GPU、启动实验或读取凭据；只用现有本地文件，可CPU复算。你曾审G3，仅审查未实现，不存在自审实现。

正式首6配置1800formal+120warm已收回并技术通过，远端监督器124199在G4暂停；raw与199文件传输完整性详g4-points-prompt.md。独立数值审查由另一agent承担，你重点审实际生成产物与结论：
- report/space-points-report.md、performance-points.png/svg，report/space-points.json；请实际看PNG或渲染图，不能只看生成器。
- README.md、status.json、真实G3 final review及G2记录、所有performance比较与raw文本必要抽查。
- 同机比与encoder-only/LM保留visual/SM实际78→64/不是fullSIS/固定并发非SLO/跨机跨模型不拼接/差异不能单因果归属，是否都准确。
- 图表布局/单位/mean±SD/P50/P95线型/颜色对应、表值和文字是否相符，包含高点TTFT改善但TPOT P50退化、mask vsunmask微小变化，不误读总体改善。
- 输出IDs不同低5/8及高82/85对320，检查报告不把它说成全部精确一致或未经证据归因为FP16；可读原始文本判断明显错图迹象，90固定案例G3与formal非逐token全同区分。
- 审查状态目前pending为真，不将技术通过当G4或整体goal完成；first6G4须有效结论才扩4点，G5仍待。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号+理由+建议，NON-BLOCKING、QUESTIONS。正文直接回复主执行者，不写marker。只批准实际两点报告范围，不冒充全矩阵G4/G5。
