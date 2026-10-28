**窄恢复G2：APPROVE，BLOCKING 0。允许一次新9项CPU-MOCK测试单元。**

审查者：`/root/space2300_review`
reviewed_at_utc：`2026-10-28T14:26:17.058192+00:00`

例外仅适用于指定boot、PID2565254及其固定systemd父身份；两次实时快照须与全部固定字段相等。其他PID不获豁免，任何字段变化、读取失败或可读cwd属于项目仍拒绝。匹配快照及SHA进入claim，未增加信号或服务清理操作。

新增测试覆盖逐字段错值、第二读变化、非指定PID、例外记录及可读项目cwd拒绝。原失败检查记录三目标和evidence均不存在，符合单次恢复而非覆盖partial的前提；执行前仍须fresh复核。

绑定：

```text
materialize_assets_cpu.py
6cc17ff2dc27abdf2b4681c82a8e3655b221000ff3fe20d41edf0df7cca45b35
test_materialize_assets_cpu.py
0bf92476339f6087096ba5c44ac2aa15fd967c3a28ce32ba6ef12449e6beea07
migrate_code_cpu.py
9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405
```

允许在workspace专属临时根一次执行该9项Windows CPU-MOCK，使用独立日志/回执，记录前后SHA及temp终态；旧失败原件保留。实际data恢复仍待结果复核、G5/push、三端字节核验和更新wrapper补审；env/model未启动，不由此自动执行。无GPU、重定位或删除许可。

仅只读审查，未运行测试。

GATE_RESULT: {"gate": "G2-PAM-exception-recovery", "decision": "APPROVE", "blocking": 0, "max_new_local_CPU_mock_test_units": 1}
