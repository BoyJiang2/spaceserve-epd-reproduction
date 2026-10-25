G1：独立只读审查本次上传计划。先读D:/Documents/codex/AGENTS.md和outputs/repository-setup/main-agent-upload-prompt.md。用户明确授权独立checkout整理、commit/push main和同一已创建私有仓库Release上传，无需例行确认。不跑GPU、不改四个封存源目录/ZIP、不提交权重/环境/缓存/凭据。

计划：核实BoyJiang2/spaceserve-epd-reproduction私有及已有历史，在work/repository-upload/checkout克隆，不force push。四批outputs相对结构内逐文件原bytes复制适合Git的报告/PNG/SVG/小数据/脚本/patch/config/pin/review/清单。大trace/nsys/SQLite及原始归档由Release承载；每个源文件记Git映射或Release覆盖位置，不静默遗漏。原报告不改；必要时docs生成阅读副本改相对链接，保留来源SHA。中文根README区分各host/model/batch/负值和限制，附实际Release URL/bytes/SHA。记录上游固定commit和LICENSE/NOTICE，不把上游patch视原创。

新增.gitattributes禁自动换行改封存bytes；.gitignore排除秘密/缓存。所有Git文件和待传assets递归敏感扫描与大小检查，归档也检查成员/文本；扫描结果不打印秘密内容。验证所有相对图片/链接或明确Release恢复路径；不跑GPU。必要脚本CPU自检，整套新交付G5有效批准后commit/push，创建Release并核API大小/SHA与实际下载，main树/README/图/报告/可见性远端验收。源四目录和原ZIP前后SHA不变。

平台当前官方文档：Git单文件100MiB上限，Release单asset<2GiB，最多1000assets；本轮大包约904MiB无需分卷，如另有超限则无损分卷附重组SHA。G1之后如有实质代码则G2，整理/报告结论不更改已有统计，G5审整体发布候选。审查失败/限额须真实记录；额度耗尽按3.2.1独立subagent接替。

请给APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING、NON-BLOCKING、QUESTIONS。仅审查，不改文件、不访问GPU/凭据、不实施发布。
