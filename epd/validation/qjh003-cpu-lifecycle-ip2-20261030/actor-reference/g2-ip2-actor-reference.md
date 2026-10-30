# IP2 actor引用生命周期：独立源G2

reviewed_at_utc: 2026-10-30T03:39:46Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，仅两个文件最小源码修正。caller持有actor handle至父ACK的静态接线满足要求；不签真实Ray通过、部署、清理或新运行许可。**

精确driver `epd/runtime/numeric_cpu_driver.py` 7320B/SHA `54fd9f719649c25c08d5710e5dd2ba022c549358bfcb7d32b500980f92746ad2`；test `epd/runtime/tests/test_numeric_cpu_driver_cpu.py` 8065B/SHA `7d2709e4ae7ce651a97f2c1f64adb043eb6ee7d1d898f67d1766e0c62ca9f3ff`。本人只本地读源码/调用者/实际readback/已有日志及Git差异、计算SHA，无项目/测试执行、网络、SSH、Ray、信号或GPU，未改实现。

## 问题与最小修正

实际IP2失败readback中driver已完成连接、before_actor_create、submitted及actor_ready（266191.418762776）；约60.156ms后父GCS查询回DEAD（266191.478919132），原protobuf含“all references to the actor were removed”。这不是旧127.0.0.1连接错误，也不是没有创建WAL的失败；现失败必须按已创建actor的生命周期规则收口，不能沿用旧无创建cleanup条件。

旧scenario仅返回expected字典，函数返回时局部actor的最后强引用可被释放；main写driver-ready等待ACK时并不持有handle。真实源diff相对2d2f仅改scenario返回 `(expected,actor)`、main解包并保存这两个本地变量及必要注释，未改调度、通信、Ray hook或其它模块。

唯一生产调用者main现在 `expected,actor=scenario(...)`，在driver-ready发布、整个≤5秒ACK等待及ACK核验期间没有重绑或删除actor，选定CPython3.10执行帧的强本地引用因此保留至main返回/异常退出。父ACK合法后正常return才释放该引用，仍允许普通non_detached随driver退出结束，detached策略不变；controlled构造窗口仍在scenario帧内持有handle，不靠显式shutdown/kill修引用。没有新增全局registry、sleep延长或持久泄漏。

已搜索scenario直接调用者：生产仅main，单测调用也同步处理tuple返回；未发现旧调用者仍将整个tuple误作expected字典的运行路径。此返回值是本内部CPU诊断接口，不改变native GPU backend。

## 用例与原日志

新增weakref反例把唯一初始强引用移交实际remote creation callback，pending.pop后不另保留；调用真实scenario并gc.collect，返回值仍持有handle，删除result后weakref消失。它验证返回值传递真实强引用而非在fixture另外保留，原submission测试同时核expected及actor对象身份。main至ACK的持有由上述真实caller源接线核验，不将该scenario fixture冒称完整main/Ray生命周期实测。

before.log实际11测试、1FAIL＋1ERROR原文保留：weakref在旧实现为None，及更新tuple契约后旧实现解包错误，均针对被审变更。final-with-env.log实际summary为176测试/1.015秒/OK、0skip；该简短日志无逐项ID，本审仅按其真实summary陈述，不声称从它独立核得176唯一ID。缺EPD_CPU_TEST_TMP的前次36ERROR日志也保留，是测试环境fixture问题，不能写成修正后实现回归失败或将其删掉。

日志SHA：before `878d5c326c00a7f4a6cce23898f86ee2f3ad6013d0ab67f3c53c7006b2320aa7`；final-with-env `785c2e987e020444a22d69787f3bd4867368fbecded9aeb20ac8fc7d56ecb242`；未设环境前次 `1b7aa35102d3922b0e7e64d6b95c4dec42967e0b05c5e9e9148e8ab26b268afa`。本人未重跑任何测试。

## 边界

静态修正针对已观察到的引用释放原因成立，但不证明修订版Ray运行成功或其它生命周期阶段已过。旧run/actor已实际失败，不能热修代码恢复它或把失败转PASS；新版本须精确Git-first发布、重新物理部署及actual G3、独立新run/预约/执行G2之后才真实四场景取证。当前创建WAL、实际ActorID、GCS DEAD和PID真实状态必须在独立cleanup审查处理，源G2不授清理任何进程。

GATE_RESULT: {"gate":"G2-ip2-actor-reference-source","passed":true,"decision":"APPROVE_WITH_NITS","blocking":0,"source_sha256":"54fd9f719649c25c08d5710e5dd2ba022c549358bfcb7d32b500980f92746ad2","tests_sha256":"7d2709e4ae7ce651a97f2c1f64adb043eb6ee7d1d898f67d1766e0c62ca9f3ff","caller_handle_retained_until_ACK_source_verified":true,"actual_Ray_success_approved":false,"cleanup_approved":false,"remote_CPU_execution_approved":false,"GPU_approved":false}
