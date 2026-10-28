结论：APPROVE（明确路径修复及新producer/cohort恢复G1）
BLOCKING：0
reviewed_at_utc：2026-10-28T21:33:27Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

已只读确认correctness_suite.py:89仍从run root拼dataset，:100仍从run root拼模型路径；实际错误原件明确在读取该dataset/manifest.json时FileNotFound。新共享资产布局应通过当前冻结CONFIG.asset定位，两路径修复合理，不应建立run内资产软链接来掩盖。

批准本地最小生产路径修复与一个针对性CPU回归：验证dataset、tokenizer路径及请求图片路径均指向共享assets，run目录不含模型/dataset仍能构造原预检向量；HTTP和tokenizer实际调用使用mock，不加载模型，不改原七reference/313请求协议或负例。

实际恢复须依次：

1. 新源码G2、一次窄CPU回归及结果复核、G5/commit/push；明确原C1到新producer的源差异和新SHA。
2. 新指定runtime版本部署并核Git HEAD/clean、逐文件blob及受审源码清单；模型/env/受保护资产不变。辅助工具另记真实版本，不能把新producer重标为旧C1。
3. 新唯一真实cohort/config，排他prepare及完整CPU59实际验证，分别适用240秒工作加120秒收口、fresh CPU/API和终态监督；成功后独立实际审查，不复制旧CPU通过标记。
4. 新manifest精确numeric G2，重新执行MASK_OFF56下完整原numeric/MPS三次并实际G3；旧numeric原件可作来源，不作为新源码执行通过证据。
5. 新模型consumer/输入与代码G2后，仅一次完整313预检；按原冷启/重启、角色、服务encoder stream、并发及清理标准取得实际G3/G4。旧失败model attempt不恢复写入、不覆盖或自动重复。

旧失败run/claim/raw、已加载服务日志及清理原件保全。已有日志支持correctness首个发送前路径失败，不能把服务启动/权重加载/内部warmup称模型预检通过；0/313结论仍须保留对应请求原始记录依据。

GPU0/原UUID/boot、双预约、08:58清理与各原预算保持。formal201分钟入场最晚约05:37，不能因本次修复缩短门槛、缩矩阵或拼旧48/54；前置未及时通过则本窗只做机制预检和断点保全。本G1不授权跳过任何实际Gate，也不提前批准formal。

NON-BLOCKING：无。QUESTIONS：无。

本次仅本地只读审查及依明确请求保存本审查原文，没有执行测试、SSH、网络或GPU操作。

GATE_RESULT: {"gate":"G1","scope":"shared_asset_correctness_path_fix_new_source_CPU59_numeric_and_complete_model_preflight_subject_to_actual_Gates","decision":"APPROVE","blocking":0}
