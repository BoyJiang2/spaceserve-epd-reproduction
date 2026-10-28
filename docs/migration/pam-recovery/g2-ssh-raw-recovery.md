**SSH身份例外窄G2：APPROVE，BLOCKING 0。允许一次新10项CPU-MOCK测试单元。**

审查者：`/root/space2300_review`
reviewed_at_utc：`2026-10-28T14:38:37.560737+00:00`

新增例外与所述窄G1一致：仅UID2147的sshd子进程、固定cmdline SHA、完整数字session cgroup，且直属root父进程链连接到指定boot下固定daemon7347。child/parent/daemon全部记录前后两读相等后才豁免；其他未知身份仍拒绝，可读项目cwd不豁免，不发送信号。匹配原件及SHA仍进入claim。

新测试覆盖anchor各字段、UID/command/cgroup异常、boot、二读startticks变化及消失拒绝；原未知权限测试明确保持拒绝语义。两个旧失败和当前目标不存在记录应继续保留，不能改成成功。

绑定SHA256：

```text
materialize_assets_cpu.py
8ffccf7061b2ebc8ac90543d0d60c79efaf7ff87552cef8fcf1bd6555dbd0c0c
test_materialize_assets_cpu.py
4cc8128531a7f39b5ac7f75b5f89f47b60ff717834f9139f61b1b81838418af4
migrate_code_cpu.py
9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405
```

允许workspace专属临时根的一次10项Windows CPU-MOCK，独立保存日志/exit/前后SHA/temp终态；失败不自动重复。实际下一次data条件恢复及env/model首次启动仍须结果复核、新G5/public push、三端源码和更新wrapper核验、每unit fresh准入与目标排他条件。此前批准不能替代这些步骤；不授GPU、删除或环境重定位许可。

仅只读审查，未执行测试或远端操作。

GATE_RESULT: {"gate": "G2-SSH-identity-exception", "decision": "APPROVE", "blocking": 0, "max_new_local_CPU_mock_test_units": 1}
