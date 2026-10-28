你是本项目的独立审查者，只读。不要修改、创建或删除任何文件，不要运行实验、SSH、访问 GPU 或网络，不要读取凭据。允许只读查看文件，以及用本地 Python 只读计算 SHA256/规范 JSON 摘要。

项目背景与硬性边界见 `D:\Documents\codex\AGENTS.md`（重点 §2 执行边界、§3 审查流程）与 `D:\Documents\codex\2026-10-23\new-chat-2\PROJECT_GOAL.md`。2026-10-28 起，用户要求 Claude Code 接替 Codex 作为主执行者；你与主执行者及实现者都相互独立。下文路径相对 `D:\Documents\codex\2026-10-23\new-chat-2\work\repository-upload\checkout`（GitHub 仓库本地 checkout，v13 内容尚未提交）。

## 审查 Gate
G1：计划——qjh000 2026-10-28 CPU 验证单元（EPD/PD 代码 v13，仅 CPU）。

## 本次变更
用户今天说“你可以继续他的工作在qjh000上面继续进行工作吗？”，随后“先做cpu的适配吧”，并已自行预约 qjh000 CPU lane。主执行者据此计划在 qjh000 新 root 上运行一次受限 CPU 测试单元，验证 v13 候选代码（v11 之后的 v12 薄 controller + v13-a 修复 + v13 仅更新 runner 范围）。
相关文件：
- `epd/plans/fair-pd-20261028-v13/qjh000-cpu-20261028-plan.md`（本计划）
- `epd/plans/fair-pd-20261028-v13/scope.json`（runner 将要求的精确 scope）
- `epd/plans/fair-pd-20261028-v13/user-original-instruction.txt`、`user-CPU-grant.json`
- `epd/code/fair-pd-candidate-20261028-v13/cpu_target_runner.py`（POLICY 与 preflight/claim/child 限制）
- 预约快照原件：`D:\Documents\codex\2026-10-23\new-chat-2\work\claude-continuation-20261028\booking\snapshot-20261028-0959.json`（2.4 MB，请只按 id `bk-20261028T0141-8936eb9c` 及 resource `h20/qjh000` 过滤查看）
- 先例（已执行、已消耗）：`epd/plans/fair-pd-20261027-v11/`（scope.json、qjh000-cpu-new-plan.md、G1-original.json）

## 请重点检查
1. scope.json 与用户原话、实际预约（id/user/kind=cpu/resource/09:00–19:00 北京即 1793149200000–1793185200000）以及 v13 runner 的 POLICY 是否逐项一致；boot、root、CPU50、1GiB、300+30 秒、一次 claim、零重试是否与计划一致。
2. 用户指令是否足以授权这次仅 CPU 的测试单元；计划有无越出授权或 AGENTS.md 硬性边界（GPU、他人进程、sudo、凭据、包安装、网络服务、旧 root/旧结果复用）。
3. Git-first 顺序（G1→G2→G5→push→指定 commit 部署与逐 SHA→fresh 预约与 host probe→唯一 runner）及失败处理是否完整。
4. 独立复算 `digest(scope)`：`sha256(json.dumps(scope, sort_keys=True, separators=(",", ":")).encode())`，应为 `bca7fd453c2d96c30363ec0e9ef8d731297208102a9c8e9b9d9199c8c81f4309`；executor_id 与 reviewer_ids 是否互不相同。
5. 公开仓库会提交这些文件：是否含凭据、token 或不应公开的信息。

## 输出格式
- 结论：APPROVE / APPROVE_WITH_NITS / REQUEST_CHANGES
- BLOCKING：必须修复的问题（文件:行号 + 理由 + 建议）
- NON-BLOCKING：建议改进
- QUESTIONS：需要主执行者或用户澄清的点
不确定的地方请明确说不确定，不要猜。最后单独一行输出：
`GATE_RESULT: {"gate": "G1", "scope_sha256": "<你复算的值>", "decision": "<结论>", "blocking": <BLOCKING条数>}`
