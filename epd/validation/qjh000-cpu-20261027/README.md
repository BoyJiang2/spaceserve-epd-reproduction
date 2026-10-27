# qjh000：EPD/PD v11 目标 CPU 验证

**76 项测试全部通过，0 失败、0 错误、0 跳过。** 独立结果审查为 APPROVE_WITH_NITS/BLOCKING 0，唯一原件路径说明已补齐；本页为待发布 G5 的数据候选。本次没有启动 GPU 或模型，不构成公平 PD 性能、CUDA IPC 或模型 G3 通过。

| 测试模块 | 实际通过数 |
|---|---:|
| test_pd_cpu | 35 |
| test_preflight_v5 | 19 |
| test_cpu_target_runner | 13 |
| test_production_identity | 9 |
| 合计 | 76 |

2026-10-27 21:52 在 qjh000 实际执行，唯一 run ID 为 `cpu50-1793109134198351931`。源码 commit 为 [`6ca496bb93778d7d8d3f57ff64b85f6c093d3df2`](https://github.com/BoyJiang2/spaceserve-epd-reproduction/commit/6ca496bb93778d7d8d3f57ff64b85f6c093d3df2)，51 项 manifest SHA 为 `48b84baa42076d6a8e9e6fd322c603fc23bc11ab43a584a1a028d830849b2c76`。服务器 Git HEAD/clean、部署及运行前后每项 SHA 均与该版本匹配。

CPU50、nice10，Python3.10.12；每进程 RLIMIT_AS 为 1GiB、CPU 时间上限300秒，主任务墙钟300秒＋最多30秒清理。实际 unittest 耗时3.406秒、顶层单元约3.583秒；这些是 CPU 验证用时，不能用于模型吞吐或延迟比较。五项真实 POSIX 场景覆盖 TERM/INT、等待异常及 fork 后 wrapper 返回前信号边界，九项身份测试使用明确的 CPU fixture，不证明真实 Torch/Ray/vLLM 兼容性。

## 原始证据与复核

- [完整测试日志](result-original/raw-test.log)、[76项 start/success 事件](result-original/test-events.jsonl)、[测试结果](result-original/test-result.json)、[顶层回执](result-original/CPU-receipt.json)。顶层回执 SHA256 为 `f70435c4bb8770f20e1397fc421169a6681aa4c07bebd070990b08e93421792d`。
- [唯一持久 claim](CPU-unit-claim.json)、[实际命令](actual-command.txt)、[实际 permit](cpu-permit.json)、[精确 scope](scope.json)、独立原始 [G1](G1-original.json)/[G2](G2-original.json)、[用户指令归档](user-CPU-grant.json)。该归档关联实际用户原话，不是用户签名或凭据。
- [原始51项部署证明](cpu-inputs/deployment.json)、[源清单](source-manifest-v11.json)、[远端代码核验](remote-code-verified.json)、[本地下载及原件链核验](local-result-integrity.json)。
- [实际预约凭据](cpu-inputs/booking.json)、[实际消费的 host 原件](cpu-inputs/host-probe.json)、[路径/SHA映射](evidence-path-mapping.json)。另存的 [stdout重新序列化投影](cpu-inputs/host-probe-stdout-normalized.json)不是 permit 消费的原字节。
- [结束后只读释放复核](release-check.json)：父进程1591520、子进程1591539及六个登记helper均 absent，tracked source clean；没有发信号或查询 GPU。[独立实际结果审查](reviews/actual-CPU-result-review.md)确认这些证据只支持 CPU 范围。
- [部署期间的传输与诊断失败记录](deployment-history.md)单列，未计成测试失败或模型失败，没有删除原件重试同一 CPU 单元。

实际顶层回执由原始 claim 的 run ID 唯一选取；测试中的嵌套 mock 回执不作为实际执行证明。所有原始结果按真实字节保留。需要复核时，可根据 permit 各 descriptor 的相对路径和 SHA，核查该目录内审批、用户指令、预约/host、Git与源码链；原服务器绝对路径在数据中保留为来源记录。

## 范围与下一步

本次仅证明受控目标 Python 上的 CPU 逻辑、真实 POSIX 子进程边界及 mock 身份契约。真实 Torch UUID、Ray 环境/cwd、vLLM driver 布局、跨卡 IPC、冷启重启及 E+P/PD/EPD 模型链路均未验证；GPU controller 与请求向量/受控释放仍需接线。不得把76 PASS当成模型可运行或性能收益。

原 root 的一次 claim 已消耗，不删除或复用。后续源码改动必须在本地形成新版本，经审查/push，在实际有效资源上部署指定 commit、核验后使用新的受控单元。CPU预约不授予GPU、1440模型请求/340分钟候选预算或正式矩阵。SpaceServe正式0/54、旧48/54、EPD旧53/60分别保留，整体目标仍未完成。

[返回 EPD 项目及 baseline 对照](../../README.md) · [v11源码和本次准入计划](../../plans/fair-pd-20261027-v11/README.md)
