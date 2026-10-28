结论：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-28T14:56:18Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

本次G1绑定清单SHA256 `21e51ba73f5eec0bb03ca983169fca4f5c5dbe1fd286042e67f74c2bf8f4397d`。八份本地源文件重新计算bytes/SHA，全部精确匹配当前protected pins，合计2,710,088字节；目标均为指定Space assets相对位置。本地源及祖先未发现symlink/junction，旧partial不在清单中。

批准：

- 编写最小一次性传输工具及负例测试源码。
- 经独立G2、测试结果复核、G5/Git-first发布及三端字节核验后，在fresh qjh003 CPU准入满足时执行一次该八文件复制。

实际执行须保持8MiB payload上限、60秒工作加120秒收口、API300秒及预约结束前120秒边界、CPU50/nice10、指定boot/UID、至少4GiB空间；所有目标在首次写入前确认不存在。目标排他创建，拒绝链接及异常祖先；源传前传后SHA、实际payload与目标SHA分别保留。首个失败停止，保留claim/partial/原始终态，不覆盖、不自动重试。

metadata直接复制当前原字节，不转换或重新生成。成功仅说明八份受保护小资产的字节落地，不创建CPU_STAGED，不证明Space环境、完整Qwen权重、库兼容性或GPU机制通过。下载、环境安装及剩余模型获取另审。

NON-BLOCKING：无。
QUESTIONS：无。

本次只读检查，没有实际复制、测试、网络、SSH或GPU操作。

GATE_RESULT: {"gate": "G1", "candidate_sha256": "21e51ba73f5eec0bb03ca983169fca4f5c5dbe1fd286042e67f74c2bf8f4397d", "scope": "eight_exact_pinned_Space_small_assets_tool_and_one_conditional_copy", "decision": "APPROVE", "blocking": 0}
