> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/reproduction/reviews/prompts/g3-h20-mechanism-focused.md) SHA256 ba984953a1d8c3fcf067abff20639321e19634afe56d23c0e185e4f95c637e39。原数字及解释不变。

你是独立只读审查者，仅Read/Grep/Glob，不改文件、不运行实验/命令/SSH/GPU、不访问凭据。项目根 D:\Documents\codex\2026-10-23\new-chat-2，先读 D:\Documents\codex\AGENTS.md。

仅G3机制证据，不审性能结论。读 outputs/reproduction/report/h20-acceptance.json、scripts/audit_h20.py、probe_epd_kv_ipc.py、probe_epd_embedding_ipc.py、probe_h20_blas.py。每台evidence/<host>/中按需抽查：native-source-manifest.json、kv-actual-cache.json、embedding-ipc.json、blas-after.jsonl、baseline-runtime.json、epd-runtime.json、correctness-checkpoint.json及epd-epoch1/2-c8.json；preflight-*中的平台与两方向KV/P2P样例。不要读取整段epoch日志，只检索Num GPU Blocks等相关行。

实际技术检查：每台6方向16MiB源目标SHA相同，原始KV两形状2048/24728×六方向×3，实际服务N60553 P→D×3；每台总39拷贝。embedding四图E→P×3；BLAS4shape；每台45固定服务用例，覆盖两轮重启和C8，输入输出IDs对基线。旧cuBLAS12.1.3.1 SIGFPE独立复现，仅改12.4.5.8，元数据声明差异已披露，同机两组相同加载库。原始native源码未改，Python最小兼容补丁另存。

最多18次只读调用，若有证据缺口列明确文件/字段，不扩大读取所有日志。输出G3 APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING（文件:行、理由、最小处理）、NON-BLOCKING、QUESTIONS。API成功不代表数据正确，固定用例不代表所有正式语义质量。本次不替代G1/G2/G4/G5。
