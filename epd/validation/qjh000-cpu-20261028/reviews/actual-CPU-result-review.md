# 独立 CPU 结果审查原文（G3-CPU）

- 实际审查者：完成 v13 G2 代码审查的同一新上下文 Claude Code subagent（general-purpose，只读），与主执行者同一模型族、独立上下文，未参与实现或执行。请求依据模板 work/claude-continuation-20261028/cpu-result-review-prompt-template.md 并附实际值（主执行者经 SendMessage 发送）。
- 结果：APPROVE_WITH_NITS，BLOCKING 0，run_id cpu50-1793171216920480650。处理记录见文末。

---

# G3-CPU 独立结果审查：qjh000 2026-10-28 EPD/PD v13 唯一 CPU 单元

（前一份 G2 代码审查已交付；本文是追加的 G3-CPU 结果审查。）

**审查方式（只读）**
- 未修改或创建任何文件，未运行测试或项目代码，未 SSH、未联网、未碰 GPU，未读取凭据（booking/ 下的 login*.out 未打开）。
- 本地 Python 只用来读取 JSON/tar、计算 SHA256 和规范 JSON 摘要。
- 用只读 git（rev-parse/log/ls-tree）比对 commit f1ff073 中的 blob。
- 原始预约快照只用来核对 SHA 和本人票字段，下文不含他人信息。

## 结论：APPROVE_WITH_NITS

结果可信，0 BLOCKING：87 项全部通过，回执、claim、permit 绑定、新鲜度、清理和执行代码版本都逐项核实无误。待改进的是证据来源记录和文档措辞，不影响结果。

### 核查结果

**1. 回执与 claim：通过**
- runtime 下只有一个 CPU-unit-claim.json（SHA 6f98d6d6…），run_id 为 cpu50-1793171216920480650。
  - run_id 与 claim_utc_ms 1793171216920（北京时间 15:06:56.920）一致。
  - max_attempts 1，auto_retries 0。
  - 截止时间为 start+300 s，清理截止为 start+330 s。
- CPU-receipt.json 的 SHA（c39f2ab4…172f）与 runner-stdout.txt 打印的值一致，stdout 中 exit_code 为 0。runner-stderr 为空；ssh-run.json 记录 RUNNER_EXIT=0、ssh exit 0。
- 回执主要字段：
  - exit_code 0，child_exit_code 0，terminal_state completed，failure null，terminal_errors 为空。
  - cleanup_confirmed true，父、子进程 nice 均为 10，startup_signal_deferred null。
  - duration 3.727 s；日志为 "Ran 87 tests in 3.555s"。
- 回执与 claim 中的 command、parent_identity、commit f1ff073…、permit_sha256 8cd4357e… 完全一致；回执记录的 claim SHA 等于下载到的 claim 文件。
- source_before 和 source_after 都是 54 项，均与 manifest 4065e53e… 完全相同。
- 回执 files 中列出的 4 个文件，SHA 都与下载文件一致：helper-pids、test-events、test-result、raw-test.log。
- result-download.tar 共 30 个文件、14 个目录：
  - 没有链接或特殊文件，没有绝对路径或 .. 路径，属主均为 uid 2147。
  - 每个成员都与 result-original 逐字节相同，两边都没有多余文件。
- inputs/ 下 7 个上传件与服务器副本逐字节相同。

**2. 测试事件与日志：通过**
- test-result：tests_run 87，failures 0，errors 0，skipped 0，successful true。
- test-events.jsonl 共 174 行：87 个 start 与 87 个 success 严格交替，没有 skip，也没有 subtest_failure。
- 各模块数量为 35/19/13/9/11，与 G2 的预期一致；test_controller_cpu 的 11 个新 test_id 全部出现。
- 实际执行的 87 个测试 ID，与 v13 五个测试模块里按类、按方法列出的测试方法集合完全相等。
- raw-test.log 中 87 项全部为 ok，没有 Traceback、Warning 或 Error。ParentExitPOSIX 的 5 项在 "..." 和 "ok" 之间夹着嵌套 runner 打印的回执 JSON，这是预期的输出。

**3. permit 绑定：通过**
- 范围与审批：
  - digest(permit.scope) = bca7fd45…，permit 中的 scope 与 commit 中的 scope.json 相同；G2 范围摘要为 9d3b08f1…。
  - G1-original.json（1fb58153…）：G1，APPROVE_WITH_NITS，0 BLOCKING。
  - G2-original.json（9abac4e1…）：G2，APPROVE_WITH_NITS，0 BLOCKING。全文与 reviews/g2-v13-code-subagent-original.md 相同，结论与 GATE_RESULT 行与我交付的 G2 一致。
  - 两份审查的 reviewer_id 都在 reviewer_ids 内，且都不等于 executor_id。
  - user-CPU-grant.json（e415e3ad…）绑定了 bca7… 和原始指令（d4aeaf18…）；manifest 为 4065e53e…。
- commit 证明链：pushed-commit（ce924e58…）→ github-main-receipt（8eda39d8…）→ github-main-ref（9e3a5150…）。三者的 object.sha 都是 f1ff073…，类型为 commit，仓库 URL 一致。
- 部署记录 deployment.json（2d87cf58…）：
  - commit 与 HEAD 均为 f1ff073，tracked_clean。
  - 没有不匹配或未登记的文件，54 项 SHA 与 manifest 一致。
  - affinity [50]，nice 10，Python 3.10.12（/usr/bin/python3）。
  - 部署输出 DEPLOY_OK，ssh exit 0。
- 本地 checkout：
  - HEAD 为 f1ff073（tree 5d2fe997…）。
  - 该 commit 中 v13 的 54 个源码文件、permit 引用的计划文件和 orchestration 副本，都与工作区逐字节一致。唯一例外是 15:10 之后本地改过的 plans 目录 README.md，它不在 permit 绑定范围内。
  - 实际执行的三个脚本与 commit 中的副本逐字节相同：deploy（0a20e946…）、probe（25a4e0ac…）、run_cpu_unit（c518a09f…）。
- 新鲜度：
  - 预约观测时间 15:06:44.431，在 claim 前 12.5 s；host probe 观测时间 15:06:55.068，在 claim 前 1.9 s。两者都远小于 300 s。
  - 服务器时钟比本地快约 0.16 s（往返 2.1 s），不影响判断。
- 预约快照：
  - 原始快照 SHA 646c3a2a… 等于规范化 booking 中记录的 raw_snapshot_sha256。
  - 快照中本人票只有一条，去掉 purpose 字段后与规范化记录完全一致：cpu，h20/qjh000，1793149200000–1793185200000，本人。
  - 资源处于 active，且允许 CPU 预约；claim 时刻该资源上没有他人 CPU 票与本时段重叠。
- host probe：qjh000，uid 2147，boot c57aee5b…，没有冲突 PID，也没有正在运行的单元，affinity [50]。探测脚本只读 /proc，不查询 GPU。

**4. GPU/网络、进程与清理：通过**
- helper-pids 记录了 7 个 helper，都是 `/usr/bin/python3 -I -S -B -c …`，工作目录都在 root 内：
  - 1 个 getpid helper；
  - 5 个 ParentExitPOSIX harness；
  - 1 个 TERM journal 孙进程。
- `git --version` 因为瞬间退出没有被记录，这符合设计。
- 顶层清理共 8 项：子进程 already_exited（exit 0），7 个 helper 均为 gone，signals 全部为空。
- release-check（SHA 289ab8db…，claim 后约 58 s）显示：父进程、子进程和 7 个 helper 共 9 个身份都已 absent；root 内没有自有进程；HEAD 仍为 f1ff073，tracked clean。
- 日志中没有网络被拦截或 GPU 包被拦截时会出现的报错。回执里的 GPU_or_model_requests 0 和 GPU_imports_allowed false 是固定字段。"没有使用 GPU" 的依据是沙箱配置（CUDA 可见性为空、-S、NoGPU 钩子）加上刻意不查询 GPU，不是 GPU 侧的实测。这符合 CPU 范围。
- 另外 5 个 cpu50-* 目录：你判断它们是测试套件生成的嵌套 mock 回执，经核实成立。来源是 test_cpu_target_runner.ParentExitPOSIX 的 harness 在 monkeypatch 掉 preflight 和 claim_unit 后调用了真实的 run()。依据如下：
  - mock 标记：commit 为 "a"×40；permit SHA 等于 sha256("{}") = 44136fa3…；claim 为 "CPU-MOCK-lifecycle-claim" 和 "c"×64；source_before 只有 1 项；也没有写 CPU-unit-claim.json。
  - 父 PID 正好是主 helper 列表中的 5 个 harness 进程。
  - 退出码 130/130/143/143/1，与 int_during_start、int、term、term_during_start、wait_error 五种模式对应；各回执 SHA 与 raw-test.log 中对应行一致。
  - 只向自有 fixture 进程（uid 2147，身份已核实）发送了 SIGTERM，这些进程都已 exited 或 gone。

  这些目录不能当作实际执行的证明。实际运行只能由 claim 里的 run_id 唯一确定。

**5. 结论边界：恰当**
- validation README 草稿和 local-result-integrity.json 都明确只证明目标 Python 上的 CPU 逻辑，不涉及 Ray/vLLM/CUDA、模型或性能。
- 待发布目录与本地证据逐字节相同，里面没有他人用户名或主机地址；原始快照不发布。

## BLOCKING
无。

## NON-BLOCKING
1. **release-check.json 缺少生成依据。** 生成它的脚本、命令和原始输出都没有保存，其中的 signals_sent 0、gpu_queried false 只是复核程序的自我声明。建议像其他三个编排脚本一样，保存实际命令或脚本，并附上 SHA。
2. **嵌套 fixture 回执写进了真实 runtime/，而不是 test-tmp。** 原因是 tests/test_cpu_target_runner.py 的 harness 把 preflight 的 root 设成了真实 SOURCE，v11 起就如此。现在能区分，README 也已注明；建议后续版本把 harness 的 root 指向 EPD_CPU_TEST_TMP。
3. **booking.json 的 observed_ms 取自本地时钟**（快照命令返回之后），原始响应里没有服务端时间戳，新鲜度依赖实测的时钟偏差。本次余量很大，不影响结论；建议在 README 中注明。
4. **README 措辞可以更精确：**
   - "未发信号" 只指释放复核本身。测试套件按设计向自有 fixture 进程发过 TERM/INT，建议写明。
   - "覆盖两项修复" 建议补一句：第二次预约检查、非 200/failed 路径等尚未覆盖（G2 非阻塞第 2、3 条）。
5. **发布前需补齐：** README 里还有 RESULT_REVIEW_PLACEHOLDER，链接的 reviews/ 目录尚不存在。属于 G5 事项。
6. **G2 非阻塞第 1 条（controller 清理循环）仍未修复。** 本次结果不改变"任何 GPU 使用前必须修复"这一要求。

## QUESTIONS
1. release-check.json 是用哪条命令或脚本生成的？能否把它连同原始 stdout 一起保存？
2. 发布时是否原样保留这 5 个嵌套目录，并在 README 里说明它们的 mock 标记？

**不确定之处：**
- 服务器 /proc 状态、tar 打包时的服务器内容、release-check 的内容，我只能依据下载的字节和编排输出判断，无法独立重现。
- "没有使用 GPU 或网络" 基于沙箱配置和测试结果，不是测量值。
- 以上所有 SHA 和一致性检查我都逐一复算过。

GATE_RESULT: {"gate": "G3-CPU", "run_id": "cpu50-1793171216920480650", "decision": "APPROVE_WITH_NITS", "blocking": 0}

---

## 主执行者处理记录

- NB1 / Q1：已保存复核脚本 [release-check-script.py](../orchestration-records/release-check-script.py) 与实际命令 [release-check-command.md](../orchestration-records/release-check-command.md)；release-check.json 即该命令原始 stdout。
- NB2：README 已说明嵌套回执的 mock 标记与来源；后续版本把 harness root 指向 EPD_CPU_TEST_TMP，列入下一版本。
- NB3：README 已注明预约观测时间取本地时钟及实测偏差。
- NB4：README 已改写“未发信号”的范围（只指释放复核；测试套件按设计向自有 fixture 进程发过 TERM/INT），并注明第二次预约检查、非 200/failed 路径尚未覆盖。
- NB5：README 占位符已替换，本目录 reviews/ 已建立。
- NB6：GPU 硬前置维持不变，README 与 v13 计划页均已写明。
- Q2：5 个嵌套目录原样保留并在 README 说明。
