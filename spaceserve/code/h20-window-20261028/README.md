# H20 SpaceServe：2026-10-28 夜间窗口（候选，尚未运行）

**状态：G1/G2 APPROVE、BLOCKING 0，候选尚待G5及发布，未部署、未运行 GPU；没有新的性能结果。** 本目录由 [`h20-window-20261027`](../h20-window-20261027/)（runtime Git `83edff6`）机械派生，只改窗口身份：新 root `/var/tmp/boyjiang-spaceserve-window-20261028-2300`、Ray 临时目录、仓库前缀、`scripts/booking_window.py` 的预约常量（用户票 `bk-20261028T0700-987277c5`，2026-10-28 23:00 至 10-29 08:00，无延长票，任何 extension 均拒绝）、`scripts/test_window_booking.py` 中两项依赖窗口时长的测试，以及重新生成的 [56 源码清单](configs/runtime-extension-source-manifest.json)、[61 部署清单](configs/deployment-files.json)和 `tools/deploy_commit_cpu.py` 里的清单 SHA。模型、输入 pins、补丁、54 单元顺序（seed 20261027）、预算与门槛均不变。

- [本窗口计划](plan-20261028-2300.md)：同单 H20 GPU4、Qwen2-VL-7B、FP16、TP1、eager、MPS100；native vLLM / 编码器解耦 / 解耦＋实际生效 encoder SM mask；6 负载 × 3 时间区组 = 54 单元，5400 正式＋1080 预热；313 模型预检上限只允许一次；formal 201 分钟入场、每单元 900 秒、结束前 120 秒受控清理。
- 部署：19:00 前在用户 CPU 票内完成 stage 目录稀疏检出、stage 测试与冻结输入复制；23:00 后经 fresh 预约与 GPU4 空闲核验，用 `tools/deploy_commit_cpu.py` 对指定 commit 做逐文件核验部署，再按 numeric → G3 → 模型 G2 → 313 → G3 → formal G2 → 54 单元推进。
- 旧 48/54 批次与 13:00 批次 313 预检原样保留，不跨窗口拼区组；未验证 decoder 互斥，不称完整 SM 分区。

审查与实际运行证据会在运行后单独交付，本目录的历史提交不构成运行许可。

[独立G1/G2复审](reviews/g1g2-final-codex.md)已关闭两处初审阻塞；[CPU staging批准](reviews/CPU-stage-G2.json)仅允许在有效CPU票中做staging，不授予GPU。

[编排脚本归档](orchestration/)保存实际执行字节；两个派生器与批准writer依赖原工作目录布局，归档副本不是可直接迁移的入口。stage入口是同目录space_stage_remote.sh，须使用本次已发布commit；不能从旧窗口复制审查通过记录。
