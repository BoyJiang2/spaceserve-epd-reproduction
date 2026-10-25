> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-report-renderer-prompt.md) SHA256 fac2d816a8f3dccb171297614ebf7758b6e60be14b41b298aab6212dad7f95fd。原数字及解释不变。

# G2：Space正式结果报告与图表生成器

只读，先读D:/Documents/codex/AGENTS.md。Claude明确额度耗尽依3.2.1接替，证据本批g2-model-runner-claude.json/epd-profile-a/reviews/g4-cuda-report-claude.json。不要改文件、跑实验、访问GPU。
新增analysis/write_space_report.py。正式GPU监督器18837当前进行first native低负载；完整points尚未出结果，不预设收益，不生成假数据。仅读已G2的space_results.py将来产出的report/space-{points,all}.json，当前仅语法PASS，未运行画图。
请核字段/单位、300合并inclusiveP50P95与三次吞吐meanSD、图颜色/线型/标签/误差条、native比与mask/unmasked比、output差异分母含warm320。points2loads/full6loads，实际roles2/3由已审核dataset决定，生成器拒绝缺矩阵。
报告机制使用有效cold/restart G3事实：90固定案例、actualFP16co-residency、encoder stream78->64 zero78 reapply64 first64、真实GPUoverlap；只encodermask非互斥decoder/fullSIS/算力比例。decoder仍有visual权重，全部进程采样内存计入；profileroff/同MPS/GPU预算；proc kwargs被丢弃警告如实写，actualRGB448/视觉tokens256或1024/processed IDs对齐。
不跨2B4090/L20、7B000、MiniCPM3卡EPD绝对排名，不将mean差异/overlap当显著因果，不自动授权新基线或模型扩展；当前G4/G5状态从真实status.json读取，audit不当独立审批。已封EPD目录/ZIP不修改。
仅评生成代码，actual图表/统计须数据完成后G4目检独立核对，不能因此关闭G4/G5。请给结论/BLOCKING具体行号/NON-BLOCKING/QUESTIONS。
