G2：只读审查本次发布工具。读D:/Documents/codex/AGENTS.md、work/repository-upload/g1-plan-prompt.md和g1-plan-subagent.md。实际Claude weekly quota错误g1-plan-claude.json，按3.2.1接替。仅你审查，主执行者实现；不访问凭据、GPU/发布远端，不改文件。

代码：
- work/repository-upload/build_repository.py：四批来源及canonical ZIP逐成员SHA/CRC/精确集合绑定，原件只读；小文件原bytes复制checkout，大trace/nsys/sqlite/gz/so及>=16MiB从Git排除，用原完整ZIP Release覆盖，每文件记录asset/member/SHA；七个最终和历史ZIP全读扫描，gzip解码扫描；强特征秘密命中阻止材料化后续发布。另建docs/reading只改链接的阅读副本且记录来源SHA/无法定位的历史路径。禁自动换行转换，不跑GPU。
- work/repository-upload/github_api.py：只经Git正常credential helper获取本任务所需现有凭据于内存，不打印或写磁盘，API固定授权仓库。
- work/repository-upload/release_assets.py：仅固定私有仓库/固定tag/枚举asset；create以实际commit建draft，不覆盖已有release；上传前核SHA/size及<2GiB，每20秒输出无秘密进度；服务器SHA/size核对；下载实际asset流式SHA，跨host redirect移除Authorization、拒绝HTTP；verified全集才publish。候选G5前不执行commit/push/create/upload。G5将明确两次提交：先完整可读候选推main（发布状态pending），建draft/upload/downloadSHA/publish，再纯验收元数据提交main；不存在的预计URL不冒充实际已发布。

请核凭据/越界/封存保护/不遗漏与大小/失败处理/重定向安全，指出真正问题及最小修复。assert入口拒绝-O。发布后会验main全部Git blob SHA、实际下载SHA/页面/图片和private，不凭退出0。尚未执行builder/上传。

给APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号原因建议、NON-BLOCKING、QUESTIONS。回复我保存。
