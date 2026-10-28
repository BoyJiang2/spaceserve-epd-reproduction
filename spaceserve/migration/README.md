# qjh003 固定目录迁移：准备状态

代码已分别发布；[共同CPU部署准备与本机5项工具测试](../../docs/migration/README.md)单独记录，尚未在qjh003部署或迁移资产。

Space 固定源码已收敛到 [`spaceserve/runtime`](../runtime/README.md)，独立 G2 APPROVE / BLOCKING 0。源快照85项、冻结索引80项；仅静态语法检查，**本次 CPU 测试未执行、尚未部署、尚未迁移资产、没有新 GPU 或性能结果**。

最终根 `/local/boyjiang/spaceserve/` 下分为 repo、assets、runs、staging、archives。EPD 独立使用 `/local/boyjiang/epd/`，当前仍在重构；Space 本次通过不覆盖 EPD。模型/环境/缓存不进入Git，真实独立run只冻结少量源码与两份实验库。旧 qjh000 根保护，目标SHA/环境验收之前不清理。

本人 qjh003 CPU/GPU 预约是北京时间2026-10-28 21:00至次日09:00；19:14只读API复核之前CPU/GPU仍由其他用户预约。不能提前部署或测试。旧 qjh000 三个应用自动任务已暂停，不借旧票启动。

模型、数据、精度和请求预算不变：单H20/Qwen2-VL-7B，三组54单元；新主机驱动/boot/UUID/NUMA/环境和CUDA机制必须实际验证，禁止继承旧G3。运行先满足指定commit/Git逐SHA、fresh本人资源、实际CPU零失败零skip及独立复核，再依阶段授权推进。旧12/87/313和48/54原件及实际来源均保留。

来源是 [ecad958 的真实历史源码](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/ecad958fdc9f09f8f3d39e3eef7c08d43db634df/spaceserve/code/h20-window-20261028)，不把本次重构版本重标为旧运行producer。被移除的main重复清单、生成器和旧review仍可在该commit读到；封存raw、七ZIP、四Release13资产不修改。

- [本地重构G1](g1-refactor-result.md)
- [Space固定快照G2原文](g2-space-refactor-final.md)
- [85项审查源SHA](space-refactor-source-review-snapshot.json)
- [唯一运行入口与复跑阶段](../runtime/README.md)
- [既有CPU准备实际记录](../preparation-20261028-2300/README.md)
- [既有实际baseline及退化对照](../comparison/README.md)
