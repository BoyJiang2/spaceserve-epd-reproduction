# G5 EPD精确候选发布批准

审查者：独立/root/profile_plan_review，依AGENTS.md3.2.1接替Claude额度耗尽；提示prompts/g5-epd-exact-commit-publication.md。只读本地审查。

结论：APPROVE，BLOCKING0，允许限定两阶段发布。

已核本地commit e4c7e84f500662760571f39cc2ef558ce7750a0d及parent3acdc797353256e22e4b123e6cf7087131100c73，1193项范围符合候选，工作区干净；两资产实测SHA匹配，发布客户端v2 G2已批准。

允许保存真实批准、普通push该精确commit至main；新tag epd-revision-2026-10-27绑定该commit，以blocked创建draft，仅上传已审ZIP及source-files.json；实际下载bytes/SHA、tag/commit/集合复核通过后发布；核public/远端main文件与原Release/tag/七资产不变；第二commit仅真实审查与验收回执及pending改实测状态，不改raw/签名报告/资产。

任何目标/tag/资产/提交不匹配停止，不覆盖、不移动历史、不forcepush。尚未远端验收，不可称发布完成；不包含GPU、Space数据或总目标完成。
