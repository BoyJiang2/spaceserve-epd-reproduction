**最终源码G2：APPROVE，BLOCKING 0。允许一次本机7项CPU-MOCK测试。**

审查者：`/root/space2300_review`
reviewed_at_utc：`2026-10-28T14:07:04.211016+00:00`

两项阻塞已关闭：evidence创建及JSON写入核完整真实祖先；同UID进程cwd权限不明拒绝，真正退出可忽略。新增负例对应这些分支。finally在终态持久化期间忽略重复受控信号，再恢复handler，避免二次中断丢失终态。

原迁移依赖SHA仍为已审`9cf2…b405`。新增实际Git clean检查和receipt逐SHA校验；固定成员、排他目标、四链接白名单、完整源前/源后/目标清单、失败partial保留未放宽。

**本机许可：**保持以下源码字节不变，在workspace专属临时根中，仅一次运行这7项CPU-MOCK测试，保存命令、实际临时根、日志、exit及源码前后SHA。测试不调用run/executor、不网络、不GPU；Windows中O_NOFOLLOW缺失以0替代仅用于fixture，不证明Linux nofollow行为。失败保留原件，不自动重复。

**远端raw unit代码结论：**data/env/model三个固定独立unit源码通过G2；实际执行仍须本机结果复核、新G5、Git-first指定tool commit及三端源码/依赖SHA、fresh本人CPU票、boot/UID/CPU50nice10与目标不存在条件。每个unit使用独立fresh证明，300秒fresh限制持续生效，不能把900秒视为允许旧证明运行的期限。失败unit保留claim/partial，不重跑。

本批准仅raw copy，不批准环境重定位、suite、删除或GPU。cwd守卫不冒称完整FD/maps引用审计，终态仍为RELOCATION_PENDING。

绑定SHA256：

```text
materialize_assets_cpu.py
b521ccfccc423598c467802ecd4cc1258f0c90073ff226c8a759aac55bbae957
test_materialize_assets_cpu.py
f40313f65899bf9ba42d7d7c072709032fc29f54febaac1be257febb1d843bff
migrate_code_cpu.py
9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405
```

NON-BLOCKING：无。QUESTIONS：无。此次仅只读，未执行测试。

GATE_RESULT: {"gate": "G2", "decision": "APPROVE", "blocking": 0, "max_local_CPU_mock_test_units": 1, "remote_execution_requires_G5_and_fresh_admission": true}
