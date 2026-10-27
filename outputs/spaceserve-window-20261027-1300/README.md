# SpaceServe H20：313请求预检批次

本批三组模型/机制预检已通过独立G3，报告通过G4；**正式0/54，完整性能目标未完成**。这不是旧48/54的补齐，也不是EPD实验。

| 项目 | 实际状态 |
|---|---|
| 代码 | runtime Git `83edff6608fc9db33ea90c3d04ce091705ee643f`；独立collector Git `6a9dd8c58231a82d0be498b832c85b5ccac7ab35` |
| 正确性/诊断 | 7 reference＋90 target＋216 diagnostic＝313；cold/restart各三组 |
| encoder机制 | 解耦独立encoder；mask实际严格78→64，可撤销/重施；不能称decoder互斥 |
| 原件 | 261项、384,109,378字节、10trace已本地SHA核验；G3冻结496项绑定 |
| 正式性能 | 未启动；没有新吞吐/TTFT/TPOT/E2E/显存/失败率对照数据 |
| 发布 | 两个代码commit已GitHub核验；本批报告/原件完整封包及Release尚待发布G5与实际上传核验，不宣称交付完成 |

- [可读报告及三组机制对照](report/preflight-report.md)
- [独立模型G3全文](reviews/g3-model-preflight-subagent.md)、[G4报告审查](reviews/g4-preflight-report-subagent.md)
- [实际运行与退出](evidence/models-attempt1-exit.json)、[资源释放](evidence/model-attempt1-terminal.json)
- [原件清单](evidence/model-attempt1-files.json)、[本地SHA核验](evidence/model-transfer-local-verified.json)、[冻结G3 Gate](evidence/G3_MODELS_APPROVED.json)
- [新目录数据/集成源副本与实际pin关系](evidence/model-frozen-data-source-mapping.json)

[既有48/54 baseline性能对照](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/4500d059988eb5e7ffb4e352d5f7319d83290958/spaceserve/comparison)保持独立。源码启动入口必须配合真实预约、精确版本及新阶段审批；本批G3不授予新GPU或formal权限。

报告末尾“待G4”为受审候选原文，实际G4已通过，见上方审查文件；保留原报告字节以便核验。完整性能矩阵与后续EPD/公平PD仍需各自完成、审查与发布。
