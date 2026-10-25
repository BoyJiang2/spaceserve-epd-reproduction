> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g1-subagent.md) SHA256 f63fdcc6bea2da23cccf357f7b0024fa7d2110607c47267662e94d8054b3fc3a。原数字及解释不变。

# G1迁移审查

实际审查者：`/root/profile_plan_review`，Claude本阶段明确额度耗尽接替，独立只读，无GPU/实验。

首审REQUEST_CHANGES、1项B1认为根盘与旧存储边界冲突；root提供最新goal中“数据盘不足时允许使用其他空间充足的可写专属目录”的实际用户授权并同步AGENTS后复审。

复审APPROVE_WITH_NITS，B1关闭，BLOCKING0。审查者说明首审授权信息不完整，现已纠正，无需重复向用户确认本次目录。允许资产复制与环境准备，不是000新脚本/MPS/兼容性G2/G3。

认可003原正式数据不重跑且保留原主机/驱动，不拼接；005待000环境可用后按明确身份停自有准备，迁移期间撤旧GPU marker；固定版本需实际兼容性验证；先两点各可用组再G4扩展，SM第三组依据原生及实际stream机制证据，与性能无关。

NONBLOCKING执行项：核实/var/tmp清理策略，至少180GiB空闲和700权限运行前复查；每完成case及时同步本地与SHA，不把磁盘持久当目录永不清理。003统计G2三项及G4/G5仍须完成。
