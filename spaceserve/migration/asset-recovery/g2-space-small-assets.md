**小素材恢复源码G2：APPROVE，BLOCKING 0。允许一次4项CPU-MOCK测试。**

审查者：`/root/space2300_review`
reviewed_at_utc：`2026-10-28T15:00:50.260345+00:00`

固定八成员、payload字段及现行pin先全部核验，再检查全部目标不存在，随后独占evidence及逐文件排他写入；完整祖先检查、fsync和实际SHA核验保持。60秒deadline、fresh证明、固定boot/UID/a3f及Git clean检查未放宽；失败保留partial，不自动重试。没有下载、模型加载或旧源修改。

四项测试设计覆盖成员闭包/越界、bytes/SHA/pin拒绝、排他写入与链接祖先拒绝；不调用main或远端executor。允许workspace专属临时根中一次执行，保存实际命令、日志、exit、前后SHA及temp终态。未实际运行，不预称通过。

绑定SHA256：

```text
restore_space_small_cpu.py
25f4756eeb8b9f547503c98ff719e8974036de5e8bf812892a84653d26d83a7f
test_restore_space_small_cpu.py
1156810bbba8215065b0a788ae9c512a3e0453928be6102e829d471cd5b222ea
migrate_code_cpu.py
9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405
```

实际八素材上传仍待测试结果复核、G5/push、三端字节和具体wrapper/argv补审及fresh现场准入。成功仅八素材，不代表CPU_STAGED、资产整套可用或GPU通过。此次没有加入PAM/SSH白名单，原资产工具审批不混用。

NON-BLOCKING：无。QUESTIONS：无。仅只读审查，未测试或访问外部。

GATE_RESULT: {"gate": "G2-small-assets", "decision": "APPROVE", "blocking": 0, "max_local_CPU_mock_test_units": 1}
