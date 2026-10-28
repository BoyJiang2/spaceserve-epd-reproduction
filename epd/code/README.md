# 冻结代码与复跑

历史批次目录提供本项目实际执行过的脚本副本；逐文件上游路径及SHA见[来源映射](../SOURCE_FILES.json)。历史副本未改算法或硬编码路径，不能把换目录称已完成可移植性验证。

新增公平PD工作请先读[未运行候选说明](../plans/fair-pd-20261027/README.md)，其中列出独立源码SHA、审查及剩余条件；[冻结源码目录](fair-pd-candidate-20261027/)不属于上述历史执行证据。源码内继承的README仅作上游参考，其引用的上游assets未随本候选发布。

最新的身份/路由桥接与本次 qjh000 CPU 验证入口见[v11 说明](../plans/fair-pd-20261027-v11/README.md)及[51 项源码](fair-pd-candidate-20261027-v11/)。目标 CPU 已实际76 PASS，原件见[独立CPU验证批次](../validation/qjh000-cpu-20261027/README.md)；真实GPU/模型与性能仍未验证。2026-10-28 的 v13 候选见[v13 说明](../plans/fair-pd-20261028-v13/README.md)及[54 项源码](fair-pd-candidate-20261028-v13/)，目标 CPU 已实际 87 PASS，原件见[该批次](../validation/qjh000-cpu-20261028/README.md)；真实 GPU/模型与性能仍未验证。

请先阅读[本项目完整复跑入口](../README.md)和[仓库可移植性说明](../../PORTABLE.md)。原始封包恢复到独立restore目录后，沿原批次目录结构复算；GPU启动仍须有效预约、环境/模型pin、空闲卡与通信/机制正确性。不会自动在本机启动GPU。

共享的首轮环境、压测、数据准备及审计脚本保留在[原路径](../../outputs/reproduction/scripts)，未因项目拆页移动或改写。模型权重、Python环境和缓存不在仓库。
