# G2 传输重试复审

/root/profile_instrument_review 原文，主agent落盘。

G2 复审：**APPROVE，BLOCKING 0，NONBLOCKING 0**。

B1 已关闭：先保留原始绝对路径，从 `WORKSPACE/work` 逐层拒绝链接，再检查新旧 holding 双向不包含；均在创建目录前完成。新增反例覆盖旧目录子路径和模拟链接祖先，既有保全与 SHA 校验未放宽。

仅批准传输重试准备工具，不代表实际下载或 G4 通过。本次未执行代码、联网或改文件。
