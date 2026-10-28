结论：APPROVE_WITH_NITS
BLOCKING：0
reviewed_at_utc：2026-10-28T13:58:00Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

批准范围仅为**本地编写CPU资产物化工具与测试源码**，之后独立G2/G5、Git-first；不批准当前直接复制或运行环境。

计划与原始盘点一致：旧root归UID2147、未见自有cwd进程；EPD环境约6.81GB、MiniCPM约16.21GB、dataset约1.88MB，另复制指定359,096字节IPC库。两个项目代码迁移审查不能替代这些资产的实际复制和可迁移性验收。

实现时保留以下明确约束：

- 只允许给定source→destination映射，目标不存在才创建；源与目标完整成员、类型、bytes/SHA及链接文本比对，源before/after不变。
- 旧inventory跳过了 `.git`、`__pycache__`。新工具须明确成员策略并重新形成完整清单，不能直接把旧统计当完整SHA封存，也不能默默跳文件。
- 环境四个链接只允许精确相对路径与原始link文本；`bin/python → /usr/bin/python3` 是明确例外，仅保留链接，不复制或加载系统目标。其他外部链接、特殊文件、foreign owner及祖先链接拒绝。
- 不修改shebang、`.pth`、RUNPATH或库字节。IPC原RUNPATH仍指旧root，结果必须为 `ASSET_BYTES_COPIED_RELOCATION_PENDING`，不称独立可运行。
- 每个实际单元重新绑定fresh CPU票、host/UID/boot、指定commit/clean及源无自有活动进程；复制前核真实空间，deadline贯穿遍历、hash、copy与终态写入。失败保留partial，不自动重试，不覆盖已完成目标。
- Space仍缺其独立环境/Qwen，不能用EPD环境冒充Space准备完成；numeric36/selected360缺口保持。

NON-BLOCKING：

建议拆成三个独立受控单元：①两份dataset及单IPC库；②EPD环境；③MiniCPM模型。每个单元最多900秒并保留120秒收口，使用独立claim/证据，不给同一失败成员重新加时。23GB级数据的源前hash、复制、目标hash及源后hash涉及多遍I/O，不能仅凭容量推定单核900秒必定足够；模型单元不足时应保留断点并审查，不自动续跑。

QUESTIONS：无。

本次只读审查，没有测试、远端操作、网络、写文件或GPU动作。

GATE_RESULT: {"gate": "G1", "scope": "local_CPU_asset_materialization_tool_and_test_source_only", "decision": "APPROVE_WITH_NITS", "blocking": 0}
