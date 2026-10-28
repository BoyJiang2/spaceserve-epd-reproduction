# 公平 PD 代码候选 v13：qjh000 2026-10-28 CPU 验证入口

**状态：本页源码已作为 commit `f1ff073dee310ae0b2922d3be7a558b6a12ca7ec` 发布，并在 qjh000 目标 CPU 实际 87 PASS（0 失败/错误/跳过）；没有新增 GPU、模型或性能结果。** [原始日志、回执与独立结果审查](../../validation/qjh000-cpu-20261028/README.md)单独交付，本页描述这次单元的范围。

- [54 项冻结源码](../../code/fair-pd-candidate-20261028-v13/)、[manifest](source-manifest-v13.json)，manifest SHA256：`4065e53e0697d7e0478a5900e34416050124772ac9df5d48a50863d8fc453a4d`。源码目录继承的 README、FOLLOWUP、PREFLIGHT 及部分测试 docstring 可能滞后，以本页和本目录文件为准。
- [精确 CPU 范围](scope.json)、[实际用户指令](user-original-instruction.txt)、[归档来源说明](user-CPU-grant.json)、独立审查者原始 [G1 JSON](G1-original.json) / [G2 JSON](G2-original.json)，审查请求、全文与处理记录见 [reviews/](reviews/)。归档包装不是用户的密码学签名。
- [本次 CPU 计划](qjh000-cpu-20261028-plan.md)、[执行说明与 host probe 口径](execution-notes.md)、[实际编排脚本副本](orchestration/)、[发布时的未执行回执](cpu-receipt-v13-unexecuted.json)（其 `remote_network_GPU_booking_push=false` 只指候选打包本身；当日的只读 API/SSH 观察、一次未成功的 GPU 预约创建尝试和远端部署预演均已在计划、审查处理记录与执行说明中披露）。
- 增量与说明：[v11→v12](epd-pd-v11-to-v12.patch)（薄 controller，[说明](source-feasibility-v12.md)）、[v12→v13-a](epd-pd-v12-to-v13-a.patch)（针对 v12 独立 G2 两项 BLOCKING 的修复，[说明](source-feasibility-v13-a.md)）、[v13-a→v13](epd-pd-v13-a-to-v13.patch)（仅 runner 范围，[说明](source-feasibility-v13.md)）。[已执行的 v11](../fair-pd-20261027-v11/README.md) 原样保留。

范围：用户 CPU 票 `bk-20261028T0141-8936eb9c`，2026-10-28 09:00–19:00（北京）；boot `c57aee5b-05dd-4c39-81fc-4c76b492d3d6`；新 checkout `/var/tmp/boyjiang-epd-cpu-qjh000-20261028`，源码子目录 `epd/code/fair-pd-candidate-20261028-v13`。父 runner 与测试子进程均限 CPU50、nice10；测试子进程及其 helper 受 1GiB 地址空间与 300 秒 CPU 时间限制（父 runner 不受这两项限制）；单次 300 秒任务（含 preflight）＋最多 30 秒受控清理，一次不可退款 claim、零自动重试；不导入 GPU 库、不启动模型或 TCP/UDP 服务。同机 GPU lane 属他人，本单元不查询、不使用（单元之外曾有一次只读 nvidia-smi 查询，见计划）。

**GPU 硬前置：** G2 非阻塞项 1 指出 controller 清理循环可能因 ProcessLookupError 提前中止，必须在任何 GPU 使用该 controller 之前修复并另走 G2（见 [G2 处理记录](reviews/g2-v13-code-handling.md)）。

v12 的独立 G2 原文未保存在本地，仅有实现者转述，因此本次 G2 覆盖 v11→v13 全部增量。CPU PASS 不替代 CUDA IPC、Ray/vLLM、冷启重启或模型 G3；numeric native36 与 selected360 仍未实现并在 claim 前 fail-closed。候选 1440 模型请求/340 分钟不是执行许可。内部实现称 PD 消融基线，不称 DistServe 实测。三个完整副本、调优 PD、EPD 的公平性能对照仍未完成。

[返回 EPD 项目及既有 baseline 比较](../../README.md) · [既有结果](../../comparison/README.md)
