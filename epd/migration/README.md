最新CPU迁移：EPD环境6,866,027,252B、MiniCPM16,210,140,997B、数据集和IPC库原字节已复制，[独立完整性审查](../../docs/migration/asset-bytes-audit.md)通过。仅RELOCATION_PENDING；库平铺路径和旧RUNPATH/环境入口待处理，未过目标suite/GPU，不删除旧源。

# EPD 固定目录迁移准备

代码已分别发布；[共同CPU部署准备与本机5项工具测试](../../docs/migration/README.md)单独记录，尚未在qjh003部署或迁移资产。

唯一维护源码已收敛到 [`epd/runtime`](../runtime/README.md)。本次62项源快照经独立 G2 APPROVE / BLOCKING 0，**测试实际0、尚未部署/迁移、GPU实际0**。旧87项实际CPU验证的来源仍为f1ff073，不能覆盖本次新路径与组件。

固定根 `/local/boyjiang/epd/` 下：repo为Git源码、assets为环境/模型/图片/IPC库、runs/cohort为真实批次证据与原始claim。source/Git与执行归属根分离；每cohort共享总账本，不因换unit重置预算；跨Space/EPD主机锁不是预约权。

本次只收敛代码/配置/入口与CPU测试设计。native36与selected360 controller仍未接齐，入口在硬件或claim前拒绝，因此公平三副本/PD/EPD正式比较仍未完成，不新增性能结论。

qjh003本人CPU/GPU票均北京时间2026-10-28 21:00至次日09:00，之前属于他人；先审查/发布，再开窗fresh核验与指定commit部署。目标资产未验收前保护qjh000原件，旧四批/七ZIP/四Release13资产不变。

- [实际来源与复跑/候选限制](../runtime/README.md)
- [本地目录重构G1](g1-refactor-result.md)
- [本次G2原文](g2-epd-refactor-final.md)
- [62项源码审查SHA](epd-refactor-source-review-snapshot.json)
- [旧87 CPU真实结果与来源](../validation/qjh000-cpu-20261028/README.md)
- [既有三卡baseline完整收益/退化对照](../comparison/README.md)

历史源代码和已封存原始数据继续按各自真实commit复跑；本次候选不能替代旧运行producer或复用旧机G3。
