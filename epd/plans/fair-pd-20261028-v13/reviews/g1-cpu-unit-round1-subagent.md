# G1 第 1 轮审查原文（qjh000 2026-10-28 CPU 单元计划）

- 实际审查者：新上下文 Claude Code subagent（general-purpose，只读），由主执行者 Claude Code 于 2026-10-28 派生；与主执行者属同一模型族，独立上下文，未参与实现。
- scope 中的审查者 ID：claude-code/subagent-G1-cpu-unit-20261028
- 提示词：g1-cpu-unit-prompt.md
- 结果：REQUEST_CHANGES，BLOCKING 1（计划写出第三方用户名）。处理记录见文末。

---

结论：REQUEST_CHANGES

只有 1 项 BLOCKING：计划里写出了第三方用户名，这些文件会进入公开仓库。修复只改计划文本，不影响 scope 摘要。授权、scope、POLICY、各项限制和 Git-first 次序我都逐项核对过，没有发现阻塞问题。B1 修复后，对同一 scope 做窄范围复核即可。

本审查绑定的文件 SHA256：
- plan.md：8985cba4f06ae1d574fc792b5d1f9c8d410eb67b41583bd541fc77f54b3d5b17
- scope.json：8440bdcf45a41457a758f6a83f4f138c691c1fbd9dabbfdd0c06fb4fc8d44b96
- user-original-instruction.txt：d4aeaf18…bea3ef
- user-CPU-grant.json：e415e3ad…a5a2d3
- cpu_target_runner.py：9e81f214…e1a5a0
- source-manifest-v13.json：4065e53e…453a4d
- 预约快照 snapshot-20261028-0959.json：138318c2…4445。只按本人票 id 和 h20/qjh000 过滤查看。

核对记录（全部只读，没有运行测试、SSH、访问网络或 GPU，也没有读取凭据）：
1. 我复算 digest(scope) 得到 bca7fd453c2d96c30363ec0e9ef8d731297208102a9c8e9b9d9199c8c81f4309，与 grant 中的 scope_sha256 一致。grant 里的 original_instruction_sha256 与指令文件的实际 SHA 一致；该文件 89 字节，是用户的两句原话。
2. runner 的 POLICY 用 AST 读取，没有导入执行。它与 scope.policy 的 13 个键逐项相等，类型都是 int/str。scope 顶层的 uid、boot_id、source_root、booking_id 与 POLICY 一致，booking_user=boyjiang。与 v11 的 scope 相比，只变了 source_root、booking_id、4 个时间戳和执行者/审查者 ID。
3. 快照中的 bk-20261028T0141-8936eb9c：
   - kind=cpu、node=qjh000、resource_id=h20/qjh000、user=boyjiang；
   - start 1793149200000 对应北京时间 09:00，end 1793185200000 对应北京时间 19:00；
   - 创建时间为北京时间 09:41:17；
   - h20/qjh000 资源 active=true、cpu_booking_enabled=true、180 核；
   - 该资源在这个时段只有另一张他人 GPU 票（10:00–19:00），没有其他 CPU 票，与计划所述一致。
4. runner 的行为与计划一致：
   - CPU50 affinity：父进程必须由 taskset 启动，子进程由 preexec 设定并复核；
   - nice10 父子都复核；
   - 子进程 RLIMIT_AS=1073741824、RLIMIT_CPU=300；
   - 主任务 300 秒，自 run() 起算；清理截止为 min(+30 秒, 开始+330 秒)；
   - 准入要求 now+330 秒 ≤ 19:00；
   - 预约观测与 host probe 都必须在 300 秒内；
   - claim 用独占创建写入 runtime/CPU-unit-claim.json，max_attempts=1，零重试。
   v11→v13 的 runner 只改了 POLICY、一条报错文本，并在测试列表中加入 test_controller_cpu。其余逻辑与昨天实际运行的 v11 相同。
5. manifest 的 SHA 是 4065e53e…；54 个文件与本地 v13 目录逐文件一致，没有多余文件。与 v13-a 目录相比只有 cpu_target_runner.py 变化。G2 摘要交叉复算为 9d3b08f1…6f63，与 G2 提示词一致。
6. executor_id「claude-code/main-20261028」与两个 reviewer_ids 互不相同，reviewer 也没有重复。
7. 授权：依据是用户两句原话、本人账号在 qjh000 的 CPU 票、PROJECT_GOAL 中"CPU 测试优先在有明确 CPU lane 的远程专属目录执行"，以及 v11 先例。我判断这足以授权这次仅 CPU、单核、只跑一次的测试单元。计划写明不授 GPU、模型请求、候选预算或正式矩阵；不碰他人进程，不用 root/sudo，不装包，不起 TCP/UDP 服务，不复用旧 root 或旧结果。计划本身没有越界（不确定点见 Q3）。
8. 编排脚本与计划次序一致（改进点见 N1、N6、N7）：
   - run_cpu_unit.py 按 commit 读取已提交的 G1/G2/scope/grant/manifest；
   - 部署脚本只稀疏检出 code 和 plans 目录，并逐 SHA 核对、拒绝多余文件、要求 tracked clean、拒绝已存在的 ROOT；
   - host probe 只读 /proc，不查询 GPU。
9. 公开内容：v13 的 plans 目录和源码中没有发现密码、token、私钥、PAT 或主机 IP。env.yml 里的点分数字是包版本号。本地 Windows 路径此前已出现在已提交文件中，不是新的暴露类型。

BLOCKING
- B1. qjh000-cpu-20261028-plan.md:6
  - 问题：括号里写出了同机 GPU 票持有人的用户名。G5 提示词把这个文件列为公开提交内容，提交后会永久公开一个与本项目无关的第三方身份，以及他当日 10:00–19:00 的 GPU 使用安排。项目规则是"原样保留、不追溯改写"，推送后实际无法撤回。
  - 必要性：计划不需要这个信息。同目录 README.md:10 已写成"属他人"，v11 计划也没有点名。我已核实公开仓库 HEAD 中没有这个用户名。
  - 建议：改为"属他人"，并确认 reviews/ 和将来的 G1/G2 原文都不含该名字。本文也有意没有写出它。

NON-BLOCKING
- N1. run_cpu_unit.py:95-97 生成规范化 booking.json 时，把资源 active 写死为 True；91-94 行只检查资源是否存在，没有检查原始快照里的 active 值。
  - 后果：runner 的资源 active 检查（cpu_target_runner.py:71-72）实际失效。
  - 现状：当前快照 active=true，原始快照的 SHA 也会保存，可以事后核对。
  - 建议执行前修复：从原始快照拷贝 active 值，非 true 时在本地拒绝。结果审查时核对原始快照与规范化文件逐字段一致。
- N2. 三个编排脚本 deploy_v13_remote.sh、remote_host_probe.py、run_cpu_unit.py 不在 manifest 和 Git-first 链内，也不在任何 Gate 的审查文件清单里。仓库中也只看到 v11 编排的输出，没有脚本本身。
  - 建议：把三个脚本的实际字节和 SHA 随结果证据一起保存或提交，并纳入结果审查。
- N3. run_cpu_unit.py:88 会在本地保存约 2.4 MB 的完整原始快照，里面有全部资源的 ssh_host/ssh_config（公网地址和登录用户）以及数千条他人预约。
  - 建议：结果发布时不提交这个文件，只提交规范化后的本人票和原始快照 SHA。v11 公开的版本只有 437 字节。
- N4. 计划:16 写的"每进程 RLIMIT_AS/RLIMIT_CPU"不精确。
  - 实际：cpu_target_runner.py:319-324 只对测试子进程设限，子进程派生的 helper 会继承；父 runner 不受这两个限制。300 秒包含 preflight 时间。
  - 建议：措辞改为"测试子进程及其 helper"。如果确实要限制父进程，需另加 prlimit 并重新审查。
- N5. 计划:17 写"已审 git 本地只读"，比 runner 的实际强制宽松。
  - 实际：cpu_target_runner.py:177-187 只限定可执行文件为 git 或自身 Python，拒绝 5 个联网子命令，并要求 cwd 在 root 内。socket 补丁不覆盖 getaddrinfo。
  - 风险：测试源码中直接调用的 git 只有 `git --version`，风险低。
  - 建议：计划措辞与实际强制一致，由 G2 确认。
- N6. 失败处理建议在修 B1 的同一轮补齐：
  - (a) 部署中断：v11 曾在同一新 root 内恢复，而本次部署脚本拒绝已存在的 root。需事先写明 claim 前的恢复规则。
  - (b) claim 前被拒：例如观测超过 300 秒、时钟偏差、main 被推进、probe 拒绝。runner 本身允许再次调用，但 run_cpu_unit.py:57-58 和 :151 会阻止重新采集，计划又写了"不在同 root 重跑"。需事先决定这种情况是否算当日单元终止。
  - (c) 设一个内部开跑截止（如 18:30）。runner 允许的最晚开跑时间是 18:54:30，需要给下载和收尾留出余量。
  - (d) push 后到 runner 启动前，不要向 main 推其他 commit（run_cpu_unit.py:106 要求 main 等于指定 commit）。
  - (e) 如果 G2 要求改代码，保持目录名和 scope 不变，G1 才仍然有效；同时同步更新计划里的 manifest SHA。
- N7. run_cpu_unit.py 先取预约快照，再做 GitHub GET、probe 和上传。v11 从预约观测到 claim 实际用了 230.4 秒，接近本地 240 秒门槛和 runner 300 秒上限。
  - 建议：先做 GitHub GET，最后连续采集预约和 probe。
  - 另外记录本地与 qjh000 的时钟偏差：booking 的 observed_ms 用本地时钟，runner 用服务器时钟，fresh() 会拒绝负年龄。
- N8. AGENTS.md 仍写 Codex 为执行者，没有记录 2026-10-28 的角色互换。
  - 建议：按 §6 追记角色变化。在 reviews/ 中标明实际审查者是新上下文的 Claude Code subagent，与执行者属同一模型族。
  - G1-original.json 的 reviewer_id 由主执行者指定，代码无法验证；original_review_text 必须是本文全文原样。
- N9. 计划:6 写"10:01 API"，与快照文件名（0959）和写入时间（10:00:23）不完全一致。建议直接引用快照文件名和 SHA。

QUESTIONS
- Q1. work/claude-continuation-20261028/booking/ 下有 book-gpu-1900.json（0 字节，11:12）、book-gpu-1900.err（54 字节）、login.out 和 login2.out（11:22/11:27）。为避免接触认证材料，我没有读它们的内容。
  - 请说明：是否尝试过创建 19:00 起的 GPU 预约？依据哪条用户原话？结果如何？
  - 本 G1 不覆盖任何 GPU 预约。如果没有用户明确授权，应如实告知用户并记录，且不得使用该预约。
- Q2. 计划:7 写"8 张 GPU 均被他人占用"，这是怎么得到的？
  - 如果用了 nvidia-smi，那是在单元之外、他人 GPU 窗口内做的只读 GPU 查询，应在计划中注明。
  - fresh probe 和 runner 都不应再查询 GPU。
- Q3. 关于这张 CPU 票和用户原话的解释：
  - 我只能核实这张票属于 boyjiang 账号、创建于 09:41:17，早于本工作目录的首个文件（10:00:23）；无法核实是用户本人操作还是经授权的 agent 创建。
  - "先做cpu的适配吧"我按上下文理解为允许在 qjh000 执行 CPU 验证。如果用户原意只是本地改代码，以用户为准。
- Q4. 角色互换后，用户是否接受由主执行者派生的新上下文 Claude subagent 作为 AGENTS.md §3 所说的独立审查？先例是 Codex 依 §3.2.1 派生的 subagent。

GATE_RESULT: {"gate": "G1", "scope_sha256": "bca7fd453c2d96c30363ec0e9ef8d731297208102a9c8e9b9d9199c8c81f4309", "decision": "REQUEST_CHANGES", "blocking": 1}

---

## 主执行者处理记录

- B1：已删除计划中的第三方用户名，改为“属他人”；同时清理了本地 SpaceServe 计划草稿中的同一名字。reviews/ 与将来的 G1/G2 原文不写该名字。
- N1：已修复，规范化 booking 的 active 取自原始快照，且非 true 时本地拒绝。
- N2：采纳，三个编排脚本的实际字节与 SHA 随结果证据保存并纳入结果审查（已写入计划）。
- N3：采纳，完整原始快照只留本地，公开时只提交规范化本人票与原始快照 SHA（已写入计划）。
- N4、N5：已按实际强制修改计划措辞。
- N6：已在计划新增“失败与时限规则”：claim 前部署中断可在同 root 继续；claim 前被拒最多再采集两次、各自 attempt 目录；内部最晚开跑 18:30；push 后不再推 main；G2 改代码时保持目录与 scope 不变并重新 G2。运行脚本已按此实现（claim 存在即拒绝、attempt 目录、不覆盖上传）。
- N7：已采纳，顺序改为 GitHub GET → 时钟偏差记录 → 预约快照与 host probe 连续采集；本地门槛改为 200 秒。
- N8：AGENTS.md §6 已追记 2026-10-28 角色变化；本文件头部标明实际审查者。
- N9：计划改为引用快照文件名与 SHA。
- Q1：是。用户 2026-10-28 在主执行者的提问中选择“帮我约今晚 GPU”（qjh000 GPU 19:00–次日 08:00）。创建请求因已保存 token 缺少 bookings:create:self 权限被拒，两次设备授权均在用户批准前过期，预约尚未创建；本 G1 与 CPU 单元不涉及该预约。
- Q2：来自同一次只读 SSH 探测中的一次 nvidia-smi 查询，已在计划中注明；fresh probe 与 runner 不查询 GPU。
- Q3：用户原话之前，主执行者的提问已说明“白天我先在 qjh000 上做 EPD/PD 新代码的 CPU 部署和测试”，用户随后回答“先做cpu的适配吧”；据此理解为允许在 qjh000 执行 CPU 验证。该票是否用户本人创建无法由主执行者核实，记录为不确定。
- Q4：用户要求 Claude Code 接续 Codex 并按既有流程推进；AGENTS.md §3.2.1 已授权 subagent 接替审查。主执行者据此使用新上下文 subagent，并会在汇报中向用户说明，若用户不接受可另行指定审查者。
