> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/epd-followup/reviews/prompts/g2-g3-followup-fix.md) SHA256 c9fc15f033e56d3b57cd61b0e0cc7f5864d02cd0286f1ef1a121f757ac154f88。原数字及解释不变。

续审，只读限制不变。请最多4次只读调用、输出800汉字内，15分钟上限；不要重读既有大日志或完整源目录。

1. Read outputs/epd-followup/reviews/g2-fix.diff：B1已固定969条，验证原ZIP固定SHA后，用zipfile比较其中SHA256SUMS与本地清单原始bytes。额外采纳N1–9的低成本建议：-O阻止、后续间隔max/零计数独立、带符号API时间差、kv字段改名与单向局限、布尔n/n_true/fraction、显式无效TTFT分段数、空输出目录与双向祖先守卫、UTF8、精确host/role/负载集合与CSV host。无原始数据变化，完整分析仍未跑。
2. Read outputs/epd-followup/tests/test_analysis.py新增回归：造969小文件，测试固定ZIP清单可通过；修改目录数据并重生成目录清单时必须被ZIP绑定拒绝。仅测试内部mock期望ZIP哈希，生产常量/CLI仍固定，没有开放任意来源参数。另测试-O guard、输出祖先guard、布尔统计和带符号距离。9个CPU测试均通过(cpu-checks.txt)。测试fixture首轮因Windows换行与ZIP字符串写入不同失败，改为ZIP存源文件bytes后通过，失败日志另存不隐瞒。不做通用合成全run框架，完整4800行将以旧摘要对账作锚点。
3. Read outputs/epd-followup/source-event-excerpts.md：从hash登记的真实源码机械提取，带完整源路径、SHA与原行号，覆盖此前未读的全部事件位置。请独立核实实际代码而非仅采信source-notes；如有必要，第4次只读调用用原文件一个范围交叉核对，避免宽Grep造成截断。

G3待补：Issued/Preprocessed时点、EncodingBegin/End、ContextBegin/End和P首token回调/bridge、embedding/KV调用事件、每步DecodingBegin，以及API await断连之后真实返回timestamps；dict初始化在orchestrator129摘录。此前Enum覆盖/基线通知等已批准无需重审。source/replay-manifest已补bundle/patch相对路径和AST比较方法。G3此处只讲CPU事件/通知，无GPU完成或因果承诺。

问题回答：Python3.12.14；benchmark客户端与服务同host perf_counter；warmup await gather结束后才正式，每重复gather屏障后下一重复；原qjh003 role不带host、005带后缀，现显式host并校验精确集合。

请分别给G2复审结论（B1能否关闭、剩余BLOCKING数）与G3新增范围结论。若新代码nits有阻塞明确最小处理；当前不评未跑数据/不授权GPU。
