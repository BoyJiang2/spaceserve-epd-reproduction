# Space只读远端验收client复审

/root/profile_instrument_review：**APPROVE，BLOCKING 0，NONBLOCKING 0**。

B1/B2 已关闭：固定两资产名称后，逐个拒绝 symlink、核实际 size 和流式 SHA256；输出显式拒绝 symlink，并用 `open('x')` 原子创建。其余绑定与既有 Release 保护保留。

仅批准验收代码，不代表实际远端验收通过。本次未执行、导入、联网或改文件。
