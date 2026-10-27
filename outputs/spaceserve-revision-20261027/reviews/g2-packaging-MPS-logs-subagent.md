# G2 打包纳入两份实际MPS日志

/root/profile_instrument_review 原文：**APPROVE，BLOCKING 0，NONBLOCKING 0**。

规则仅新增 `logs/mps/control.log` 和 `logs/mps/server.log` 两个精确相对路径，未开放整个 logs 目录。新增测试覆盖两者允许、`other.log` 在创建输出前拒绝；后续扫描、压缩及 SHA 校验流程保留。

仅批准此打包增量，实际候选仍须 G5。本次未执行代码、联网或改文件。

实际首次打包在输出创建前拒绝unclassified source path logs/mps/control.log，未生成包；此增量保留全量取证两日志，没有省略失败原件。九CPU测试PASS，后续实际包另核。
