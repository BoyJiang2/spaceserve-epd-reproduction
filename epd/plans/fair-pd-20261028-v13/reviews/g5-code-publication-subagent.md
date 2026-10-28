# G5（代码发布）审查原文：EPD/PD 候选 v13

- 实际审查者：G1 同一新上下文 Claude Code subagent（只读）；请求原文见 g5-code-publication-request.md。
- 结果：APPROVE_WITH_NITS，BLOCKING 0，暂存树 5d2fe9971dddee6382a626e1e6e79be3a3d76afb。据此提交 commit f1ff073dee310ae0b2922d3be7a558b6a12ca7ec（tree 同上，parent 85619cf），普通 push 前远端 main 仍为 85619cf，push 后远端 main 为 f1ff073。处理记录见文末。

---

G5 审查（仅代码发布）：EPD/PD 候选 v13 及其 CPU 单元审查记录

结论：APPROVE_WITH_NITS

暂存内容、源码完整性、G1/G2 原始 JSON 和公开内容都已逐项核对，没有阻塞问题。下面的 nits 是文档措辞和记录完整性问题。

核对记录（只用了 rev-parse、cat-file、diff、ls-files、show 和本地 SHA 计算；没有 commit/push、SSH、网络或 GPU，没有读取凭据）：

1. 暂存树与范围
   - HEAD 为 85619cfcf553796ab3b3501e4a386f4a867f1801，本地 origin/main 也是这个值。远端我没有联网核实。
   - 5d2fe9971dddee6382a626e1e6e79be3a3d76afb 是 tree 对象；`git diff --cached --quiet` 对它退出 0，说明索引与该树完全一致。
   - 相对 parent 共 85 个路径：
     - 83 个新增：epd/code/fair-pd-candidate-20261028-v13/ 下 54 个，epd/plans/fair-pd-20261028-v13/ 下 29 个；
     - 2 个修改：epd/README.md 和 epd/code/README.md，各追加一句导航。
   - v11、v8 候选、validation、spaceserve/ 等旧目录零改动。
   - 工作区与暂存字节一致，没有未暂存的改动，也没有漏掉的未跟踪文件。`.gitattributes` 为 `* -text`。

2. 源码完整性
   - 暂存 manifest 的 SHA256 为 4065e53e0697d7e0478a5900e34416050124772ac9df5d48a50863d8fc453a4d。
   - 54 个条目用 `git show :<path>` 逐一计算 SHA256，全部一致。
   - 暂存的源码路径集合与 manifest 完全相同。

3. 已审文件均未变
   - plan：98b39014…dff44，即 G1 第 2 轮所审版本；
   - scope.json：8440bdcf…，digest 为 bca7fd45…4309；
   - user-CPU-grant.json、user-original-instruction.txt、plans/README.md、cpu-receipt，以及三个 patch。

4. G1/G2 原始 JSON
   - G1-original.json（1fb58153…8d38）：
     - gate=G1；scope_sha256=bca7fd45…4309，我按 scope.json 复算一致；
     - decision=APPROVE_WITH_NITS，blocking=0（整数）；
     - reviewer_id=claude-code/subagent-G1-cpu-unit-20261028，在 reviewer_ids 内且不等于 executor_id；
     - original_review_text 与 reviews/g1-cpu-unit-round2-subagent-original.md 逐字节相同，只差文件末尾一个换行（write_gate_original.py 做了 strip）；
     - 我逐段比对过，这就是我第 2 轮的原文，没有被改写；文中的 GATE_RESULT 与 JSON 字段一致。
   - G2-original.json（9abac4e1…8a32）：
     - gate=G2；scope_sha256=9d3b08f1…6f63，用 scope 摘要和暂存 manifest SHA 复算一致；
     - decision=APPROVE_WITH_NITS，blocking=0；
     - reviewer_id=claude-code/subagent-G2-v13-code-20261028，在 reviewer_ids 内且不等于 executor_id；
     - 正文与 reviews/g2-v13-code-subagent-original.md 相同，只差末尾换行；文中的 GATE_RESULT 与 JSON 字段一致；
     - 我无法拿 G2 审查者的实际输出来对照，只能确认这两份暂存副本彼此一致。
   - 两份 JSON 都满足 cpu_target_runner.py 中 require_review 的全部条件。

5. 编排脚本
   - orchestration/ 下 6 个文件的暂存 SHA，与 execution-notes.md 表格一致，也与本地 tools/ 目录中的实际文件一致。
   - run_cpu_unit.py 已按第 2 轮的 N-a/N-b/N-c 修改，与 execution-notes 的描述一致：
     - N-a：claim 检查、读已提交文件、部署记录、GitHub GET、时钟偏差这些只读准备全部成功后，才建立 attempt 目录（:111-114）。
     - N-b：时钟偏差为负时，上传后先等到本地经过时间不少于偏差绝对值加 3 秒再启动，仍守 200 秒门槛（:174-180）。
     - N-c：SSH 断开或输出中没有 RUNNER_EXIT 标记时，只读轮询最多 42×10 秒，直到确认没有 claim 或回执已写出，然后下载；不会再次调用 runner（:196-203）。

6. host probe 口径修正（remote_host_probe.py，SHA 25a4e0ac…）
   - 实现：读取 /proc/<pid>/stat 第 9 字段 flags（去掉 comm 之后的索引 6），PF_KTHREAD=0x00200000 与内核定义一致。只排除内核线程；用户态进程的 Cpus_allowed_list 恰为 50 时仍算冲突。输出里的 definitions 字段也已同步。
   - 判断：这仍在 G1 范围内。
     - G1 批准的是"CPU50 无独占冲突"。cpuhp、migration、ksoftirqd、kworker 等是每个核上都有的内核线程，不是他人占用该核的任务。
     - 原口径会让 probe 永远拒绝。修正只是让工具符合计划本意，不会把真正的冲突放行。
     - scope、POLICY 和 runner 都没变，runner 仍要求冲突列表为空。
     - 与昨天同一次开机上 v11 probe 得到空列表的结果一致。
   - 已知局限（G1 第 2 轮所审版本已有，不是新引入）：只看线程组主线程，不检查 /proc/<pid>/task/* 中各线程的 affinity；也不统计绑在"包含 CPU50 的小 CPU 集合"上的进程。在 nice10 和极小负载下可以接受。

7. 公开内容
   - 对 85 个暂存 blob 做了模式扫描，以下各类均未命中：
     - GitHub、OpenAI、Slack、AWS 等 token；
     - 私钥、ssh 公钥；
     - Bearer / Authorization 头；
     - password、secret、api_key、token、device_code 等键值；
     - ChatGPT、Claude、Codex 分享链接；
     - 预约服务域名、电子邮件、非回环 IPv4。
   - 唯一看起来像 IP 的点分数字，是 epd/README.md 中原有的 cuBLAS 版本号。
   - 另外在内存中把预约快照里 103 个他人用户名和 21 个 ssh 主机/跳板值与暂存内容比对，没有打印原值。结果：
     - 只命中一个恰好等于常见英文单词的用户名（出现在普通英文句子里）和代码中的 localhost；
     - 所在文件与已公开的 v11 文件逐字节相同，属于误报；
     - 第三方用户名和主机地址都没有出现。
   - user-original-instruction.txt 只有用户两句原话，不含对话链接。
   - reviews/ 中提到 token 的地方，只是"已保存 token 缺少 create 权限"的描述，不含任何凭据值。

8. README 与导航
   - plans README:3 写明"候选代码与审查记录已发布，CPU 单元尚未执行；没有新增 GPU、模型或性能结果"。
   - plans README:12 写明：numeric native36 和 selected360 尚未实现，在 claim 前 fail-closed；1440 请求 / 340 分钟不是执行许可；不称 DistServe 实测；完整的公平对照尚未完成。
   - 两处导航句都写了"CPU 单元尚未执行"。没有夸大。
   - 4 个 md 文件中的相对链接都能在暂存树中解析。

BLOCKING：无。

NON-BLOCKING
- N1. plans README.md:10 的措辞与计划不一致
  - 这里仍写"每进程 1GiB 地址空间"，而已修正的计划:16 写明只限测试子进程及其 helper，父 runner 不受 RLIMIT 约束。
  - 同一行的"不查询"指的是本单元；单元之外曾做过一次只读 nvidia-smi，计划:7 已披露。
  - 建议改成与计划一致的措辞。改动会改变暂存树：可以在结果提交时一并修，或者现在修完按新树重新 G5。
- N2. plans README 没有提到 G2 非阻塞项 1
  - 该项要求 controller 清理循环必须在任何 GPU 使用之前修复，并另走 G2；目前只记录在 reviews/g2-v13-code-handling.md。
  - 建议在 README 的边界/缺口处加一句，避免只读 README 的人漏掉这个 GPU 硬前置。
- N3. plans README:5 的覆盖范围偏窄，且缺少两个链接
  - 这里只说"源码目录继承的 README 仅作上游参考"，但 G2 非阻塞项 9 指出 FOLLOWUP.md、PREFLIGHT.md 和测试 docstring 也已过时。
  - 建议改为"继承的 README、FOLLOWUP、PREFLIGHT 等说明可能滞后，以本页和 plans 文件为准"。
  - README 也没有链接 execution-notes.md 和 orchestration/，建议补上。
- N4. cpu-receipt-v13-unexecuted.json 的 remote_network_GPU_booking_push=false
  - 这个字段沿用 v11 的口径，只指候选打包本身。
  - 同一天另有只读 API/SSH 观察、一次未成功的 GPU 预约创建尝试和一次远端部署预演，都已在计划:7、reviews 处理记录和 execution-notes 中披露，整体记录是完整的。
  - 建议在结果交付时注明这个字段的口径，以免被误读成"当日没有任何远端或预约操作"。
- N5. 两份审查请求原文没有存档
  - AGENTS.md §3.2/§3.2.1 要求在 reviews/ 保存提示词。目前 G1 第 2 轮的请求原文和本次 G5 的补充请求原文（含实际暂存树和新增核对项）都没有存入。
  - round2 原文文件也没有像 round1 文件那样标注实际审查者。
  - 建议在结果提交时补存。如果现在补入，暂存树会改变，需要重新 G5。
- N6. run_cpu_unit.py:199-202 把 NOCLAIM 当作轮询终态
  - 如果 SSH 恰好在 runner 写入 claim 之前（还在 preflight 阶段）断开，脚本可能过早下载，而 runner 随后仍会 claim 并运行测试。
  - claim 的独占创建和 probe 的 root_active_units 检查已经能防止第二次执行，所以这只影响证据完整性。
  - 建议：看到 NOCLAIM 时，再确认 SOURCE_ROOT 内没有自有进程存活（或等一个短宽限期后复查），否则继续等；事后可以只读补下载。

QUESTIONS
- 没有阻塞性问题。只需确认：push 前远端 main 仍是 85619cf。我没有联网核实，本地 origin/main 是这个值。如果远端已经前移，普通 push 会失败，此时应停下来，不要 force。

GATE_RESULT: {"gate": "G5", "staged_tree": "5d2fe9971dddee6382a626e1e6e79be3a3d76afb", "decision": "APPROVE_WITH_NITS", "blocking": 0}

---

## 主执行者处理记录

- QUESTIONS：commit 前以 `git ls-remote` 实测远端 main 仍为 85619cf，普通 push 成功（85619cf..f1ff073），未使用 force。
- N1、N2、N3、N4：已在结果提交中修改 plans README（措辞、GPU 硬前置、继承文档滞后说明、execution-notes/orchestration 链接、未执行回执字段口径）。
- N5：已在结果提交中补存 g1-cpu-unit-round2-request.md 与 g5-code-publication-request.md，并在请求文件头标注实际审查者。
- N6：未修改脚本，以保持实际执行脚本与已提交副本逐字节一致；实际运行中 SSH 未断开（RUNNER_EXIT=0、ssh exit 0），该边界未触发。
