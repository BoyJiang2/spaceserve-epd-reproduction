> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/epd-profile-a/reviews/prompts/g5-delivery.md) SHA256 ca5a6b0c9cd6b781363963de04bac4f1616456f2286789fa6d22c79752e130f1。原数字及解释不变。

# G5：EPD方案A独立交付验收

先读D:/Documents/codex/AGENTS.md，仅只读，不改文件、不跑实验、不访问GPU、不读取凭据或发外部消息。Claude实际新quota错误g4-cuda-report-claude.json（usage_limit_reached,reset22:50）依3.2.1接替。

验收本批EPD方案A，不是SpaceServe或整体goal。固定qjh003实际完成8配置2400formal+160warm，无重跑；qjh000仅后续CPU分析。G1/G2/G3、统计G4、CUDA及报告G4均有效APPROVE_WITH_NITS/BLOCKING0。你已做过G4，此次检查交付完成标准与可复算/归档，不需重复全部统计。

候选：outputs/epd-profile-a/，README.md、status.json、plan.md、approved-scope.md、report/report.md、report/performance.json/csv、report/cuda-analysis.json、PNG/SVG、analysis/、tests/、results/formal/（8原生nsys+8SQLite/逐请求/运行脚本/runtime/identity/memory/controls/补丁），reviews/实际结论和提示、evidence/。
候选SHA256SUMS455payload；ZIP work/epd-profile-a-g5-candidate.zip，456entries，235657666bytes，SHA10b5cca20852422c6e59527767865c4f342decdc61442bc559a4c6934eebbefd。逐文件ZIP/目录bytes及CRC通过，outputs/epd-profile-a-candidate-integrity.json。__pycache__/.pyc不是payload。旧封存reproduction/与zip、epd-followup/及zip不得修改；本批聚合已检查旧969manifest及固定ZIP。

请核：
1. 约定配置/全部原始数据/正确性与G3、实际采集覆盖、版本补丁命令可复算，若不能确定明确写缺口。
2. 结论保留无加速，-5.0027158%为诊断而非显著性/纯GPUprofiler；区分测量003和分析000、输出差异/边界/采样显存/共享kernel/因果限制。
3. G1-G4审查来源真实、无BLOCKING；G5通过后将仅更新README/status/report状态句和生成器同步、保存本次真实G5记录、重新SHA封ZIP并完整校验，旧raw/统计不变。这类收尾写入不伪装事前批准。
4. 若交付存在阻塞请给文件行号/具体需补的材料；允许本批单独完成、整体目标继续active。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING、NON-BLOCKING、QUESTIONS。仅有可复跑命令不代表已经独立复跑；明确实际核验范围。
