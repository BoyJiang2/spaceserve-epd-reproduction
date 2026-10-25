> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/epd-followup/reviews/prompts/g2-g3-followup-offline.md) SHA256 459cfafa8c66cba2da84f0e9017054c51f616e771fc67d4a5997700c13cde358。原数字及解释不变。

你是独立只读审查者，当前仅G2离线代码与G3事件语义。只用Read/Grep/Glob；不改文件、不跑命令、网络/SSH/GPU、不读凭据或聊天历史。项目根 D:\Documents\codex\2026-10-23\new-chat-2。最多9次只读调用，15分钟上限。

G1已由Claude APPROVE_WITH_NITS，用户“继续工作”仅批准这个离线批次；实际GPU profiling/PD仍须新具体方案与用户确认。旧outputs/reproduction/与ZIP不动。

必读文件：
- outputs/epd-followup/scripts/analyze.py（尚未跑完整数据）
- outputs/epd-followup/tests/test_analysis.py（6 CPU测试已通过，含实际callback AST隔离复现；没有导入官方模型或GPU）
- outputs/epd-followup/source-notes.md
- outputs/epd-followup/source/replay-manifest.json
- outputs/epd-followup/source/epdserve/orchestrator.py 相关callback249–266行
- source/epdserve/engine_decoding.py 的DecodingBegin/End位置、engine_context.py的ContextEnd/StepOutput及迁移、api_server.py返回timestamps。可用Grep带上下文读取，不递归日志。

G2：来源从旧summary精确选择16H20配置4800正式，首1/C1来自cache-fix、其余原矩阵。完整分析前后验证旧969文件manifest及原外层ZIP SHA，输出必须在旧root外，不覆盖已有analysis.json。重算TTFT/TPOT/E2E分位数对账旧值；每case保留300请求及三次重复。首次间隔与后126间隔分开，后者P50/P95/P99/max，按端点重建首末token输出窗口重叠代理（不是GPU batch size）；同timestamp合并通知入bin0，不参与重叠均值。EPD阶段可加的只有逐请求有序TTFT分段，不加分位数；异常分段保留标志/不伪造。请查丢数、负值、时钟/分母/percentile及混用来源等阻塞问题。

G3：实际运行代码的文本重放来自完整官方commit 9b111f710dfb4724072b603d626a1e4dad93ef1f+已归档最终H20补丁（仅改api_server/llm_async；source/replay-manifest记录16文件，另外四份实际baseline适配器generate AST相同）。事件Enum查询vs字符串存键导致DecodingBegin迭代覆盖，实际callback测试复现。P产生首token，事件记录与API通知的先后须谨慎；API真实timestamps位于async for内await is_disconnected之后，不能拿StepOutput.timestamp当返回值。源码笔记精确描述这些局限。请检查源码事实，单独给G3是否可用于后续事件跨度解释；这不是硬件预检，不需要重跑P2P。

输出分别G2、G3 APPROVE / APPROVE_WITH_NITS / REQUEST_CHANGES，分别列BLOCKING数和最小处理（文件行号）、NON-BLOCKING、QUESTIONS。不审尚未运行的完整数据结论，不批准GPU实验。
