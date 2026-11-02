# EPD：源码部署与 CPU 验证（2026-11-03）

**qjh003 已完成指定源码部署和 77 项 CPU 软件测试；本批尚无 GPU/模型或性能结果。** 这不是 native36、CUDA IPC、embedding/KV 传输、冷启动/重启后模型正确性或公平三组性能通过。CPU 测试使用隔离的模拟依赖，不能据此推断真实 Ray/NVML/Torch 链路可运行。

[返回 EPD 项目](../README.md) · [历史 baseline 比较](README.md) · [SpaceServe 独立项目](../../spaceserve/README.md)

## 本次完成与尚缺证据

| 项目 | 实际结果 | 可核查原件 |
|---|---|---|
| GitHub 实验源码 | `1a637d2de9c71e2c6fb98ee5a9673be1b2870e3f`，源码发布独立 G3 通过 | [审查原文](../data/epd-20261103-source-G3.txt) |
| qjh003 部署 | 同一 commit，155 项源码清单逐文件 SHA256 一致，工作树 clean | [源码清单](../data/epd-20261103-source-manifest.json)、[实际部署终态](../data/epd-20261103-deployment-terminal.json)、[独立 G3](../data/epd-20261103-deployment-G3.txt) |
| 目标机 CPU 软件测试 | 77 项，0 失败、0 错误、0 跳过；CPU50、nice10、空 CUDA | [原始命令与 unittest 日志](../data/epd-20261103-cpu-commands.log)、[测试摘要](../data/epd-20261103-cpu-summary.json)、[独立 G3](../data/epd-20261103-cpu-G3.txt) |
| 测试前后源码与进程 | 155 项源码不变；原监督进程身份已不在，未发送清理信号 | [原始终态](../data/epd-20261103-cpu-terminal.json)、[独立退出观察](../data/epd-20261103-cpu-release.json) |
| 实际 GPU / 模型链路 | **本批未执行**；需要新有效资源窗口及当前版本配置、预检证据 | 没有以 CPU 结果代替 |
| 三副本 / PD 消融 / EPD 性能 | **本批未执行**；没有新的 req/s、tokens/s、TTFT、TPOT、E2E 或加速比 | [既有实测性能与限制](README.md)保留，不能混为本批结果 |

实际测试子进程共运行约 1.57 秒；摘要约 1.66 秒还包含发现与包装，二者计时范围不同。原始命令日志和终态保持原字节。源码发布审查记录的“尚未部署”、部署审查记录的“尚未测试”属于当时状态；后续各阶段的独立原件分别证明推进，不追溯修改旧记录。

## 代码与复跑入口

源码固定在 [1a637d2](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/1a637d2de9c71e2c6fb98ee5a9673be1b2870e3f/epd/runtime)：[统一入口](https://github.com/BoyJiang2/spaceserve-epd-reproduction/blob/1a637d2de9c71e2c6fb98ee5a9673be1b2870e3f/epd/runtime/entry.py)、[CPU 与预检说明](https://github.com/BoyJiang2/spaceserve-epd-reproduction/blob/1a637d2de9c71e2c6fb98ee5a9673be1b2870e3f/epd/runtime/PREFLIGHT.md)、[三组选择协议](https://github.com/BoyJiang2/spaceserve-epd-reproduction/blob/1a637d2de9c71e2c6fb98ee5a9673be1b2870e3f/epd/runtime/selected_unit.py)、[实际双 session 执行实现](https://github.com/BoyJiang2/spaceserve-epd-reproduction/blob/1a637d2de9c71e2c6fb98ee5a9673be1b2870e3f/epd/runtime/selected_execution.py)。本页所在文档 commit 与这些实验源码 commit 分开记录。

在指定源码版本、已授权 CPU 环境以及已有可写临时目录下，可复跑 selected CPU 软件测试：

```bash
cd /local/boyjiang/epd/repo/epd/runtime
export EPD_CPU_TEST_TMP=/local/boyjiang/epd/staging
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 \
  taskset -c 50 nice -n 10 /local/boyjiang/epd/assets/envs/epd/bin/python \
  -I -S -B -m unittest discover -s tests -p 'test_selected*.py' -v
```

以上仅为 CPU 软件测试入口，实际已验收批次还使用了固定 harness 的隔离导入限制与原件收集，详见原始命令日志。Linux 本批无跳过；Windows 平台存在一个 POSIX 专属测试跳过，不混作目标 Linux 成绩。不要在实验运行中切换部署源码。

实际 GPU 路径仍按 `numeric → qualification → calibration → selected_g3` 的原协议推进。三个系统共同使用 MiniCPM-V-2_6、FP16/TP1、三张 H20；PD 为 E+P 合并、D 独立的内部消融基线，**不是 DistServe 实测**。合理调优的选择规则、共同请求与缓存、原生 reference、实际资源释放和独立 G3 都须实际验证。selected 的 cold/restart 各 60 条、每系统总 120 条，不等于正式性能矩阵已经执行。

当前仓库内旧 `project-scope.json` 只允许 numeric，且绑定历史预约；它不能用来启动新的模型阶段。未来窗口需要先冻结有效配置并完成对应源码提交/部署与审查，不能删除 guard 或用历史 PASS 放行。服务启动诊断也不能代替完整实验验收。

## 数据边界与历史性能

本页公开必要的原始 CPU 日志、源码清单、终态及独立审查，见[本批文件大小与 SHA256](../data/epd-20261103-evidence-index.json)。包含其他用户历史预约信息的完整 claim/API 快照保留本地原件，不新增公开；索引保留原件 SHA 与字节数，独立审查已核授权条件和原始命令关联。未提交环境、模型、缓存或凭据。

[旧 qjh003 方案 A](README.md)与[旧 qjh000 53/60 修正批次](../README.md)独立保留，正收益、退化和逐请求数据均不删除。旧三卡完整三副本 baseline 的吞吐及 EPD/baseline 比值不能改称本批公平 PD 三组结果。profiling 还不足以证明 off 运行的因果关键路径，不把 E+P 的量级估计写成严格收益上限。
