你是本项目的独立审查者，只读。不要修改、创建或删除任何文件，不要运行测试、实验、SSH、访问 GPU 或网络，不要读取凭据。允许只读查看文件、`git diff --no-index` 比较本地目录，以及本地 Python 只读计算 SHA256。

项目背景与边界见 `D:\Documents\codex\AGENTS.md` 与 `D:\Documents\codex\2026-10-23\new-chat-2\PROJECT_GOAL.md`（当前目标：先完成 SpaceServe 三组可信性能对照）。仓库本地 checkout：`D:\Documents\codex\2026-10-23\new-chat-2\work\repository-upload\checkout`。

## 审查 Gate
G1＋G2：SpaceServe qjh000 2026-10-28 夜间新窗口（计划与机械代码派生）。

## 本次变更
- 计划：`D:\Documents\codex\2026-10-23\new-chat-2\outputs\spaceserve-window-20261028-2300\plan.md`（新窗口独立 54 单元，沿用 13:00 窗口冻结方案）。
- 实际预约：用户票 `bk-20261028T0700-987277c5`，h20/qjh000 GPU lane，2026-10-28 23:00（1793199600000）→ 10-29 08:00（1793232000000）。证据为计划中引用的本地只读 API 快照 `D:\Documents\codex\2026-10-23\new-chat-2\work\claude-continuation-20261028\booking\snapshot-1500.json`（含他人预约与主机信息，只按本人票 id 与 h20/qjh000 过滤查看，审查输出中不要写出他人用户名）。
- 代码：`spaceserve/code/h20-window-20261028/` 由 `D:\Documents\codex\2026-10-23\new-chat-2\work\claude-continuation-20261028\tools\make_space_window.py` 从 Git 83edff6 的 `spaceserve/code/h20-window-20261027/` 派生；本地辅助工具 `D:\Documents\codex\2026-10-23\new-chat-2\work\space2300-tools\` 由同目录 `make_space_tools.py` 从 `work\space1300-tools\` 派生。请直接 `git diff --no-index` 新旧目录核对。

## 请重点检查
1. 计划是否与用户授权、当前目标及 13:00 窗口冻结方案一致（模型/输入/54 顺序/预算/门槛/清理），有无越界（增卡、并行 EPD、复用旧 G3/旧 boot、跨窗拼区组、19:00–23:00 无票时段的远端操作）。
2. 代码差异是否只限窗口身份：新 root、Ray 临时目录、仓库前缀、booking 常量（无延长票且任何 extension 均拒绝）、两个窗口时长相关测试、重新生成的 56/61 清单与部署工具 SHA pin；有无遗漏仍指向旧 root/旧票的引用（脚本、工具、配置）。
3. booking_window.validate 与 refresh_booking.select_booking 在新常量下的边界：开始前、结束前 120 秒、过期、他人票、CPU 票、陈旧证明是否均拒绝；新测试是否覆盖。
4. 重新生成的清单与文件实际 SHA 一致；部署工具 pin 指向新清单。
5. 公开仓库内容不含凭据、他人用户名或其他敏感信息。

## 输出格式
- 结论：APPROVE / APPROVE_WITH_NITS / REQUEST_CHANGES
- BLOCKING / NON-BLOCKING / QUESTIONS（文件:行号 + 理由 + 建议）
最后单独一行：`GATE_RESULT: {"gate": "G1+G2", "decision": "<结论>", "blocking": <BLOCKING条数>}`
