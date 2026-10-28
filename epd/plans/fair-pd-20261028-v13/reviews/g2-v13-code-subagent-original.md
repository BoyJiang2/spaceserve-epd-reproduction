# G2 独立代码审查：EPD/PD 候选 v13（qjh000 2026-10-28 仅 CPU 单元）

审查方式：独立只读 subagent，将登记为 scope.json 中的 G2 reviewer。
- 未创建、修改或删除任何文件；未运行测试、项目代码、SSH 或网络命令；未读取凭据。
- 本地 Python 主要用于只读计算 SHA256 和规范 JSON 摘要。此外做了两件事：用 `ast.literal_eval` 只按字面量解析 runner 的 POLICY 字典；统计各文件换行符。两者都没有导入或执行项目代码。
- 以下行为结论全部来自静态阅读和推演，没有实际执行验证。
- 审查期间 plan 目录有变动：新增 README.md、cpu-receipt-v13-unexecuted.json 和 g5 提示词，plan md 在 11:40 更新。这些都不在 54 项 manifest 内。审查结束时我复核了 scope.json 和全部 54 项 SHA，均未变化。

## 结论：APPROVE_WITH_NITS

### 核查结果摘要

**1. 完整性：通过**
- `source-manifest-v13.json` 的实际 SHA256 为 4065e53e0697d7e0478a5900e34416050124772ac9df5d48a50863d8fc453a4d。manifest 54 个条目与目录中 54 个文件逐一一致，无多余、缺失或重复路径。
- 版本链：
  - v11：checkout 与 work 两份都等于 48b84baa…（51/51）。
  - v12：等于 1249cc45…（54/54）。
  - v13-a：等于 753cdfac…（54/54），与 v13 manifest 中记录的 prior 值一致。
  - work/v13 与 checkout 中的 v13 逐字节相同。
- v13-a → v13：字节级只有 cpu_target_runner.py 不同。差异只有 POLICY（第 24–28 行）和第 77 行的报错文本，共 6 行，与 plan 目录中的 patch 和 make_v13.py 的结果一致。
- POLICY 的 13 个键与 scope.json["policy"] 完全相等。scope.json 顶层的 uid、boot_id、source_root、booking_id 也一致。时间戳换算后是 2026-10-28 09:00 和 19:00（+08:00）。
- plan 目录中的三份 patch 和两份 feasibility 说明，与 outputs/pd-baseline-proposal 下的副本 SHA 相同；patch 涉及的文件清单与目录实际差异一致。
- 换行符：20 个文件是 CRLF。仓库 `.gitattributes` 为 `* -text`，本地 core.autocrlf=false，提交时字节原样保存，服务器上逐 SHA 核对不受影响（v11 情况相同）。launch_server.sh 是 LF。
- 摘要复算：
  - digest(scope) = bca7fd453c2d96c30363ec0e9ef8d731297208102a9c8e9b9d9199c8c81f4309。
  - G2 scope = digest({"scope_sha256": bca7…, "source_manifest_sha256": 4065…}) = 9d3b08f17d62ce6456747b6c629b046150107bda0bf3863e9a6eb9eaa1e16f63，与预期一致。
  - user-original-instruction.txt 的 SHA 与 grant 记录一致。

**2. B1（预约校验）：已修复**
- 校验逻辑，preflight_controller.py:45-52 `booking_for_unit`：
  - 通过 SHA 绑定读取原始预约文件。
  - observed_ms 必须是整数，且不得晚于当前时间。这比 booking_remaining 允许的 +2 秒更严格。
  - 调用 preflight_guard.py:74-100 的 booking_remaining，核对：新鲜度不超过 300 秒；read_only 与 origin；资源处于 active；已批准票据的 resource、node、user、kind=gpu、start、end；时间连续覆盖；授权窗口；并扣除不少于 120 秒的 cleanup_seconds。
  - 最后要求 wall_seconds ≤ 剩余时间。
- 调用顺序（run，:168-211）依次为：
  1. authorize（:169）。CPU 授权的 scope 不是 EPD_preflight_only，会在 :35-38 被拒。
  2. load_execution / validate_spec（:170）。
  3. 锁和 active 状态检查。
  4. booking_for_unit（:185）。
  5. 构造 NvmlBackend（:186）。
  6. snapshot（:188）。
  7. 再次 booking_for_unit（:191）。
  8. 构造 Claim（:192），内部再查一次 booking_remaining。
  9. reserve（:204），又查一次。

  构造 NVML 和 Claim 之前都已做预约校验。
- 新测试 test_controller_cpu.py:89-106：
  - 我逐项推演了 Fixture。now=1e8，`int(1e5*1000)` 是精确值；config 中的 uid 和 root 有效；runtime 目录已存在。
  - 如果用未改动的基线预约，第一次 booking_for_unit 会通过并调用 NvmlBackend。所以六种模式各自命中了目标分支：
    - expired、wrong_ticket、before_window：在覆盖或窗口检查处被拒。
    - wrong_owner：在身份检查处被拒。
    - future：在新增的严格时间检查处被拒。
    - short：剩余 180 秒，小于 300 秒，被拒。
  - 目前这条测试不是空转，但比较脆弱（见 NON-BLOCKING 2）。

**3. B2（请求事件持久化与取消传播）：已修复**
- fixed_unit.py 的改动：
  - :109-113 新增只追加的 request-events.jsonl。
  - :140-141 在 POST（:144）之前写入并 flush `submitted` 事件，包含完整请求体。
  - :145-148 在 read() 返回后、做状态码/JSON/token 校验之前写入 `http_body`，包含状态码、接收时钟和 base64 编码的原始字节。
  - :162-168 写入 complete、failed 或 cancelled 事件；:169 写入终态行。
  - :170-173 请求失败时创建 STOP 文件，被取消时重新抛出 CancelledError。
  - :198-211 run_client 只在本次调用期间把 TERM/INT 映射为 task.cancel，并在 finally 中恢复原处理器。
- 取消能否传到最外层：外层取消会穿过 `gather(return_exceptions=True)`，因为按 CPython 3.10 的 _GatheringFuture 语义，只要有子任务被真正取消，外层就会抛出 CancelledError。
- 效果：
  - 客户端子进程收到 TERM 后以非零码退出，已 flush 的 submitted 记录保留。
  - 遭 SIGKILL 时，只会留下诚实的"未完成"记录。
- 公平性：三组使用同一条客户端路径，每个请求的额外开销相同，不引入不公平优势。
- 新测试 :173-210 有两条：一条本地取消；一条在真实子进程等待假 HTTP 时发送 SIGTERM。两条都断言请求 0 依次为 submitted→http_body→complete，请求 1 为 submitted→cancelled，并检查 base64 响应体和 requests.jsonl 中的终态。如果删掉信号处理器，进程会被默认 SIGTERM 直接杀死，journal 断言会失败，因此测试确实覆盖了修复点。

**4. 本次 CPU 单元的安全性：通过**
- runner child 的限制与已执行的 v11 完全相同。v11→v13 只改了 POLICY、报错文本，以及在 :226 加入第五个测试模块名。限制包括：
  - Python 以 -I -S -B 启动。
  - :174 的 NoGPU 导入钩子。
  - :175-196 的 Popen 包装：只允许 git 和本 Python 解释器；cwd 必须在 root 内；拦截 push/pull/fetch/clone/ls-remote；记录 helper 身份。
  - :197 禁用 os.system。
  - :199-206 对 AF_INET/INET6 禁止 connect/connect_ex/bind/listen/sendto/sendmsg。
  - CUDA_VISIBLE_DEVICES 为空，NVIDIA_VISIBLE_DEVICES=void。
  - 绑定 CPU50、nice10、RLIMIT_AS 1GiB、RLIMIT_CPU 300 秒。
  - 只写一次 claim；运行前后重新计算源码哈希。
- 新测试模块：
  - 没有真实 socket：aiohttp 被替换成 sys.modules 里的假对象，测试中的 URL 从不会被连接。
  - 不导入任何 GPU 包。
  - 所有临时文件都在 EPD_CPU_TEST_TMP 下。
  - NVML、Claim、Popen、kill、time 在需要的地方都已 mock。
  - controller.run 在 booking_for_unit 处就停下。
  - reserve 只写 fixture 的临时目录。
- 唯一的孙进程：
  - 命令是 `sys.executable -I -S -B -c …`，包装器允许它，会记入 helper-pids，清理阶段会核对它已退出。
  - 它不受 child 进程内补丁的约束，但 -S 去掉了 site-packages；假 aiohttp 保证不联网；它还继承了空的 CUDA 可见性、rlimit、CPU affinity 和 nice 值。风险可以接受。
- 五个测试模块：
  - 只导入标准库和项目内模块。顶层 import aiohttp 的 benchmark.py 没有被任何测试导入。
  - 没有任何 skip。预期 35+19+13+9+11=87 个测试，skipped=0。
  - 我逐一推演了新增的 11 个测试，没有发现会确定性失败的用例。
  - 也不依赖目标机的额外外部状态。
- v12 改动对既有测试的影响都已同步处理：test_preflight_v5 的 Fixture 补上了三个必需文件；test_production_identity 补上了环境变量。没有既有测试调用新签名的 reserve。

**5. 未实现阶段的 fail-closed：通过**
- fixed_unit.py:47-49 对 qualification 和 calibration 以外的阶段（numeric、selected_g3、cleanup_reserve）抛出 NotImplementedError；未知单元会更早在 unit_budget 里抛出 ValueError。
- 两者都发生在 load_execution（:67，由 run 在 :170 调用）中，早于加锁、预约检查、NVML、Claim 和任何进程启动。
- 另外，main 要读取 preflight-static.json，但仓库里只有 candidate 状态的 .candidate.json；也还没有被 manifest 钉住的 unit 模板。因此 controller 目前无法发起任何 GPU 操作。

**6. 凭据和敏感信息：通过**
- 54 个源码文件和 plan 文件中没有发现凭据、token 或私钥。
- 代码中只出现回环地址，仓库 URL 本来就是公开的。
- plan md 当前版本已不含第三方用户名。
- v11 先例中公开的 booking.json 只包含本人的票，建议本次结果沿用这种过滤。

## BLOCKING
无。

## NON-BLOCKING
1. **controller 清理循环可能提前中止（preflight_controller.py:121 与 :315-328，只在 GPU 路径，本 CPU 单元不执行）。**
   - 问题：`stop_owned` 里的 os.kill 没有捕获 ProcessLookupError，进程在身份核对和发信号之间退出就会抛错，Ray 级联退出时这种竞态并不少见。而整个清理循环（descendants、backend.read、sidecar 读取、stop_owned）只包在一个 try 里，任何一处异常都会让后面所有自有进程（包括较早启动的 API/GPU 服务）都不再被停止。
   - 后果：虽然会记为 release_unconfirmed 并阻止下一单元，但 GPU 进程可能遗留在共享卡上。
   - 建议：每个 PID 单独 try/except；把 ProcessLookupError 视为已退出；无论如何都尝试停止非 GPU 的自有进程。在任何 GPU 使用这个 controller 之前必须修复，并另走 G2。
2. **B1 测试较脆弱（test_controller_cpu.py:89-106）。**
   - 问题：
     - 没有正向对照（有效预约时 NvmlBackend 应被调用）。
     - 只断言泛化的 ValueError。
     - 只覆盖了 :185 的第一次检查，没覆盖 :191（snapshot 之后、Claim 之前）的第二次检查。
   - 建议：
     - 用 assertRaisesRegex 匹配具体报错。
     - 加一条正向对照：mock 让 NVML 抛出哨兵异常。
     - 加一个"第一次检查通过、第二次失效"的用例，断言 Claim 未被构造。
3. **B2 测试的挂起风险和覆盖缺口（test_controller_cpu.py:168-169 与 :173-210）。**
   - 挂起：cancel_locally 分支里的 `await waiting.wait()` 没有超时。如果将来出现回归、请求 1 走不到 POST，测试会一直等到 runner 的 300 秒上限，把这一次性单元耗掉。这种情况会 fail-closed，不会产生假 PASS。建议改成 `asyncio.wait_for(..., 10)`。
   - 未直接断言"POST 前 submitted 已落盘"：可以在出现 waiting-HTTP 后、发 SIGTERM 之前读一次 events 文件。
   - 未覆盖：非 200 / failed 路径、取消时生成 STOP 文件、SIGINT。
   - :173 的显式重抛没有被单独验证：即使去掉它，gather 本身也会传播取消，测试仍会通过。
4. **两条 v12 测试近乎恒真。**
   - :69-72：配置因缺少键在 preflight_guard.py:53-54 就被拒了，根本没走到 candidate 状态检查；而 authorize 本来就不会调用 NVML 或 Popen，所以那几条"未被调用"的断言恒为真。
   - :80-85：传入 `config={}`，preflight_controller.py:87 先抛出 KeyError('uid')，mock 的 proc.identity 根本没被调用。
   - 两条的安全结论在别处另有支撑，不算误导，但建议修正：前者用完整键集加 assertRaisesRegex("no GPU authorization")，后者提供 uid 和 root。
5. **runner 沙箱的既有缺口（cpu_target_runner.py:177-206，v11 起未变）。**
   - 问题：
     - 本 Python 的 helper 没有被强制带 -I/-S；不带 -S 的 helper 可以绕过 NoGPU 导入 pynvml。
     - 网络 git 用的是黑名单，漏掉了 `remote update`、`submodule update`、`archive --remote`、fetch-pack 等。
     - DNS（getaddrinfo）、fork、posix_spawn 没有拦截。
   - 影响：当前测试只用 `git --version` 和 -I -S -B 的 helper，对本单元没有影响。
   - 建议：后续版本改成白名单。
6. **全局 340 分钟检查跨重启无效（preflight_controller.py:199-203）。** 它用 perf_counter 与账本里的 start_monotonic 比较，机器重启后没有意义。按分配额度计的阶段预算（account）仍然有效。建议同时记录 UTC 时间和 boot_id，boot 变化时直接拒绝。
7. **严格时间检查可能误拒（preflight_controller.py:47）。** 只要 observed_ms 晚于当前时间就拒绝。如果预约回执在本地 Windows 时钟下生成后再上传，微小的时钟偏差就会导致误拒（属 fail-closed）。建议规定回执必须用目标机时钟生成，或允许与 booking_remaining 一致的有界偏差。
8. **fixed_unit.py:121-129 的提交前拒绝不留痕。** 因 RGB 不符或 stop/deadline/N+1 而在提交前被拒的请求，不会写事件，也不会创建 STOP 文件，同批其他请求会继续提交。由于 controller 事先已校验 RGB，影响很小。
9. **文档滞后。** 源码目录继承的 FOLLOWUP.md:127-131（仍写 "v6 … cpu_target_runner.py … qjh001 … has not run"）、PREFLIGHT.md 以及 test_controller_cpu.py:1 的 docstring 都已过时。不影响功能，plan README 也已声明这些只作上游参考。
10. **流程缺口。** v12 G2 的原文没有保存，不符合 AGENTS.md §3.2.1 和 §3.4 的要求。建议在 reviews/ 中记录：原文缺失、转述的来源，以及本次 G2 已覆盖 v11→v13 全部增量并取代 v12 G2。

## QUESTIONS
1. v12 G2 原文中，除 B1、B2 外是否还有 NON-BLOCKING 项或附加条件需要跟踪？我无法核实实现者的转述是否完整，只能基于整段增量独立判断。
2. 结果审查是否以下列数值为预期：tests_run=87、failures=0、errors=0、skipped=0，且 test-events 中出现全部 11 个新 test_id？数目不符应视为异常。
3. 关于 G2 JSON 包装：是否会使用 reviewer_id "claude-code/subagent-G2-v13-code-20261028" 和 scope_sha256 9d3b08f1…，并以本文全文作为 original_review_text、不改写结论？另外 README 链接的 G1-original.json 和 G2-original.json 目前还不存在，需要在 G5 之前补齐。
4. 将来 GPU 预约回执由哪台机器的时钟生成？这关系到 NON-BLOCKING 第 7 条。

**不确定之处：**
- 我没有运行任何测试或代码。"测试会通过、不是空转"是按 Python 3.10 语义（包括 asyncio gather 的取消语义）做的静态推断，我比较有把握，但没有经过执行验证。
- 静态检查未发现 3.11 以上才有的语法。
- 目标机上 /proc children 等内核特性只影响 GPU 路径，我没有核实。

GATE_RESULT: {"gate": "G2", "scope_sha256": "9d3b08f17d62ce6456747b6c629b046150107bda0bf3863e9a6eb9eaa1e16f63", "source_manifest_sha256": "4065e53e0697d7e0478a5900e34416050124772ac9df5d48a50863d8fc453a4d", "decision": "APPROVE_WITH_NITS", "blocking": 0}
