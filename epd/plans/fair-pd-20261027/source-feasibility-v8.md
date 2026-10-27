# v8：最小启动信号竞态修复，UNEXECUTED

v7独立G2 REQUEST_CHANGES/BLOCKING1，reviewed UTC 2026-10-27T10:37:35Z。完整peer原文由主线程另存reviews/g2-v7-original-profile-instrument-review.md，本实现者不修改；reviews/g2-v7-relayed-task-summary.md仅任务摘要。

只改cpu_target_runner.py和tests/test_cpu_target_runner.py。启动/Popen返回/身份绑定阶段handler只暂存TERM/INT，不抛异常；取得对象并完成身份观察后转入原统一停止/finally路径。若信号在真正启动前到达则不启动。正常wait阶段保留原中断行为。cleanup_confirmed必须有Popen对象及非空、均已确认的cleanup，不能all(empty)推断released；未知身份仍unconfirmed并拒杀。

新增确定性真实POSIX测试源码：worker/helper已创建、Popen wrapper尚未返回时停在显式barrier；发送TERM或INT，验证parent暂不退出且worker仍是原身份，再释放barrier，检查取得对象后进入清理并保存终态。这些测试未执行，不是即时fake通过。已有wait exception/finally/nice10/commit缓存逻辑不扩展。

v1–v7原件不变，v8无tests/语法/编译/patch检查，无remote/network/GPU/预约/push。CPU交接仍pending，无新增执行许可；SIGKILL父进程仍不保证，formal与实际controller接线继续blocked。等待独立复审及合法remote CPU，不降低资源/时间门槛。
