# G2 v7 — original independent response

Reviewer: /root/profile_instrument_review. Primary saved original response.

G2 v7：**REQUEST_CHANGES，BLOCKING 1**。审查时间：**2026-10-27T10:37:35Z**。

已核对 v6→v7 仅两个文件变化，实际字节匹配 manifest；manifest、delta patch、UNEXECUTED receipt SHA均与提供值一致。未执行测试、编译或 patch apply。

**B1：启动期间收到信号，仍可能遗漏已创建的子进程。**

- `cpu_target_runner.py:306–308`的 handler 直接抛异常。
- `:318`在 `Popen(...)`返回前，子进程可能已经创建，但局部变量 `process`仍为 `None`。此时 TERM/INT会跳入 finally，`:336`跳过子进程清理；`:354`甚至可能因空清理集合将 `cleanup_confirmed`记为 true。
- 新回归的 `test_cpu_target_runner.py:108–116`也在返回 Popen 对象前写 ready，因此存在同一竞态，不能稳定证明该边界已关闭。

**最小修复：**启动及身份绑定期间 handler只记录信号，不抛异常；取得 Popen对象与身份后再进入统一停止路径。增加确定性回归：真实子进程创建后、Popen wrapper返回前触发 TERM/INT，断言实际清理与回执正确。无法确认身份时保持 unconfirmed，不能使用空集合推断已释放。

其余改进成立：等待异常进入 finally、清理拒绝未知身份、僵尸未回收不冒称释放、nice10设验记录，以及 commit/permit/parent/argv保留。

仍仅审代码候选；目标CPU未验证，handoff用户确认及旧 final_release 缺口未关闭，不授予远程执行、GPU或发布许可。

## Disposition

Accepted; implementation agent assigned minimal immutable v8. No execution. No disagreement with review; remaining launch race must be closed before approval.

