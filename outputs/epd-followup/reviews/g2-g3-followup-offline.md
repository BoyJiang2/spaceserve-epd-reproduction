# G2 离线分析代码与 G3 事件语义：独立审查结论

审查者：Claude（claude-opus-5-5），只读。本次正好用了 9 次只读调用：Read 了 analyze.py、test_analysis.py、source-notes.md、replay-manifest.json、orchestrator.py:226–273 和 lifetime.py；Grep 了 epdserve 六个文件、两份不同的基线文件，并统计了 SHA256SUMS 的行数。没有运行测试或命令，没有访问网络、SSH 或 GPU，没有读取凭据或聊天历史。

**审查缺口：** epdserve 那次 Grep 的结果有 43.3KB，超过内联上限被转存，我只看到前 2KB。要读它得用第 10 次调用，超出预算，所以没读。因此 engine_decoding、engine_context 和 api_server 的相关行我没有独立核对。replay-manifest 里的 SHA 值在不能运行命令的条件下无法复算，只能按记录引用。"6 个 CPU 测试已通过"是按提交说明引用的；我只逐条核对了断言和测试数据的算术，两者一致。

---

## G2：离线分析代码

**结论：REQUEST_CHANGES，BLOCKING 1 个**

### BLOCKING

**B1 `outputs/epd-followup/scripts/analyze.py:86–102`：封存校验没有和"旧的 969 文件清单"绑定**
- **问题：** `freeze_snapshot` 只检查目录里现有的 SHA256SUMS 和现有文件是否互相一致。
  - 它不检查条目数是不是 969：`files_verified` 在第 100 行只记录，不判断。
  - 它也没有固定清单文件自身的 SHA，也没有和外层 ZIP 里的清单比对。第 97–99 行只校验了 ZIP 本身的哈希；这个哈希值和 AGENTS 里记录的 `3d12…be38` 一致。
- **后果：** 如果目录里的数据被改动，同时清单被重新生成，before==after 照样成立。收尾阶段本项目确实多次重新生成过完整性清单，所以这不是空想。这时输出里的 `frozen_before/after` 和 `archive_sha256` 会给人一种"已证明是封存数据"的错误印象。这不满足提交说明里"验证旧 969 文件 manifest"的要求。
- **已核对：** 当前 `outputs/reproduction/SHA256SUMS` 有 969 行 `<sha256>␠␠<name>` 格式的条目，所以加上下面的检查不会让正常运行失败。
- **最小处理：**
  1. 在第 96 行之后加 `assert len(entries) == 969`。
  2. 把 `digest(root/'SHA256SUMS')` 和封存时记录的清单 SHA 常量比对。这个值要从收尾完整性记录里取，不能用当前文件现算。另一种做法是用 zipfile 只读打开那个已固定哈希的 ZIP，确认里面的清单字节和目录里的清单一致。
- **复审范围：** 只看这个函数。

### 已核对、没有阻塞问题的部分
- **丢数：** 第 122–125 行检查每个配置 300 条、每次重复 100 条、index 覆盖 0..99；第 28 行检查成功且正好 128 个 token；第 166 行检查总数 4800。任何偏差都会直接报错，不会悄悄丢数据。
- **负值：** 第 32 行要求 gap ≥ 0；第 30 行的顺序检查保证 TTFT 和尾段非负；事件跨度只在顺序正确时计算（53–55）；TTFT 分段只在整条链单调时才输出（61–64），不正常的只留标志，不伪造数值。
- **分母：** TPOT 是 decode_window/127，与旧口径一致；后段均值除以 126；统计结果都带 `n`。
- **分位数方法：** 用线性插值（第 13–22 行）。测试里 `[0,10,20]` 的 p95=19 正确；第 150–154 行把 TTFT/E2E/TPOT 的 P50/P95 与旧摘要对账。
- **混用来源：** 第 118–119 行检查数据有效性和 source_kind（1 图/并发 1 用 cache-fix，其余用原矩阵）；第 134 行检查 EPD 必须有事件、基线必须没有；第 113 行总数 16。
- **首间隔：** 首间隔和后 126 个间隔分开统计；后者在 case 级、每次重复、按重叠数分组都有 P50/P95/P99/max（159、162、163）。
- **重叠代理：** 按端点重建窗口，用半开区间；合并通知（同一时间戳）在第 73–74 行放进 bin 0，第 139–141 行把它排除在均值之外。同一请求自身必然被计入，所以 `count>=1` 在数学上成立。
- **输出位置：** 第 107 行用 resolve 之后的路径确认输出不在旧 root 内；第 108 行不覆盖已有的 analysis.json。

### NON-BLOCKING
1. **assert 可被关掉：** 所有安全和对账检查都是 assert（例如 107–108、113、152–154、167–168）。用 `python -O` 或设置了 PYTHONOPTIMIZE 时它们全部失效，但仍会写出 `legacy_summary_reconciled: True`（164）。建议在 `run()` 开头加 `if not __debug__: raise SystemExit(...)`，B1 新加的检查也同样受益。
2. **首间隔没分干净：** 逐请求的 `max_gap_ms` 和 `zero_gaps`（第 37 行）都包含首间隔，和"首间隔分离"的设计不一致；case 级的 `later_gaps_ms` 是对的。建议改成只算 `gaps[1:]`，命名为 `later_gap_max_ms`、`later_zero_gaps`。
3. **距离丢了符号：** `decode_begin_distance_*`（67–68）用了 abs。要解释"覆盖"，需要知道它是否在最后一个 token 之前约一步，所以建议改成带符号的 `event − stamp`。
4. **把 API 观察时刻叫成了 token 时刻：** 涉及 `kv_begins_after_first_token`、`kv_ends_before_second_token`（65–66）和标签 `prefill_end_to_first_token`（177）。API 时间戳一定不早于 callback 时刻（见 G3 第 4 条），所以前者只有 True 有确定含义，后者只有 False 有确定含义。建议改名为 `*_api_*_stamp`，并在 JSON 里写明这种单向性。
5. **布尔字段的分位数没有意义：** 布尔字段进了 `stats()`（149、159），会算出 p50/p95。建议对布尔字段只输出 `n` 和 `n_true`（或比例）。
6. **分段分位数不能相加：** 建议在 analysis.json 里写明只有逐请求的分段、以及同一有效子集上的均值可以相加；同时显式给出每个配置的无效分段数。
7. **输出目录守卫不完整：** 只检查了 analysis.json（108），`per-request.csv`（170）仍可能被覆盖；也没有阻止 root 位于输出目录之内（比如 output 设成 `outputs/`，文件就会写到封存 ZIP 旁边）。建议要求输出目录不存在或为空，并加 `assert not root.is_relative_to(output)`。
8. **读文件没指定编码：** 第 111、121 行的 `read_text()` 没指定编码，在本机中文 Windows 上默认是 cp936。遇到非 ASCII 内容会报错，但不会悄悄改数值。建议和第 87 行一样写 `encoding='utf-8'`。
9. **配置选择只查了总数：** 建议再检查（主机, role, 图数, 并发）唯一，并且正好等于约定矩阵；如果 role 里没有主机名，在逐请求 CSV 里加一个显式的 host 列。
10. **测试没覆盖主流程：** 测试没有覆盖 `run()`、`freeze_snapshot()` 和 `hashlib.file_digest`（后者需要 Python ≥3.11）。ZIP 哈希写死在代码里，导致无法用合成数据做端到端测试。建议把期望哈希做成参数，补一条合成的 `run()` 测试，覆盖选择、对账和 CSV 列。
11. **可选改进：**
    - EPD 的重叠窗口从 `stamps[0]` 开始（129），这符合约定的"首末 token 输出窗口"，但会把还在 KV 迁移或 D 端排队的请求算进去。可以加一个从 `stamps[1]` 开始的敏感性变体。
    - 每条请求另存原始的 `(事件 − 提交时刻)` 偏移，包括分段无效的请求，便于事后审计。
    - 第 158 行重复调用 `measure()`，只是效率问题。

### QUESTIONS
1. 分析环境的 Python 是否 ≥3.11？
2. 压测客户端是否和服务在同一台机器上，`submission_perf_counter` 是否为 `time.perf_counter`？首轮的 TTFT 已经依赖这个前提，本批新增的"提交→issued"分段同样依赖，建议写进 scope。
3. 正式重复 0 开始前是否等所有预热请求结束，重复之间是否有屏障？如果没有，重叠代理在边缘会少计。
4. summary.json 里 H20 配置的 role 是否包含主机名？

---

## G3：事件语义（源码事实）

**结论：APPROVE_WITH_NITS，仅限下面"已核对"的范围；BLOCKING 0 个。未核对的部分不在本次批准内。**

### 已核对的事实
1. **事件类型定义：** `lifetime.py:40` 是普通 `Enum`，不是 str 混入或 StrEnum。成员（44–56）包含分析用到的 12 个名称和 finished。`__str__` 返回 value（58–59），序列化用的是 `str(event_type)`（76–83），所以响应里是小写字符串，和 analyze.py:47–59 一致。
2. **覆盖机制：** `orchestrator.py:255–257` 用 Enum 成员做 `in` 查询，第 266 行却用 `event_type.value` 字符串作键。普通 Enum 和字符串永远不相等，所以去重守卫永远不生效，同名事件后写覆盖前写。AST 测试（test_analysis.py:61–77）提取实际方法、只去掉注解，用普通 Enum 调用两次。它的 Enum 模型和实际代码一致，所以复现有效。
3. **补充：** 第 266 行是 dict 赋值，和 `dont_add_if_dup` 无关，因此所有事件类型都只保留最后一次写入。其他类型是否每个请求会出现多次，本次没有确认。
4. **API 时间戳晚于 callback：** `orchestrator.py:245` 在 callback 里给 `StepOutput.timestamp` 赋值，第 246 行放入每请求的 asyncio 队列，226–232 行的生成器 await 取出后再 yield。所以 API 侧的任何时间戳都不早于 callback 时刻，中间还隔着队列和事件循环的等待。"StepOutput.timestamp 不是响应里的时间戳"这一论断，在 orchestrator 这一侧成立。
5. **事件时刻的来源：** 事件时间戳在构造 `LifetimeEvent` 时取 `perf_counter`，见 `lifetime.py:67–69`。笔记写的是 :68，实际赋值在 :69，属笔误级。
6. **Finished 事件：** `orchestrator.py:236` 的 Finished 在最后一次 yield 之后才记录，晚于最后一个 API 时间戳。分析没有用它，这是对的。
7. **分片 ID 路径：** 第 261–263 行会写带后缀的键。按协议请求内编码并行是关闭的，这条路径不应出现；万一出现，analyze.py:59 会直接报错，不会静默。
8. **基线：** `qjh003-original.py:77–82` 和 `qjh003-cache-fixed.py:90–95` 都是在每次 vLLM 异步 yield 之后取一次 `perf_counter`，再按新增 token 数重复填充；中间没有 `is_disconnected` 等待；响应里没有 lifetime_events。这和笔记第 4、5 条一致。qjh005 的两份按 manifest 记录与 qjh003 的 SHA 相同，我没有复算。

### 未核对（预算内读不到，不构成否决）
- `engine_decoding.py:303–308`（DecodingBegin 是否每次迭代都记录）和 `:255–273`（KV 迁移跨度）
- `engine_context.py:335–343`（ContextEnd 是否先于首个 StepOutput）
- `api_server.py:140–144,158`（返回的时间戳是否在 `await is_disconnected` 之后取）
- issued、preprocessed、encoding*、encoding_migration* 这些事件在哪里记录

**最小处理：** 补一次不超过 4 次调用的窄范围只读核对，直接 Read 上述行段前后各 10 行左右，不要再用宽范围 Grep。

### 能否用于后续事件跨度解释
- **现在可以用：**
  - 所有 lifetime_events 都是该类型最后一次写入时的 CPU 侧 `perf_counter` 时刻。
  - `decoding_begin` 和 `reported_decode` 不是首次 D 调度的时间。
  - API 时间戳既不是 callback 时刻，也不是 GPU 完成时刻。
  - 基线合并通知造成的零间隔不代表零执行时间。
- **暂时不能用：**
  - TTFT 各分段的具体含义
  - 两个 kv_* 布尔量的解释
  - "每次迭代覆盖"里"每次迭代"这一部分（`decode_begin_distance_*` 的数据可以佐证，但对应的源码位置本次没看到）

### NON-BLOCKING
- `source-notes.md:5`：把"后写覆盖"推广到所有事件类型；行号 `lifetime.py:68` 改为 68–69；注明 Finished 不用于跨度计算，以及分片键在本协议下不适用。
- `source-notes.md:7`：写明"API 时间戳不早于 callback"这个单向不等式来自 orchestrator.py:245–246 和 226–232 的队列结构。
- `replay-manifest.json:3–6`：补上归档补丁和 bundle 的相对路径；第 135 行写明 AST 是用什么方法比较的。

### QUESTIONS
- `request_lifetime_events` 实际是怎么初始化的？这不影响覆盖结论，但测试里用的 `defaultdict(dict)` 应该注明依据的是哪一行源码。

---

本次审查不批准任何 GPU 实验，也不评价尚未运行的完整数据结论。
