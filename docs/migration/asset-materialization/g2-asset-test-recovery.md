**G2测试环境恢复审查：APPROVE，BLOCKING 0。允许一次新的纠正7项CPU-MOCK测试单元。**

审查者：`/root/space2300_review`
reviewed_at_utc：`2026-10-28T14:11:18.978460+00:00`

原始失败确实发生在目标复制后inventory的fstat/lstat比较；独立诊断记录仅ctime不同，其余六字段一致。Windows fixture仅去掉最后ctime比较，保留inode、owner、mode、size、mtime及完整SHA核验，范围合理；这不证明生产Linux ctime/nofollow守卫通过。

最终绑定：

```text
materialize_assets_cpu.py
b521ccfccc423598c467802ecd4cc1258f0c90073ff226c8a759aac55bbae957
test_materialize_assets_cpu.py
c45a87e1d762b02f2e2a0871fba610219f793ce52ebaa16716e12802de49a401
migrate_code_cpu.py
9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405
```

允许仅在Windows、workspace专属临时根中执行一次纠正单元，使用新日志/回执，记录源码前后SHA及临时根终态；第一次6PASS/1ERROR原件保留。失败不得自动重复。本批准不包含WSL、远端或真实资产操作。

仅只读审查，未执行测试。

GATE_RESULT: {"gate": "G2-test-environment-recovery", "decision": "APPROVE", "blocking": 0, "max_new_local_CPU_mock_test_units": 1}
