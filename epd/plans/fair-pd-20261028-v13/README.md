# 公平 PD 代码候选 v13：qjh000 2026-10-28 CPU 验证入口

**状态：候选代码与审查记录已发布，CPU 单元尚未执行；没有新增 GPU、模型或性能结果。** 执行后的原始日志、回执与独立结果审查会单独交付到 `epd/validation/`，本页只描述这次单元的范围。

- [54 项冻结源码](../../code/fair-pd-candidate-20261028-v13/)、[manifest](source-manifest-v13.json)，manifest SHA256：`4065e53e0697d7e0478a5900e34416050124772ac9df5d48a50863d8fc453a4d`。源码目录继承的 README 仅作上游参考。
- [精确 CPU 范围](scope.json)、[实际用户指令](user-original-instruction.txt)、[归档来源说明](user-CPU-grant.json)、独立审查者原始 [G1 JSON](G1-original.json) / [G2 JSON](G2-original.json)，审查提示词与全文见 [reviews/](reviews/)。归档包装不是用户的密码学签名。
- [本次 CPU 计划](qjh000-cpu-20261028-plan.md)、[未执行回执](cpu-receipt-v13-unexecuted.json)。
- 增量与说明：[v11→v12](epd-pd-v11-to-v12.patch)（薄 controller，[说明](source-feasibility-v12.md)）、[v12→v13-a](epd-pd-v12-to-v13-a.patch)（针对 v12 独立 G2 两项 BLOCKING 的修复，[说明](source-feasibility-v13-a.md)）、[v13-a→v13](epd-pd-v13-a-to-v13.patch)（仅 runner 范围，[说明](source-feasibility-v13.md)）。[已执行的 v11](../fair-pd-20261027-v11/README.md) 原样保留。

范围：用户 CPU 票 `bk-20261028T0141-8936eb9c`，2026-10-28 09:00–19:00（北京）；boot `c57aee5b-05dd-4c39-81fc-4c76b492d3d6`；新 checkout `/var/tmp/boyjiang-epd-cpu-qjh000-20261028`，源码子目录 `epd/code/fair-pd-candidate-20261028-v13`。CPU50、nice10、每进程 1GiB 地址空间，单次 300 秒任务＋最多 30 秒受控清理，一次不可退款 claim、零自动重试；不导入 GPU 库、不启动模型或 TCP/UDP 服务。同机 GPU lane 属他人，不查询、不使用。

v12 的独立 G2 原文未保存在本地，仅有实现者转述，因此本次 G2 覆盖 v11→v13 全部增量。CPU PASS 不替代 CUDA IPC、Ray/vLLM、冷启重启或模型 G3；numeric native36 与 selected360 仍未实现并在 claim 前 fail-closed。候选 1440 模型请求/340 分钟不是执行许可。内部实现称 PD 消融基线，不称 DistServe 实测。三个完整副本、调优 PD、EPD 的公平性能对照仍未完成。

[返回 EPD 项目及既有 baseline 比较](../../README.md) · [既有结果](../../comparison/README.md)
