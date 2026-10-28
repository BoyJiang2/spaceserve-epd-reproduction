结论：APPROVE（窄恢复G1）
BLOCKING：0
reviewed_at_utc：2026-10-28T14:23:44Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

原件支持本次失败发生于写入前：data实际exit1，三个目标及asset-data证据目录均不存在。两次只读观测的PID/startticks/UID及父子关系一致，父进程为已记录的用户systemd服务；子进程cwd/exe确因PermissionError不可读。未发现需要扩大例外范围的依据。

批准最小修复设计：

- 仅在指定boot、父子两组PID/startticks/UID/PPID/comm/cmdline SHA/cgroup，以及父exe路径**全部实时精确匹配**时，对该sd-pam的cwd PermissionError作只读例外。
- 例外只处理不可读cwd，不跳过其他检查；若cwd可读且属于源项目，仍须拒绝。
- 核验过程前后复读身份，身份变化、缺字段或其他PermissionError均拒绝；不按裸comm/UID匹配，不自动接纳新PID或重启后的服务。
- 将例外实际匹配原件及其SHA写入claim/终态。不发送信号、不清理该服务，不称已完成FD/maps引用审计。

此为受审本机工具代码修改及**后续一次data恢复**的条件性计划批准。实际恢复前仍须新G2、针对性CPU测试与结果复核、G5/public push、三端字节及wrapper新hash核验，并重新确认fresh CPU资源与所有目标/evidence不存在。旧失败原件保留；env/model未启动事实保持，不据此增加同一单元重试次数或时间预算。

无需为避免这一明确系统服务而取消整体cwdguard；所提精确身份例外已是较小修法。此批准不覆盖GPU、删除或任何实验runtime变更。

NON-BLOCKING：无。
QUESTIONS：无。

GATE_RESULT: {"gate": "G1", "scope": "exact_boot_bound_systemd_PAM_readonly_guard_exception_and_one_conditional_data_recovery", "decision": "APPROVE", "blocking": 0}

## 前阶段时间审计更正（追加，原文不改）

审查者在实际raw阶段G1（2026-10-28T14:15:29Z，实际clock）明确：此前本地资产工具G1正文中的 `13:58:00Z` 未经clock工具实测，不能作为精确审查时刻证据；原文保留并附此更正。实际资源准入依赖API观察与服务器/本地时钟回执，不依赖该审查时间字符串。
