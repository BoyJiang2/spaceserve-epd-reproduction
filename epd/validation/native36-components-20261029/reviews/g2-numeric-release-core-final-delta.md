# G2 NumericRelease 最终小增量精确审查

审查者 `/root/epd_pd_followup`；UTC 2026-10-29T07:25:29Z。

**APPROVE / BLOCKING 0。** 本结论针对最新两源码，初审及`g2-numeric-release-core-v2.md`原件不改；不以旧a1eb/54d覆盖最新版本。

| 对象 | 本轮实际 SHA256 |
|---|---|
| checkout/epd/runtime/numeric_release.py | 3a80d84e5340457ac07d0984065eee6510021bb615877be0ccbad9b93878c40a |
| checkout/epd/runtime/tests/test_numeric_release_cpu.py | 5af079b4931fa036e9b9ba398a504d6af5dc95eb42656e743ac188c2611eedc6 |
| numeric-release-cpu-tests-v4.log | cecdef8d87c976e78b20f5f5e5d0a68d6f75d5647ea40d1dc311a18bc06263f8 |

只读核实增量：

- 身份lookup的FileNotFound原始repr与准确/proc目录exists/boot/monotonic记录进`proc_identity_lookup_failed` WAL，然后按目录实际是否存在拒绝或继续；不把子文件缺失当原进程消失。日志失败仍抛异常，不伪称释放。
- B2 fixture显式令NVML空processes/used=0且/proc仍存在，分别模拟identity与environment子项缺失，要求未加入released、exporter仍被Importer依赖阻断、无信号。覆盖了初审危险条件。
- 新adapter测试调用真实NumericProc方法、mock底层三API，精确核`os.pidfd_open(123,0)`、`signal.pidfd_send_signal(42,SIGTERM,None,0)`、`os.close(42)`，并断言`os.kill`未调用。生产adapter本身仍无裸PID fallback，前轮pidfd绑定/截止检查不变。
- v4日志实际15项CPU-MOCK、0.183s、OK；本审没有运行测试。旧9/13/14项日志保留，不能用它们替代本15项原件；底层API被mock仍不证明目标Linux pidfd权限/内核或真实信号行为。

仅release核心认可。独立supervisor/Node与daemon归属、driver死亡接管、mapping WAL到copy提交的确认协议、完整native36入口与真实Ray/POSIX/NVML/CUDA Gate仍待接线和独立核验。未执行测试/编译/网络/远端/GPU，未改实现，未commit/push；Space730/main/bundle冻结保持。
