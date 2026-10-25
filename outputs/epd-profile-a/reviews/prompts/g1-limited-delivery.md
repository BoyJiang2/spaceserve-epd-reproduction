# G1补充：EPD A离线补齐与高扰动限制

只读，先读D:/Documents/codex/AGENTS.md。不得改文件/跑实验/访问GPU。Claude新实际quota错误见outputs/epd-profile-a/reviews/g4-cuda-report-claude.json，按3.2.1接替。
当前总goal明确：003已2400formal+160warm不重跑；后续000分析，不新增GPU采集。EPD G1-G4有效，但新G5发现两BLOCKING（消息/待主执行者保存g5-delivery-subagent.md）：
B1 approved-scope.md:49/52要求稳态D、P->KV->首D、baselineprefill附近输出间隔，逐匹配通知间隔数值分解/覆盖率；现只有整请求kernel并集/handoff。拟新增只读CPU分析已有SQLite，以同rid worker迭代顺序+对应API token关联；明确GPU活动并集、无关联GPU活动、API disconnect等待（可重叠另报）、worker结束到API与未解释余量/匹配率；不能把空闲认成CPU因果，不能叫kernel并集依赖关键路径。至少给三类可审时间归属，无证据部分单列。代码先G2，真实分析G4，再G5。
B2 旧approved-scope.md:53超过5%时trace仅路径存在性，并缩短后再审。高EPD -5.0027158%，新用户goal又明确不重跑。拟在本批限定高EPD trace仅路径存在性，去掉对其的量化瓶颈解释；其原始raw仍保存。低EPD和baseline在阈值内，用于数值分解；不新增/缩窗采集、不改变测量设置。明确高负载EPD off因果瓶颈本批未解释，缩窗留下一轮另审，不虚称完成旧全部定量目标。

请审：新goal约束下该受限交付+现有数据补分析是否符合当前授权和完成标准，还是必须用户再次裁决；不允许主执行者静默改标准。仅范围复核，不批准未写的分析代码/未见的数据，不预判B1达标。
给APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，具体BLOCKING，NON-BLOCKING，QUESTIONS。
