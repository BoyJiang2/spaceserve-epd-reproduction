# G2 收尾helper修复复审

先读 D:/Documents/codex/AGENTS.md。按3.2.1接替尚未恢复的Claude额度；原真实失败证据和22:50重置见前次prompt。当前为22:4x。你只读审查，不改文件、不运行helper、不访问远端/GPU、不启动实验。

请复核你此前3项BLOCKING及一个计数建议的修复：
- work/package_space_7b.py：verify_sealed_batch用固定ZIP SHA锁定归档，目录manifest归一后必须等于归档内manifest；ZIP唯一完整成员集及每payload全读SHA/CRC，再核当前目录全成员SHA。兼容真实旧包root和folder-prefix两种布局。
- work/unpack_space_phase.py：destination_for拒绝反斜杠、冒号、NUL、绝对/..和非规范路径，所有传入成员在任何写入前先resolve边界验证，mkdir后写入前再验证；report和附加evidence写入也经同一边界检查。
- 四helper模块入口显式拒绝not __debug__，早于工作与依赖加载。pack另验证120/360warm和6/18cases。
- work/test_delivery_helpers.py，evidence/delivery-helper-regression.json：主执行者真实执行4个CPU回归均通过，包含实际Windows junction逃逸和两种ZIP根布局双改测试。你可读源码/证据，不自行执行。

这里只评收尾代码，正式数据仍测量中，不是G4或G5。请给结论APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号/原因/最小建议，NON-BLOCKING，QUESTIONS。回复供主执行者保存。
