# qjh000：EPD/PD v13 目标 CPU 验证（2026-10-28）

**87 项测试全部通过，0 失败、0 错误、0 跳过。** [独立结果审查](reviews/actual-CPU-result-review.md)及[Codex 接续复核](reviews/codex-handoff-review.md)均为 APPROVE_WITH_NITS、BLOCKING 0。本次没有启动 GPU 或模型，不构成公平 PD 性能、CUDA IPC 或模型 G3 通过。

| 测试模块 | 实际通过数 |
|---|---:|
| test_pd_cpu | 35 |
| test_preflight_v5 | 19 |
| test_cpu_target_runner | 13 |
| test_production_identity | 9 |
| test_controller_cpu（v12/v13-a 新增） | 11 |
| 合计 | 87 |

2026-10-28 15:06 在 qjh000 实际执行，唯一 run ID 为 `cpu50-1793171216920480650`。源码 commit 为 [`f1ff073dee310ae0b2922d3be7a558b6a12ca7ec`](https://github.com/BoyJiang2/spaceserve-epd-reproduction/commit/f1ff073dee310ae0b2922d3be7a558b6a12ca7ec)，54 项 manifest SHA 为 `4065e53e0697d7e0478a5900e34416050124772ac9df5d48a50863d8fc453a4d`。服务器 Git HEAD/clean、部署与运行前后每项 SHA 均与该版本一致。测试数与 G2 审查者事前推演的 35+19+13+9+11 完全一致，11 个新 test_id 全部出现。

父 runner 与测试子进程均为 CPU50、nice10，Python 3.10.12；测试子进程及其 helper 受 1GiB 地址空间与 300 秒 CPU 时间限制；主任务墙钟 300 秒＋最多 30 秒清理。顶层单元约 3.73 秒，这是 CPU 验证用时，不能用于模型吞吐或延迟比较。新增用例覆盖 v12 G2 的两项修复：预约校验在构造 NVML 与 Claim 之前生效（六种拒绝模式），以及请求事件的 submitted→http_body→complete/cancelled 持久化与真实子进程 SIGTERM 取消传播；身份测试使用明确的 CPU fixture，不证明真实 Torch/Ray/vLLM 兼容性。

第二次预约检查、非 200/failed 路径等尚未覆盖。预约观测时间取本地时钟，依赖本次实测的约 0.16 秒时钟偏差；不把它描述为服务端时间戳。

## 原始证据与复核

- [实际顶层回执](result-original/epd/code/fair-pd-candidate-20261028-v13/runtime/cpu50-1793171216920480650/CPU-receipt.json)（SHA256 `c39f2ab47e08ece5b57ee44bfe90b954cd13ecef9800eebd91ae6ab9024c172f`）、[完整测试日志](result-original/epd/code/fair-pd-candidate-20261028-v13/runtime/cpu50-1793171216920480650/raw-test.log)、[87 项 start/success 事件](result-original/epd/code/fair-pd-candidate-20261028-v13/runtime/cpu50-1793171216920480650/test-events.jsonl)、[测试结果](result-original/epd/code/fair-pd-candidate-20261028-v13/runtime/cpu50-1793171216920480650/test-result.json)、[helper 身份](result-original/epd/code/fair-pd-candidate-20261028-v13/runtime/cpu50-1793171216920480650/helper-pids.jsonl)。
- [唯一持久 claim](result-original/epd/code/fair-pd-candidate-20261028-v13/runtime/CPU-unit-claim.json)、[实际 permit](result-original/epd/plans/fair-pd-20261028-v13/cpu-permit.json)、[permit 绑定的 cpu-inputs](result-original/epd/plans/fair-pd-20261028-v13/cpu-inputs/)（规范化本人预约、host probe、部署记录、GitHub main 原始响应与收据）、[runner stdout](result-original/epd/plans/fair-pd-20261028-v13/runner-stdout.txt)/[stderr](result-original/epd/plans/fair-pd-20261028-v13/runner-stderr.txt)。审批、scope、用户指令与 manifest 位于 [v13 计划目录](../../plans/fair-pd-20261028-v13/README.md)，permit 中各 descriptor 的相对路径即指向该目录内文件。
- runtime 下其余 `cpu50-*` 目录是测试套件中真实 POSIX 用例以 mock 授权调用 runner 产生的嵌套回执，原样保留但不作为实际执行证明；其 commit 为 `a` 重复40次、claim 为 `CPU-MOCK-lifecycle-claim`，实际回执由唯一持久 claim 的 run ID 选取。
- [编排记录](orchestration-records/)：实际命令、时钟偏差（服务器比本地快约 0.16 秒）、SSH 退出信息、部署输出，以及[结束后只读释放复核](orchestration-records/release-check.json)（父/子/7 个 helper 共 9 个身份均 absent，root 内无自有进程，HEAD 与 tracked clean 不变；未发信号、未查询 GPU）。实际执行的编排脚本与 [v13 计划目录的 orchestration/](../../plans/fair-pd-20261028-v13/orchestration/) 副本逐字节相同。
- [本地完整性核对](local-result-integrity.json)：tar 成员与解压副本、上传输入与服务器副本、permit descriptor、回执与 stdout、claim 绑定的 permit SHA、规范化预约绑定的原始快照 SHA 均一致。完整原始预约快照含他人预约与主机信息，只保留在本地，此处仅公开其 SHA 与大小。
- [独立结果审查](reviews/)。

释放复核本身未发信号；测试套件按设计向自有 fixture 进程发送过 TERM/INT。[复核脚本](orchestration-records/release-check-script.py)与[实际命令](orchestration-records/release-check-command.md)已保存，release-check.json 是该命令原始 stdout。脚本中的零信号、未查询 GPU 字段是对代码路径的声明，并非 GPU 侧测量。

## 范围与下一步

本次只证明受控目标 Python 上的 CPU 逻辑、真实 POSIX 子进程边界与 mock 身份/预约契约。真实 Torch UUID、Ray 环境、vLLM driver 布局、跨卡 IPC、冷启重启及 E+P/PD/EPD 模型链路均未验证；numeric native36 与 selected360 仍未实现（claim 前 fail-closed），controller 清理循环须在任何 GPU 使用前按 G2 非阻塞项 1 修复。不得把 87 PASS 当成模型可运行或性能收益。

本 root 的一次 claim 已消耗，不删除或复用；后续源码改动须形成新版本、经审查与 push，在实际有效资源上部署指定 commit 后使用新的受控单元。CPU 预约不授予 GPU、1440 模型请求/340 分钟候选预算或正式矩阵。SpaceServe 正式 0/54、旧 48/54、EPD 旧 53/60 分别保留，两个完整目标仍未完成。

[返回 EPD 项目](../../README.md) · [v13 源码与本次计划](../../plans/fair-pd-20261028-v13/README.md) · [昨日 v11 CPU 验证](../qjh000-cpu-20261027/README.md)
