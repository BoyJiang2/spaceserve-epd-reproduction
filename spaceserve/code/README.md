# 冻结代码与复跑

最新顺序平衡补充的[实际冻结入口](../../outputs/spaceserve-revision-20261027/scripts)、[CPU分析](../../outputs/spaceserve-revision-20261027/analysis)、[版本与部署映射](../../outputs/spaceserve-revision-20261027/configs/executed-model-config-map.md)、[补丁恢复](../../outputs/spaceserve-revision-20261027/patches/README.md)单独保存；48/54部分G4通过，六项未执行。完整离线重算须恢复[本批Release-only成员](../REVISION_ASSETS.md)，历史批准不构成新GPU许可。

这里提供本项目历史批次实际执行过的脚本副本；逐文件上游路径及SHA见[来源映射](../SOURCE_FILES.json)。副本未改算法或硬编码路径，不能把换目录称已完成可移植性验证。

请先阅读[本项目完整复跑入口](../README.md)和[仓库可移植性说明](../../PORTABLE.md)。原始封包恢复到独立restore目录后，沿原批次目录结构复算；GPU启动仍须有效预约、环境/模型pin、空闲卡与通信/机制正确性。不会自动在本机启动GPU。

共享的首轮环境、压测、数据准备及审计脚本保留在[原路径](../../outputs/reproduction/scripts)，未因项目拆页移动或改写。模型权重、Python环境和缓存不在仓库。


新增[H20指定commit部署候选](h20-window-20261027/README.md)按本地→审查→GitHub→指定commit部署执行；代码发布不等于新模型或54单元验收，旧48/54保持独立。
