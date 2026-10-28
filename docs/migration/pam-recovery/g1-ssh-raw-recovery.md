结论：APPROVE（窄恢复G1）
BLOCKING：0
reviewed_at_utc：2026-10-28T14:35:56Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

原件显示第二次data恢复仍在写前退出，三个目标及asset-data证据目录不存在；完整不可读cwd盘点只有已知PAM及两个符合所述结构的SSH会话。两次失败不能记为复制尝试成功。

认可使用**固定boot下的root-owned sshd daemon锚点及直接父子关系**识别动态SSH transport，较逐PID追加例外稳定，且范围仍可限制。批准实现以下精确规则：

- 仅处理cwd读取的PermissionError；可读cwd属于源项目时仍拒绝。
- 实际子进程UID2147、comm、cmdline SHA及完整cgroup格式匹配；正则须整串匹配session数字，不能使用子串包含。
- 直属父实际UID0、comm=sshd、PPID=7347；daemon同时匹配固定boot、PID7347、UID0、PPID1、startticks19660及精确ssh.service cgroup。
- 对子、父、daemon先后完整复读身份并要求一致，保存实际PID/startticks、UID、PPID、cgroup及可读摘要。消失、身份变化、字段不可读或任何其他未知cwd均拒绝，不自动学习新锚点。
- 保留现有精确PAM例外；不跳过整个session/cgroup中的其他进程，不发送信号或清理服务。

这是对“系统transport身份可解释但cwd不可读”的有限豁免，**不能宣称已证明该进程没有任何源目录引用**。本阶段只读源、不删改源，复制前后完整SHA仍须验证；完整引用审计留给后续清理。

批准范围为上述修复设计及条件性一次data恢复。第三次实际启动前必须完成新G2、针对性正反例测试、结果复核、G5/public push、三端工具/wrapper字节核验和fresh现场准入；原两次失败保留。env/model仍未启动，不增加其预算或自动重试权限。

NON-BLOCKING：无。
QUESTIONS：无。

本次仅本地只读审查，未测试、远端操作、写文件、访问网络或GPU。

GATE_RESULT: {"gate": "G1", "scope": "boot_bound_root_sshd_transport_exception_and_one_conditional_data_recovery", "decision": "APPROVE", "blocking": 0}
