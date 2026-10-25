> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-final-delivery-helpers-subagent.md) SHA256 530febba84f525bf133d05f6fc59dc0a2ca4aa3671d76bb2402a458f4c9de56a。原数字及解释不变。

# G2 收尾helper预审

实际审查者：独立只读 subagent `/root/profile_runner_review`。Claude usage_limit_reached 实际证据见本批提示所引 EPD review JSON；审查时尚未到22:50重置时间。主执行者保存原结论，未让审查者运行helper、访问远端/GPU或修改文件。

结论：REQUEST_CHANGES，3项BLOCKING。

1. `work/package_space_7b.py:38-50`：旧目录未绑定固定旧ZIP；旧payload与SHA256SUMS一起变更仍可能通过。应绑定固定ZIP内清单并核对归档payload与当前目录，增加双改仍拒绝的CPU用例。
2. `work/unpack_space_phase.py:40-58`：PurePosixPath检查后交给Windows Path，反斜杠、drive片段和已有目录链接可能逃逸。应拒绝Windows危险路径并在写入前证明resolve位于target内。
3. 四个helper关键验证依赖assert，`python -O`可禁用。入口应拒绝优化模式或改显式异常。

NON-BLOCKING：pack应明确检查points/all预热120/360和配置6/18。最终ZIP逐成员全读CRC/SHA、唯一集合、源postpack及外置ZIP哈希设计合理。metadata正常路径只在真实结束后新增只读检查证据。

本结论不是最终数据、归档完整性或G5批准。正式计时期间不得运行收尾helper。

主执行者处理：三项均已本地修复，且采纳NON-BLOCKING计数检查。4个CPU回归通过（含两种ZIP根布局的payload+manifest双改拒绝、Windows路径、真实junction逃逸拒绝、四入口-O拒绝）。证据 `evidence/delivery-helper-regression.json`，源码 `work/test_delivery_helpers.py`。尚待同范围复审；未上传运行收尾helper，远端冻结实验源码不变。
