# 公平 PD 基线：未运行的代码候选 v8

本目录属于 EPD 项目。**没有新增性能或模型正确性结果；v8 的 CPU 测试、编译、补丁应用和 GPU 测试均未执行。** 独立 G2 仅批准代码候选，不是可直接启动的实验包。

源码目录继承的 README 仅作上游参考，其中引用的上游 assets 未随本候选发布；候选状态与操作边界以本页为入口。冻结源码字节不因展示调整而修改。

目标是在同模型、精度、三张 H20 总预算、输入输出及缓存条件下，对照三个完整副本、合理调优的 E+P 融合/D 独立路径和 E/P/D 独立路径。内部融合实现称为“PD 消融基线”，不称 DistServe 实测。旧方案 A 和 53/60 批次结果保持独立。

- [49 项冻结源码](../../code/fair-pd-candidate-20261027/)、[源文件 SHA256 清单](source-manifest-v8.json)。清单 manifest 的 SHA256 为 `6cdcda3423ea7f0c88e0bc298aa25622c6602868a43be3ef0961909cf9857f07`；文件路径相对于该源码目录。
- [未执行记录](cpu-receipt-v8-unexecuted.json)、[独立 G2 v8 原文](reviews/g2-v8-original-profile-instrument-review.md)。旧版本的 CPU PASS 不能作为 v8 的验证结果。
- [候选计划](plan-v8.md)、[预算](budget-v8.json)、[实现范围与缺口](source-feasibility-v8.md)、[完整补丁](epd-pd-followup-v8.patch)、[启动竞态修复差异](epd-pd-v7-to-v8.patch)。计划中的原本地工作路径是来源记录，部署时以 Git 指定 commit 的源码目录与逐 SHA 清单为准。

本次仅发布源代码供后续从 Git 部署验证。CPU runner 固定到 2026-10-27 的条件窗口；CPU50 项目交接仍未确认、旧项目最终释放回执缺失，因此没有执行。不能把这个入口用于其他日期或绕过资源归属核验。后续窗口须更新并重新审查对应配置。

仍缺实际生产 worker/endpoint 适配、完整受控启动链路、合法目标 CPU 验证，以及新 GPU 资源与冻结预算确认。候选首阶段的 1440 模型请求/340 分钟不构成执行许可；正式性能矩阵也未授权。完成前述条件和适用 G1–G5 后才开展实验。源码运行期间冻结，环境、权重、缓存和凭据不在本次发布中。

[返回 EPD 项目及既有 baseline 对照](../../README.md) · [既有性能比较](../../comparison/README.md)
