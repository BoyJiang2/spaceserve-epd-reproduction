# 公平 PD 代码候选 v11：qjh000 CPU 验证入口

**当前只完成代码与计划审查，目标 CPU 测试尚未执行，没有新增 GPU/模型或性能结果。** v11 在 v8 基础上补齐实际 API/worker 身份与路由证据生产，并接入对应九项 CPU 测试；真实 Torch UUID、Ray cwd/env、vLLM 0.6.1 driver 布局及模型路径仍待后续实际验证。

- [51 项冻结源码](../../code/fair-pd-candidate-20261027-v11/)、[manifest](source-manifest-v11.json)，manifest SHA256：`48b84baa42076d6a8e9e6fd322c603fc23bc11ab43a584a1a028d830849b2c76`。源码目录继承的 README 仅作上游参考，上游 assets 未随候选发布。
- [精确 CPU 范围](scope.json)、[实际用户 CPU 指令](user-original-instruction.txt)、[归档来源说明](user-CPU-grant.json)、独立审查者原始 [G1 JSON](G1-original.json) / [G2 JSON](G2-original.json)。归档包装不是用户的密码学签名。
- [本次 CPU 计划](qjh000-cpu-new-plan.md)、[未执行回执](cpu-receipt-v11-unexecuted.json)、[v11 准入与剩余缺口](source-feasibility-v11.md)、[身份桥接范围](source-feasibility-v9.md)。
- 增量补丁：[v8→v9](epd-pd-v8-to-v9.patch)、[v9→v10](epd-pd-v9-to-v10.patch)、[v10→v11](epd-pd-v10-to-v11.patch)。[v8 基线与完整补丁](../fair-pd-20261027/README.md)独立保留。

本次用户已指定 qjh000 CPU，实际票为 `bk-20261027T1130-99a32163`，2026-10-27 19:00 至 28 日 08:00。目标为新 boot `c57aee5b-05dd-4c39-81fc-4c76b492d3d6`、新 checkout `/var/tmp/boyjiang-epd-cpu-qjh000-20261027`，源码子目录为 `epd/code/fair-pd-candidate-20261027-v11`。CPU50、nice10、每进程 1GiB 地址空间，单次 300 秒任务＋最多 30 秒受控清理，零自动重试；不导入 GPU 库、不启动模型或 TCP/UDP 服务。其他人的 GPU 预约不被修改或使用。

必须先完成候选及精确 commit G5、普通 push、服务器指定 commit/51 项 SHA/clean 验证，再提供五分钟内真实 CPU 预约和 host probe，由 runner 消费精确 scope 的原始 G1/G2、真实用户指令和实际 Git 远端证明。启动前会持久化不可退款的一次 claim；失败保存原始日志，不删除 claim 重跑。所有临时文件在受控 runtime 下，输出保留全测试 ID、真实退出码、skip、源码前后 SHA 与清理身份。

本入口固定这次日期/主机/boot，不能直接用于新窗口。实际 CPU 结果未知；CPU PASS 也不替代 CUDA IPC、Ray/vLLM、冷启重启或模型 G3。GPU controller、请求向量/claim 接线及受控释放仍有缺口；候选 1440 模型请求/340 分钟不是执行许可。内部实现称 PD 消融基线，不称 DistServe 实测。三个完整副本、调优 PD、EPD 的公平性能对照仍未完成。

[返回 EPD 项目及既有 baseline 比较](../../README.md) · [既有结果](../../comparison/README.md)
