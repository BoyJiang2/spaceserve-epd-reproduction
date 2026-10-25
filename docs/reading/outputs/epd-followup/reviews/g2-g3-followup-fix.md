> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/epd-followup/reviews/g2-g3-followup-fix.md) SHA256 dbb17377b21127fd148c8dc08d71dddffe9362a9964cf73a673c19f416aba80d。原数字及解释不变。

审查者：Claude（claude-opus-5-5），只读，本次 4 次调用：g2-fix.diff、test_analysis.py、source-event-excerpts.md，以及原文件 api_server.py:132–161 抽查。cpu-checks.txt 未读，"9 个测试通过"按你的说明引用。

## G2 复审
**结论：APPROVE_WITH_NITS；B1 可以关闭；剩余 BLOCKING 0。**

- **B1 已修复：** freeze_snapshot 现在要求恰好 969 条、清单名不重复、外层 ZIP 的 SHA 与固定值一致，并把 ZIP 内 `reproduction/SHA256SUMS` 与目录清单逐字节比对。新回归测试正好覆盖"改目录数据并重新生成清单"的情形，且被拒绝。mock 只在测试内用，生产常量和命令行参数不变。
- **N1–9 均按说明落实：**
  - -O 守卫是 `run()` 的第一句。
  - 后续间隔的 max 和零间隔计数与首间隔分开。
  - kv 字段已改名，并写明只有单向含义；API 时间差改为带符号。
  - 布尔字段只输出计数；EPD 输出无效分段数。
  - 输出目录须为空，并有双向祖先守卫；读文件用 UTF-8。
  - 配置须精确等于约定的 16 项，host 由 source_case 路径和 role 后缀交叉校验。
- **NON-BLOCKING：**
  1. 测试没有覆盖真实 ZIP 的成员名和字节。若不符，完整运行会在启动时直接失败（安全方向），首次运行请记录结果。
  2. manifest_sha256 与 directory_content_sha256 现在等值，可删一个。

## G3 新增范围
**结论：APPROVE_WITH_NITS，BLOCKING 0。**

抽查原文件 api_server.py:136–161，与摘录逐行一致；各摘录头部的 SHA 与 replay-manifest 一致。以下只涉及 CPU 事件与通知，不涉及 GPU 完成时刻：
- **Issued 与 Preprocessed：** Issued（orchestrator:207）在异步生成器开始执行时记录。Preprocessed（222）在分词、input_processor 和建请求之后、送入 E 之前记录。
- **Begin 与 End 事件：** EncodingBegin、ContextBegin 在派发远程 step 之前逐请求记录；EncodingEnd、ContextEnd 在处理已完成批次时记录。
- **P 首 token 与 bridge：** engine_context:334–342 先记 ContextEnd，再回调首 token；之后才为未结束的请求建 MigratingRequest，推入 bridge 队列。
- **embedding 与 KV 迁移：** embedding（context:380–394）和 KV（decoding:259–272）都是 await 远程迁移调用这一段的 CPU 观测跨度。
- **DecodingBegin：** decoding:303–308 每次派发解码批次都以 True 调用 DecodingBegin，叠加 Enum 查询与字符串存键不一致的问题，结果是逐步覆盖。
- **API 返回的 timestamps：** api_server:140–145 在 await is_disconnected 之后才取 perf_counter，这些值就是返回的 timestamps。

NON-BLOCKING：
- DecodingEnd 的记录位置没有摘录，reported_decode 只能作描述，不作解释。
- 208–221 之间没有 await，预处理会同步占住事件循环。如果各引擎协程也跑在这个循环上，可能推迟其他请求的通知和调度。这只能作为 profiling 候选。
- 补丁后的 llm_async 层没有摘录。"API 时间戳不早于 callback"这一点不受影响；是否逐 token 一一对应，可由 EPD 的 later_zero_gaps 数据佐证。

本次不评价尚未运行的数据，不授权任何 GPU 实验。
