# G5（代码发布）审查请求原文（主执行者经 SendMessage 发给 G1 审查者）

- 实际审查者：G1 同一新上下文 Claude Code subagent（只读）。基础提示词为 g5-code-publication-prompt.md（其中 `<STAGED_TREE>` 占位符因提示词本身位于暂存树内而保留），实际暂存树与补充核对项如下。审查原文见 g5-code-publication-subagent.md。

---

G5（代码发布）审查请求：请按 D:\Documents\codex\2026-10-23\new-chat-2\work\repository-upload\checkout\epd\plans\fair-pd-20261028-v13\reviews\g5-code-publication-prompt.md 执行（只读规则不变：不修改文件、不 commit/push、不 SSH/网络/GPU、不读凭据；允许只读 git 命令与本地 SHA 计算）。

实际暂存树：5d2fe9971dddee6382a626e1e6e79be3a3d76afb；parent：85619cfcf553796ab3b3501e4a386f4a867f1801（远端 main 仍是它）。提示词里的 <STAGED_TREE> 即此值（提示词文件本身在暂存树内，故保留占位符）。暂存 85 个路径：v13 源码 54、plans 目录、epd/README.md 与 epd/code/README.md 各一句导航。

自你第 2 轮之后的新增与变化，请一并核对：
1. G1-original.json（SHA 1fb58153…8d38）用你第 2 轮原文全文（reviews/g1-cpu-unit-round2-subagent-original.md）；G2-original.json（SHA 9abac4e1…8a32）用 G2 审查者原文全文（reviews/g2-v13-code-subagent-original.md，结论 APPROVE_WITH_NITS/BLOCKING 0，scope 9d3b08f1…6f63）。两者都由 orchestration/write_gate_original.py 生成，scope 摘要现场复算。
2. 新增 execution-notes.md：不改写已审计划（plan 仍为 98b39014…），记录你第 2 轮 N-a～N-f 的处理、Q-a 的预演记录（目录 /var/tmp/boyjiang-deploy-gitcheck-20261028，不是单元 ROOT，验证后删除）。
3. host probe 口径修正（请确认仍在 G1 范围内）：只读预演时发现 CPU50 上固定有 cpuhp/50、idle_inject/50、migration/50、ksoftirqd/50、kworker/50:* 等每 CPU 内核线程（PF_KTHREAD 置位、父进程 kthreadd）。原定义会把它们当冲突，使 probe 永远拒绝。现定义为“PF_KTHREAD 未置位且 Cpus_allowed_list 恰为 50 的用户态进程”；修正后对已消耗 v11 root 预演：冲突为空，并正确识别出已有 claim。昨天同一次开机上的 v11 probe 也是空列表。
4. 新增 orchestration/（6 个脚本的字节副本，SHA 列在 execution-notes.md）；run_cpu_unit.py 已按你的 N-a/N-b/N-c 修改（只读准备成功后才计 attempt；负偏差先等待；SSH 断开时只读轮询回执再下载，绝不重跑）。
5. reviews/ 下 G2 的处理记录 g2-v13-code-handling.md 写明 v12 G2 原文缺失、本次 G2 取代之，以及非阻塞项 1（controller 清理循环）是任何 GPU 使用前的硬前置。

请按提示词的输出格式给出结论，最后一行 GATE_RESULT（staged_tree 为你实际看到的暂存树）。
