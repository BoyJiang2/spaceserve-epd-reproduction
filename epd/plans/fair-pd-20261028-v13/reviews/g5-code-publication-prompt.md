你是本项目的独立审查者，只读。不要修改、创建或删除任何文件，不要 commit/push、运行测试、SSH、访问 GPU 或网络，不要读取凭据。允许只读 git 命令（status/diff/show/ls-files/cat-file/rev-parse）与本地 Python 只读计算 SHA256。

项目背景与硬性边界见 `D:\Documents\codex\AGENTS.md` 与 `D:\Documents\codex\2026-10-23\new-chat-2\PROJECT_GOAL.md`。仓库本地 checkout：`D:\Documents\codex\2026-10-23\new-chat-2\work\repository-upload\checkout`（公开仓库 BoyJiang2/spaceserve-epd-reproduction，main 当前 85619cf）。

## 审查 Gate
G5：交付（仅代码发布）——把 EPD/PD 候选 v13 及其 CPU 单元审查记录作为一个普通 commit 推到 main，供 qjh000 按指定 commit 部署。这不是 CPU 结果或实验完成的交付。

## 本次变更
已 `git add` 的暂存区即为待提交内容（请用 `git diff --cached --stat` / `git diff --cached` 查看），预期只包含：
- 新增 `epd/code/fair-pd-candidate-20261028-v13/`（54 文件，须与 `epd/plans/fair-pd-20261028-v13/source-manifest-v13.json` 逐文件 SHA 一致，暂存 blob 字节即文件字节，仓库 `.gitattributes` 为 `* -text`）。
- 新增 `epd/plans/fair-pd-20261028-v13/`：计划、scope、manifest、三个增量补丁、feasibility、用户指令与归档、G1/G2 原始 JSON、reviews（提示词与审查全文）、未执行回执、README。
- 修改 `epd/README.md` 与 `epd/code/README.md` 各一句导航。
暂存树：`<STAGED_TREE>`；parent：`85619cfcf553796ab3b3501e4a386f4a867f1801`。

## 请重点检查
1. 暂存内容是否严格只有上述路径；旧目录（v11、v8 候选、validation、spaceserve/、旧 Release 相关）是否零改动。
2. 暂存的 54 个源码 blob 是否与 manifest SHA 完全一致（可用 `git show :<path>` 计算）；manifest 自身 SHA 是否为 `4065e53e0697d7e0478a5900e34416050124772ac9df5d48a50863d8fc453a4d`。
3. G1/G2 原始 JSON：gate、scope_sha256（G1=`bca7fd45…4309`，G2=`9d3b08f1…6f63`）、decision、blocking=0、reviewer_id 在 scope.reviewer_ids 内且不等于 executor_id，original_review_text 与 reviews/ 中审查全文一致、未被改写。
4. 公开内容是否含凭据、token、密码、私人对话链接或其他敏感信息（特别注意 user-original-instruction.txt 与 reviews/）。
5. README/导航是否如实写明“CPU 单元尚未执行、无 GPU/性能结果、controller 未完成”，没有夸大。

## 输出格式
- 结论：APPROVE / APPROVE_WITH_NITS / REQUEST_CHANGES
- BLOCKING / NON-BLOCKING / QUESTIONS（文件:行号 + 理由 + 建议）
不确定的地方请明确说不确定。最后单独一行：
`GATE_RESULT: {"gate": "G5", "staged_tree": "<你看到的暂存树>", "decision": "<结论>", "blocking": <BLOCKING条数>}`
