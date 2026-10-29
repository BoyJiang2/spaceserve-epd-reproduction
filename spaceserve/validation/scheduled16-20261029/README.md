# qjh003 16点候选准备

本批采用用户明确的“等到16点如果显存占用是0 你就开始”。这是待执行的源码与CPU准备路径，不是新的性能结果；正式矩阵仍为0/54，新GPU2的数值与313模型实际验收尚未执行。

`tools/control_space_temporary_cpu.py <phase> --scheduled-cpu`依次使用
`transfer-recovery`、`deploy-recovery`、`prepare`、`cpu`。控制器读取工作区
`outputs/migration-qjh003/space-16-config.json`和原始用户指令，先核真实GitHub main与源码字节/Git blob，再在CPU50/nice10执行每个完整240+120秒单元。

新候选固定`space-16-20261029`、GPU2 UUID c005、同NUMA0逻辑CPU0–89/OMP4、原模型及mask候选56；配置状态candidate、allowed_actions空、booking空，不能启动GPU阶段。目标CPU时段为北京时间16:00–16:20，实际其他CPU或整机预约冲突时拒绝。四个单元的最坏预算超过20分钟，因此每步必须重新满足完整预算，不能保证完成。

源码通过独立G2；12项本地CPU模拟测试通过，含时段、冲突、候选配置、旧失败与bundle恢复闭包。模拟不等于实际Linux冻结/CPU suite，更不等于GPU G3。此前HTTPS部署失败原件保留在[上一批](../temporary-idle-gpu2-20261029/README.md)。本路径只恢复源码，不重复模型资产下载。

16点须实际重核GPU2显存严格0MiB、compute空、身份/NUMA与预约。实际CPU成功后，仍须冻结经审查的GPU授权配置、新numeric实际G3、完整313模型实际G3；正式54的201分钟入场条件不变。未验证decoder互斥分区，不能称完整SM分区。
