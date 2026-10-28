G1 第 2 轮（窄范围复核，同一 scope）

结论：APPROVE_WITH_NITS

第 1 轮的 BLOCKING（B1）和 NON-BLOCKING（N1–N9）都已关闭。本轮没有新的 BLOCKING。下面的 nits 都是执行稳健性和措辞问题，不影响安全性和授权边界。

核对记录（全部只读：没有运行测试，没有 SSH、网络或 GPU，没有读取凭据）：
1. 文件 SHA256：
   - 与主执行者所述一致：
     - plan.md：98b39014ca623f33f65d1d7975b45b04e5256a8b51bd148df4c05345799dff44
     - run_cpu_unit.py：a6dd9bca…756a
     - deploy_v13_remote.sh：0a20e946…cb64a
     - remote_host_probe.py：4b5aceac…ef6d，内容与第 1 轮所读相同
   - 与第 1 轮相同、未变：
     - scope.json：8440bdcf…8d44b96
     - cpu_target_runner.py：9e81f214…e1a5a0
     - source-manifest-v13.json：4065e53e…453a4d
     - user-CPU-grant.json：e415e3ad…a5a2d3
     - user-original-instruction.txt：d4aeaf18…bea3ef
2. 摘要与一致性：
   - 我复算 digest(scope) 得到 bca7fd453c2d96c30363ec0e9ef8d731297208102a9c8e9b9d9199c8c81f4309。
   - grant 仍绑定这个摘要。
   - 用 AST 读出的 runner POLICY 与 scope.policy 逐项相等。
   - executor_id 与两个 reviewer_ids 互不相同。
   - G2 摘要交叉复算为 9d3b08f1…6f63。
3. B1 已关闭：plan:6 已改为"属他人"。我在以下范围做了不区分大小写的检索，都没有出现该用户名；用已知字符串做的正对照检索结果正常：
   - plans 目录，含 reviews/ 中的第 1 轮原文与处理记录；
   - v13 源码目录；
   - 整个 checkout 工作树（git grep --untracked）；
   - AGENTS.md 与 PROJECT_GOAL.md。
4. N1 已关闭：run_cpu_unit.py:128 在原始快照的 active 不是 true 时本地拒绝；:134 从原始快照拷贝 active 值。
5. N2/N3 已关闭，执行时兑现：
   - plan:22 写明三个编排脚本的字节和 SHA 随结果证据保存，并纳入结果审查；
   - 完整快照只留本地，依据 plan:6、plan:22 和 run_cpu_unit.py:124。
6. N4/N5 已关闭：plan:16–17 的措辞现在与 runner 的实际强制一致：
   - 父 runner 和测试子进程都限 CPU50、nice10；
   - RLIMIT 只施加于测试子进程及其 helper；
   - 300 秒包含 preflight；
   - 子进程只允许 git 或 runner 自身 Python，拒绝 5 个联网子命令，cwd 必须在 root 内。
7. N6 已关闭。plan:24–30 新增"失败与时限规则"，覆盖：
   - claim 前部署中断：在同一新 root 内继续；
   - claim 前被拒：最多再采集两次，每次独立 attempt，不改动已提交文件；
   - claim 写入后即为当日唯一结果；
   - 内部开跑截止 18:30；
   - v13 push 后不再向 main 推送；
   - 记录时钟偏差；
   - G2 若要求改代码，目录与 scope 不变，并重新 G2。

   脚本实现与之对应：
   - claim 已存在即拒绝（:61-63）；
   - attempt 不超过 3 次（:58-60）；
   - 每次用新文件名，permit 仍放在 plans 目录根下（:67-68），满足 bound_bytes 的路径约束；
   - tar -k 不覆盖已有文件（:170）。

   不会出现第二次测试执行：claim 由 runner 以独占创建写入固定路径，每个 root 只有一个；host probe 也把已有 claim 视为活动单元（remote_host_probe.py:26-29、run_cpu_unit.py:142）。
8. N7 已关闭（负时钟偏差的问题见 N-b）：
   - 顺序为：部署记录 → GitHub GET → 时钟偏差 → 预约快照 → host probe → 上传 → 本地年龄不超过 200 秒才启动（:79-175）。
   - 按偏差不超过 60 秒、runner 启动约 10 秒估算，服务器侧看到的预约年龄约在 270 秒以内，低于 runner 的 300 秒上限。
9. N8 与 N9 已关闭：
   - AGENTS.md:1052-1057 已追记 2026-10-28 的角色变化；round1 文件头标明了实际审查者。
   - plan:6 改为引用快照文件名与 SHA。
10. 部署脚本：
    - 新流程为 clone --sparse --no-checkout --depth=1，然后 sparse-checkout set、fetch 指定 commit、detach checkout。
    - 其余部分未变：拒绝已存在的 ROOT，逐 SHA 核对，拒绝多余文件，要求 tracked clean，核对 HEAD。
    - 主执行者说这个流程已在 qjh000 预演过；我无法独立核实，见 Q-a。
11. 第 1 轮问题的答复均已记录。这些答复我无法独立核实，以下按主执行者的陈述记录：
    - Q1：GPU 预约尝试依据用户的选择；因 token 缺少创建权限，预约没有创建成功。
    - Q2：那次是单元之外的一次只读 nvidia-smi，已在 plan:7 注明。
    - Q3：提问时已说明白天在 qjh000 做 CPU 部署和测试；这张票是谁创建的仍记为不确定。
    - Q4：将向用户说明审查安排。
    本 G1 仍然不覆盖任何 GPU 预约或使用。

BLOCKING：无。

NON-BLOCKING
- N-a. 前置失败也会消耗 attempt 次数。
  - 问题：run_cpu_unit.py:58-66 在所有前置步骤之前就建立 attempt 目录。因此以下任何一种瞬时失败，或误传 commit 参数，都会消耗三次中的一次，而 runner 根本没有运行：读取部署记录、GitHub GET、时钟 SSH、预约快照（token）、probe SSH。
  - 影响：这种计数偏保守，不影响安全。
  - 建议：在第一个 attempt 之前做一次不计数的只读连通性检查（ssh true、GitHub GET、只读快照）；或者在计划中写明"任何采集尝试都计数"。
- N-b. 负时钟偏差可能导致误拒。
  - 问题：脚本只检查偏差绝对值不超过 60 秒（:116），没有补偿负偏差。runner 看到的预约年龄 = 本地经过时间 + 偏差。服务器比本地慢时，如果本地经过时间小于偏差的绝对值，fresh() 会以"负年龄"拒绝。
  - 建议：偏差为负时，先等本地经过时间超过偏差绝对值再加几秒才启动，同时仍守住 200 秒门槛；或者把阈值收紧到约 ±10 秒。
- N-c. SSH 中途断开时下载可能不完整。
  - 问题：:185-199 在 SSH 断开时会立即下载，而 runner 可能仍在服务器上运行。
  - 建议：ssh_exit 非 0 时，先只读确认 CPU-receipt.json 已写出或 runner 已结束，再下载；必要时可再次只读下载，绝不重跑。
- N-d. plan:27 的措辞。
  - 问题：这条写的是"runner 在 claim 前拒绝"，但所举例子里包含编排脚本层面的拒绝，例如 main 前移、probe 拒绝。
  - 建议：改为"claim 前任何拒绝（runner 或编排脚本）"。纯措辞。
- N-e. 与 SpaceServe 窗口的先后顺序。
  - plan:28 的"push 后不推 main"同样约束 SpaceServe 夜间窗口的代码发布 commit：EPD runner 必须在任何 SpaceServe push 之前启动并收尾。
  - PROJECT_GOAL 也禁止同机正式运行期间有另一系统的负载。本单元及结果下载应在 19:00 GPU 窗口前完成。
- N-f.（可选）加强 Q3 的授权记录。
  - 现状：Q3 的提问上下文目前只出现在处理记录中。
  - 建议：可以把主执行者的提问原文（标明作者）与用户的回答并列归档。这样做 grant 的 SHA 会变，但 scope 摘要不受影响。

QUESTIONS
- Q-a. 在 qjh000 预演部署流程时用的是哪个目录？
  - 请确认它不是本单元的 ROOT `/var/tmp/boyjiang-epd-cpu-qjh000-20261028`；否则正式部署会因"ROOT 已存在"被拒，该检查本身是安全失败。
  - 请把预演的目录、时间和结果写入部署记录。这次预演不在第 1 轮计划里；它不是测试单元，但属于远端操作，应如实记录。

GATE_RESULT: {"gate": "G1", "scope_sha256": "bca7fd453c2d96c30363ec0e9ef8d731297208102a9c8e9b9d9199c8c81f4309", "decision": "APPROVE_WITH_NITS", "blocking": 0}
