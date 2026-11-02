# G4 — Nov2 SpaceServe 313预检可读报告

APPROVE_WITH_NITS / BLOCKING 0。仅批准当前可读报告/结构化对照/逐请求提取的数据与结论口径；不是未来Release、发布G5或完整54性能验收。

独立reviewer `/root/space_source_consolidation_review`，Codex subagent非Claude，依AGENTS§3.2.1接替。只读报告/数据/已核G3及本地archive；使用只读解析比对提取记录，未运行项目tests、SSH/API/GPU、读取凭据或改源，仅写本G4 MD/JSON。

准确报告spaceserve/comparison/20261102-preflight.md RAW SHA256 `7525db668cf3d1be2025738bdfc555a5aa96e8fa5505961842b6f21794f28d5b`。实际model G3 MD SHA3fca1a26ebae7471736b005c9e30e4e2d123b8ab99c551b528c6ba25ffdc71f8与JSON批准/B0一致，原as-of observer未知字段未改；报告最新终态另引用真实cleanup原件，未倒填旧G3。

## 数据与文字核对

逐请求JSONL实际313行/3021784B，reference7/correctness90/diagnostic216。reviewer直接流式读取本地原tar.gz的13个来源文件，逐个源SHA与JSONL.source_sha256核同，313个record均与真实来源原JSON/JSONL记录完全一致，0缺失/差异。97正确性/reference原HTTP status均200；216诊断success全true，120warm+96profiled，visual_tokens全1024/output_tokens全128。没有用summary自己验证summary，也未跑新推理。

six trial/role分组各15correctness+36diagnostic（20warm/16profiled）与结构化summary一致，90输出/processed IDs对齐reference、C4/C8实际峰4/8、worker/FP16/同卡与四条真实trace overlap值、SM78→78与78→54由已独立实际G3支持，报告只据其作机制可运行结论。本reviewer未重新解析全部大型trace，将已批G3作为该机制证据来源，不伪称新硬件测量。

报告明确formal0/54、无性能加速比/CI或完整矩阵结论、固定顺序profiler小样本不替代正式吞吐/TTFT/TPOT/E2E/显存波动，decoder互斥未证明、LM保留visual参数不当容量收益、min_pixels/max_pixels警告不叫override生效，NCCL/semaphore退出警告原样保留。旧48/54与旧预检独立、不跨窗拼数据、不再本窗启54的口径准确。

archive元数据351867489B/SHA57204d3bb27babf73672fbd4999b2db4b41b9a2c4f36eecbf24e46fe9a8d8a0c、550成员/409946044解压B/allSHA与G3相符；本次核13来源提取，不冒称重新全550验收。Release尚待发布明确，不叫远端下载通过，未来发布/下载另G5。

真实release-check记录远端phaseexit0/387原PID观测absent/GPU UUIDc005 0MiB0util空apps，与报告区分本地observer失败。最新cleanup C文件与原S/space-1700-model-observer-local-cleanup.json RAW SHA同为fe2aaf6f9db2acf0d13d5c7e9b952ec46b0ba2a8ebbc0db2a42ba93bcd353914：原PID40692、creation_filetime134380949120252927、OpenSSH实际路径、before259、精确handle TerminateProcess后exit1/natural=false。另原remote-precheck真实4PID均absent；报告正确写为收口本地observer，不伪称自然退出/本地exit0，不倒推原连接异常根因，也不当远端实验被终止。

报告11个相对链接全部在当前候选worktree真实存在，无缺链；入口/配置/source注明准确执行commit和新run/预约Gate要求，不将历史许可复用。没有对其他旧报告/README或未来未知Release作验收。

## NON-BLOCKING N1

报告句“诊断请求带profiler、每组仅16条”略易与表中的每轮36条及总两轮混淆。建议改为“每轮每组含20条预热和16条profiler样本”，保持原表与数据不变。这是措辞澄清，不要求重跑或重算，不阻塞此G4；若采纳须在后续发布候选如实记录报告新SHA，不能仍标本审查的原报告SHA。

QUESTIONS：无。此G4不批准部署/GPU/正式54或总goal完成；Space完整54、EPD公平PD与两项目最新最终交付仍未完成。