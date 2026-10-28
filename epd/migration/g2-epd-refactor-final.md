结论：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-28T11:29:30Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

本次窄G2复审绑定更新后的62项快照，SHA256 `42cd8a4837a96c9ef7b78ab0c227a5f1cc5db8b597c627826b3e66986e6e6853`。全部成员bytes/SHA重新计算一致。仅只读审查，未运行测试、网络、SSH、GPU或写文件。

原两项阻塞已关闭：

1. controller预约测试现提供独立临时layout、host锁与真实phase模板，明确patch `controller.paths_for`，并包装真实booking_for_unit、断言调用一次。六个异常分支要求NVML/Claim未构造；有效预约正对照只允许到抛出CPU-MOCK哨兵的backend factory。测试不再因candidate路径检查而提前“通过”。

2. CPU源码核验现要求必需准入/shared成员，校验安全logical/git_path映射及去重，并与完整tracked项目/common集合比较；同时核实际加载的runner、project_config、preflight_guard、admission和共享ProjectLayout源码字节。冻结cohort source commit/manifest与permit证据也显式一致。新增CPUClosure测试覆盖漏共享/依赖及修改副本后同步伪换pin的拒绝情景。

旧qjh000测试名称已调整；未在此次修改中发现可明确判定的新Linux运行失败。此判断是静态检查，不代表套件实际通过。

NON-BLOCKING：无新增项。
QUESTIONS：无。

批准范围仅为该固定快照的EPD代码与CPU测试设计。实际测试仍为0；numeric36/selected360入口继续未接齐并拒绝。远端运输、部署、CPU执行及GPU操作须分别满足相应资源、指定commit与审查条件，旧87项PASS不覆盖本次变更。

GATE_RESULT: {"gate": "G2", "snapshot_sha256": "42cd8a4837a96c9ef7b78ab0c227a5f1cc5db8b597c627826b3e66986e6e6853", "decision": "APPROVE", "blocking": 0}
