# G5处理与来源回答

实际G5：Claude (claude-opus-5-5)，session `baf9dad2-d355-4528-b56c-02c841d6131a`，APPROVE_WITH_NITS、BLOCKING为0；原文 `g5-claude-final-20261023.md/json`。G1–G4是Claude额度耗尽时用户授权接替的独立subagent审查，额度恢复不使已有有效批准失效。G5用时496298ms，18次只读调用，permission_denials为空。

- N1：同步report、状态、delivery-audit、完成核对与AGENTS。最终验收标志在收尾校验后更新；额度失败及blocked页已明确标为历史。外层ZIP的SHA在ZIP完成后追加到原AGENTS，ZIP内快照保留封包时状态，避免自身哈希循环；外部最终AGENTS快照另存。
- N2/Q2：补齐初次RGB G2、G4代码预审及G4实际复审索引。两次G2续问由实际审查者从同一会话逐字回传，存 `prompts/g2-rgb-followup-actual.md`、`g2-full-replay-followup-actual.md`；均注明实际agent、AGENTS授权和额度失败指针。没有改写原结论或伪造事前批准。
- N3：报告补四问小节，只复述已有数值及限制；原处限定4090三点和L20无mask低点的差值与重复波动同量级。统计脚本、摘要、原始数据未改；文字补充另存report/final-editorial-notes.md，复算正文时可参考。
- N4：保留绝对图片路径，遵守本应用显示要求；README已说明换目录后用make_report.py刷新。没有把相对路径不能预览的问题转交用户确认。
- N5：显存表后明确旧L20完整模型基线保留为有效测量，但对应EPD仅诊断，不支撑EPD性能结论。
- N6/Q3：acceptance本身不重复列七文件SHA；audit_cache_fix.py读取report/cache-fix-code-manifest.json并逐个核对各host实际used-scripts后才生成acceptance。manifest、实际快照、审计源码与G4独立缓存复核均已入包，README补指针。
- N7：README明确整合run_epd_h20.sh本轮没有端到端执行；实际旧脚本与补测脚本有单独快照/证据，批准没有被表述成执行通过。
- N8：完整文本payload的凭据特征扫描结果另存report/credential-feature-scan.json，只记录文件名/规则与计数，不输出任何匹配值。这是启发式特征检查，不是绝对无凭据证明。
- Q1：g5-final-delivery.md是候选生成前保存但未执行的subagent草稿，属于候选958个payload；实际本轮Claude提示词g5-claude-focused.md当时位于交付目录外，现与实际结果一起新增入包。不是候选生成后悄悄添加草稿。

收尾证据：候选到最终的完整文件差异、受保护目录字节一致与指定统计非时间戳字段一致记录在ZIP旁reproduction-h20-differences.json；最终完整SHA/CRC输出在reproduction-h20-integrity.json和.zip.sha256。它们位于ZIP外，避免校验文件包含自身哈希。原始data/evidence/configs/patches与scripts全部保持候选字节。若校验失败或新增统计/因果修改，按G5条件重审，不沿用本批准。
