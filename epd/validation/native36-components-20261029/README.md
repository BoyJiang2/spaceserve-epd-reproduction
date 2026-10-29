# Native36后端准备组件：尚无新GPU结果

本分支增量发布已独立审查的三个准备组件及CPU模拟测试。**完整后端、collector、监督器/driver接线和生产numeric分派仍未完成，不能运行native36，也没有新增PD/EPD性能结论。** 不替代旧实际CPU87/旧numeric24测试或GPU Gate。

| 组件 | 代码 | 本地验证 | 范围 |
|---|---|---|---|
| numeric身份 | [production_identity.py](../../runtime/production_identity.py) | 6新增＋9原HTTP=15 CPU-MOCK PASS | gcs loopback身份、禁伪HTTP回执；真实owned-head绑定仍由后端落实 |
| 释放核心 | [numeric_release.py](../../runtime/numeric_release.py) | 15 CPU-MOCK PASS | importer→exporter依赖、fsync记录、pidfd、真实proc目录和NVML联合退出条件 |
| head构造 | [numeric_head.py](../../runtime/numeric_head.py) | 10 CPU-MOCK PASS | Ray2.10源码固定、禁自动全杀、部分失败保留；信号只记取消、登记后传播 |

以上共40个不同测试，均为Windows注入模拟；未启动实际Ray/进程、未发送真实信号、未初始化NVML/Torch/CUDA。head测试的假路径仅为字符串，不创建系统根目录。真实Linux/Ray/POSIX和CUDA释放仍需独立Gate。全部源码SHA见[SOURCE_SHA256.json](SOURCE_SHA256.json)，使用本分支实际Git commit定位版本，不把开发基点当运行版本。

## 审查与失败记录

- [身份G2](reviews/g2-numeric-identity.md)、[释放最终精确G2](reviews/g2-numeric-release-core-final-delta.md)、[head G1/G2复审及fixture补审](reviews/g1-g2-numeric-head-core-v2.md)。
- 释放初审发现裸PID信号复用、cwd/environ缺失误当进程消失：[初审](reviews/g2-numeric-release-core.md)。修为稳定pidfd、发送前期限复核、独立proc目录观察，旧审查和结果保留。
- head初审发现只屏蔽主线程不能防后台线程信号：[初审](reviews/g2-numeric-head-core.md)。[旧源码确定性反例](logs/numeric-head-background-regression-before.log)真实失败（child已创建、registry为空），修复后[10项结果](logs/numeric-head-cpu-tests-final.log)通过。当前实现不用新增信号屏蔽，保留官方Ray child政策。
- [身份首轮14PASS/1ERROR](logs/numeric-identity-cpu-tests.log)来自测试launcher模拟UID与Windows文件UID冲突；仅修launcher后[15PASS](logs/numeric-identity-cpu-tests-v2.log)，生产归属校验未放宽。[释放15项原件](logs/numeric-release-cpu-tests-v4.log)与[旧9项原件](logs/numeric-release-cpu-tests.log)分别保留。

## 后续与复验

[完整设计v2](plans/numeric-production-backend-plan-v2.md)、[直接Node补充v3](plans/numeric-head-node-amendment-v3.md)中的信号屏蔽方案由head复审的协作式取消实现取代，其余预算/失败边界不变。官方Ray源码固定于ray-2.10.0：[Node](https://github.com/ray-project/ray/blob/ray-2.10.0/python/ray/_private/node.py)、[services](https://github.com/ray-project/ray/blob/ray-2.10.0/python/ray/_private/services.py)、[RayParams](https://github.com/ray-project/ray/blob/ray-2.10.0/python/ray/_private/parameter.py)；运行时逐源码SHA核对，不能换版本猜接口。

CPU模拟按[测试源码](../../runtime/tests/)运行，需要先设置EPD_CPU_TEST_TMP为自有可写临时目录；Windows原HTTP测试需要将os.getuid模拟为该临时目录stat.st_uid（只在测试launcher内）。分别执行unittest discover的test_numeric_identity_cpu.py、test_numeric_release_cpu.py、test_numeric_head_cpu.py及test_production_identity.py。模拟结果不证明真实Linux可用；实际运行入口仍按[固定项目流程](../../runtime/README.md)和完整审查。

MiniCPM-V-2_6/FP16/TP1、三卡65%、36完整原生传输、0模型请求、1800秒含120收口/总340分钟及零重试不变。失败或释放未确认必须保留并停止，不借无限retain延期。后续还需完整supervisor/driver/collector/固定入口、真实生命周期Gate、numeric36、资格/校准/selected360及公平性能矩阵。

本次仅代码/CPU证据增量，不改旧实验、ZIP或Release。SpaceServe仍先运行，GPU正式测量不并行。[返回EPD独立项目及历史baseline](../../README.md) · [baseline对照](../../comparison/README.md)
