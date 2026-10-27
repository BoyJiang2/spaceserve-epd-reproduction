# SpaceServe原始数据、报告与证据

| 批次 | 正式请求/证据 | 报告 |
|---|---|---|
| qjh000单H20/7B顺序平衡补充（48/54部分，4800正式＋960预热） | [逐请求](../../outputs/spaceserve-revision-20261027/results/formal) / [机制与终态](../../outputs/spaceserve-revision-20261027/report/publication-status.md) | [已通过部分G4的报告](../../outputs/spaceserve-revision-20261027/report/formal-terminal-reviewed-candidate/report.md) |
| qjh000单H20/7B（5400正式） | [原始记录](../../outputs/qjh000-migration/results/formal) / [完整批次](../../outputs/qjh000-migration) | [完整报告](../../docs/reading/outputs/qjh000-migration/report/space-all-report.md) |
| sapphire1 4090、sapphire3 L20/2B | [原数据目录](../../outputs/reproduction/data/raw) / [机制证据](../../outputs/reproduction/evidence) | [分主机报告](../../docs/reading/outputs/reproduction/report/sapphire-stage-report.md) |

各主机、2B/7B分别解释；encoder SM mask不等于未验证的decoder互斥分区。顺序平衡补充为独立48/54部分批次，六项缺失，不混入历史图表。

本批[完整包与trace/SHA索引（已实际下载验收）](../REVISION_ASSETS.md)；历史大trace及完整封包：[真实Release下载、大小与SHA](../../publication/ASSETS.md)。原封存和七ZIP/Release保持不变，不为目录重组重跑GPU。
