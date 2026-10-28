你是本项目的独立审查者，只读。不要修改、创建或删除任何文件，不要运行实验、测试、SSH、访问 GPU 或网络，不要读取凭据。允许只读查看文件、本地 `git diff --no-index` 比较目录，以及用本地 Python 只读计算 SHA256/规范 JSON 摘要。

项目背景与硬性边界见 `D:\Documents\codex\AGENTS.md`（重点 §2、§3）与 `D:\Documents\codex\2026-10-23\new-chat-2\PROJECT_GOAL.md`。2026-10-28 起 Claude Code 接替 Codex 为主执行者；v12/v13-a 由 Codex 的实现 subagent 编写，v13 由主执行者机械生成；你与他们都相互独立。下文路径相对 `D:\Documents\codex\2026-10-23\new-chat-2\work\repository-upload\checkout`。

## 审查 Gate
G2：代码与补丁——EPD/PD 候选 v13，用于 qjh000 2026-10-28 的一次仅 CPU 测试单元。

## 本次变更
- 已审已执行基线：`epd/code/fair-pd-candidate-20261027-v11/`（commit 6ca496bb，昨日 76 PASS）。
- 待审：`epd/code/fair-pd-candidate-20261028-v13/`（54 文件），manifest `epd/plans/fair-pd-20261028-v13/source-manifest-v13.json`。
- 增量：`epd/plans/fair-pd-20261028-v13/epd-pd-v11-to-v12.patch`（v12 薄 controller）、`epd-pd-v12-to-v13-a.patch`（针对 v12 G2 的修复）、`epd-pd-v13-a-to-v13.patch`（仅 runner POLICY）。也可直接 `git diff --no-index` 比较 v11 与 v13 两个目录。
- 说明：同目录 `source-feasibility-v12.md`、`source-feasibility-v13-a.md`、`source-feasibility-v13.md`。
- 已知缺口：v12 的独立 G2 结论为 REQUEST_CHANGES/BLOCKING 2，但原文未保存在本地，只有实现者在 source-feasibility-v13-a.md 的转述：B1 为 preflight_controller 的预约校验（booking_for_unit 读取原始绑定预约、拒绝未来时间戳、核对票/用户/资源/窗口/新鲜度及单元+清理覆盖，并在构造 NVML 与 Claim 之前调用）；B2 为 fixed_unit 的请求事件持久化与取消传播。

## 请重点检查
1. 完整性：v13 每个文件与 manifest SHA 一致；相对 v13-a（`D:\Documents\codex\2026-10-23\new-chat-2\work\epd-pd-followup-20261027\v13-a`）只有 cpu_target_runner.py 的 POLICY 与一条报错文本变化，且新值与 `epd/plans/fair-pd-20261028-v13/scope.json` 的 policy 完全一致。
2. B1、B2 是否被 v13-a 真正修复（逻辑与调用顺序），新增测试是否确实覆盖修复点而非空转。
3. 这次 CPU 单元的安全性：runner 的 child 是否仍阻止 GPU 包导入、TCP/UDP、外部可执行文件与网络 git；测试套件（runner 中五个模块）是否有会联网、导入 GPU 包、依赖目标机外部状态、大量 skip 或恒真通过从而误导 CPU 结果的用例。
4. v11→v13 新代码中是否有会让 CPU 结果失真、或将来误放行 GPU/正式阶段的阻塞缺陷；numeric36/selected360 等未实现阶段是否在 claim 与任何 GPU 操作之前 fail-closed。
5. 凭据/敏感信息：公开仓库将提交这些文件。
6. 独立复算 G2 scope 摘要：`digest({"scope_sha256": "bca7fd453c2d96c30363ec0e9ef8d731297208102a9c8e9b9d9199c8c81f4309", "source_manifest_sha256": <manifest 文件实际 SHA256>})`，摘要函数为 `sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode())`，预期 `9d3b08f17d62ce6456747b6c629b046150107bda0bf3863e9a6eb9eaa1e16f63`。

范围说明：controller 整体尚未完成是已知事实，不必因此要求补全；只在缺陷会影响本次 CPU 单元的可信度/安全性，或未实现阶段没有 fail-closed 时列为 BLOCKING。

## 输出格式
- 结论：APPROVE / APPROVE_WITH_NITS / REQUEST_CHANGES
- BLOCKING：必须修复的问题（文件:行号 + 理由 + 建议）
- NON-BLOCKING：建议改进
- QUESTIONS：需要主执行者或用户澄清的点
不确定的地方请明确说不确定，不要猜。最后单独一行输出：
`GATE_RESULT: {"gate": "G2", "scope_sha256": "<你复算的值>", "source_manifest_sha256": "<你复算的值>", "decision": "<结论>", "blocking": <BLOCKING条数>}`
