# SpaceServe 2026-11-03：源码与 CPU 准备证据

**qjh003 的 103 项源码部署与 36 项 CPU 软件回归已通过独立验收；本批没有 GPU 模型或正式性能数据。** 本页保留旧版本的失败，不将软件测试计入吞吐、TTFT、TPOT、E2E、显存或加速比统计。

[SpaceServe 项目](../README.md) · [历史 baseline 比较](README.md) · [11月2日模型与机制证据](20261102-preflight.md) · [原件大小与 SHA256](../data/space-20261103-cpu-index.json)

## 版本、成功与失败

| 阶段 | 源码版本 | 实际结果 | 原始证据 |
|---|---|---|---|
| 控制面修正 | `1935a9e` | CPU 无项目票时，同账号的其他 CPU/整机预约也会阻止准入；没有新增使用资源的权利 | [补丁](../data/space-20261103-cpu-authorization.patch) |
| 首次目标机软件回归 | `1935a9e` | **36 run、0 failures、3 errors、0 skip；exit1**。三项 FD 测试在 setUp 创建 `/local/outputs` 临时目录时报错 | [summary](../data/space-20261103-cpu-old-summary.json)、[原始日志](../data/space-20261103-cpu-old-commands.log)、[原终态](../data/space-20261103-cpu-old-terminal.json) |
| 失败资源收口 | `1935a9e` | child 已等待退出，原 supervisor 实际不存在，后续 fresh 源码仍为103项/clean；**测试仍失败** | [独立审查原文](../data/space-20261103-cpu-old-closure-G3.txt)、[结构化结论](../data/space-20261103-cpu-old-closure-G3.json) |
| 临时目录修正及新部署 | `8536190` | 仅一行测试代码优先使用明确指定的现有临时目录；103项新源码逐 SHA 核同 | [补丁](../data/space-20261103-cpu-temp-directory.patch)、[manifest](../data/space-20261103-cpu-source-manifest.json)、[部署终态](../data/space-20261103-cpu-deployment-terminal.json)、[独立部署 G3](../data/space-20261103-cpu-deployment-G3.txt) |
| 新版本目标机软件回归 | `8536190` | **36 run、0 failures、0 errors、0 skip；exit0**。三项 FD 用例实际执行并通过 | [summary](../data/space-20261103-cpu-new-summary.json)、[原始日志](../data/space-20261103-cpu-new-commands.log)、[原终态](../data/space-20261103-cpu-new-terminal.json)、[独立 CPU G3](../data/space-20261103-cpu-G3.txt) |
| 新版本资源释放 | `8536190` | 测试前后103项源码完全一致，HEAD/clean核同；本次原 supervisor 的 `/proc` 目录已不存在，未发送清理信号 | [真实退出观察](../data/space-20261103-cpu-new-release.json) |

两个版本是不同的受审查单元。原失败版本未重派、未删用例或 skip，也没有创建 `/local/outputs` 绕过错误。失败终态中的 `source_after` 仍为空；后续只读收口证明的是后来观察到的源码状态，未补写原失败终态。新版本的 `source_before` 与 `source_after` 才是同次成功测试的前后证据。

CPU36包含24项窗口策略测试，以及12项阶段启动与控制器测试。三个真实 FD 用例检查正确文件的 hash/rewind、错误 hash 的拒绝和非普通文件的拒绝。它们使用标准库、真实小文件与 pipe；GPU查询相关测试采用原有 mock，没有据此验证实际 GPU 空闲、CUDA、NVML、Ray、SM mask 或模型推理。

新版本实际 child 使用 CPU50、nice10、空 CUDA、系统 Python 隔离模式，硬件/网络包禁止导入的 attempts 和 loaded 均为空。五条受监督命令均 exit0，测试前后源码核同；释放观察绑定本次 supervisor PID284994/start59286101，见原件。日志的 unittest 计时与 summary 的加载加执行计时范围不同，两者都不是 GPU 性能指标。

## 指定源码与 CPU 复跑

运行源码固定为 [85361901112eda3af0157df396d9f858be245c94](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/85361901112eda3af0157df396d9f858be245c94)：[窗口检查](https://github.com/BoyJiang2/spaceserve-epd-reproduction/blob/85361901112eda3af0157df396d9f858be245c94/tools/space_window_20261030.py)、[FD 测试](https://github.com/BoyJiang2/spaceserve-epd-reproduction/blob/85361901112eda3af0157df396d9f858be245c94/tools/test_control_space_window_20261030.py)、[统一实验入口](https://github.com/BoyJiang2/spaceserve-epd-reproduction/blob/85361901112eda3af0157df396d9f858be245c94/spaceserve/runtime/entry.py)。文档提交与运行源码提交分别记录，复跑须使用上述源码版本。

在已授权的 CPU 环境、已部署指定版本和现有可写临时目录下，可复跑相同36项基础用例：

```bash
cd /local/boyjiang/spaceserve/repo/tools
test "$(git rev-parse HEAD)" = 85361901112eda3af0157df396d9f858be245c94 || exit 1
export SPACESERVE_CPU_TEST_TMP=/local/boyjiang/spaceserve/staging
CUDA_VISIBLE_DEVICES='' NVIDIA_VISIBLE_DEVICES=void \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  taskset -c 50 nice -n 10 /usr/bin/python3 -I -S -B -c \
  'import sys,unittest; sys.path.insert(0,"."); suite=unittest.defaultTestLoader.loadTestsFromNames(["test_space_window_20261030","test_run_space_window_20261030","test_control_space_window_20261030"]); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())'
```

该命令只运行基础软件测试。原验收还包含真实资源授权、103项源码前后校验、禁止硬件包导入、进程监督及退出观察；可核查[当时的 supervisor](../data/space-20261103-cpu-supervisor.py.txt)、[child](../data/space-20261103-cpu-child.py.txt)和原始命令日志。原封装含历史时间边界和审批条件，供查证使用，不能作为未来窗口许可直接复用。

发布时普通 Git push 遇到 TLS unexpected EOF，实际 exit128，[原错误日志](../data/space-20261103-cpu-git-push-failure.log)保留。后续独立审查批准的 Git API恢复创建相同对象，并以 `force:false` 推进源码分支；[实际 source G3](../data/space-20261103-cpu-source-G3.txt)核验了8536 commit、全树和原 blob。没有把原 CLI 失败改写为成功。

## 与模型和性能实验的边界

- 本页只新增 CPU 软件准备证据，**本批 GPU 正式仍为0/54**，没有新的请求吞吐、tokens/s或延迟加速比。
- [11月2日313请求](20261102-preflight.md)属于模型源码 `03688f8` 的独立历史批次，支持当时的解耦与 encoder mask 机制证据。当前8536的控制与测试修正没有产生新的模型预检，不能借用旧窗口许可。
- 当前 window policy/config 的历史日期仍未改为未来预约。新 GPU 窗口须先绑定有效资源和配置，完成指定版本部署及实际预检，再按完整预算执行54单元、5400正式＋1080预热。
- [旧48/54部分结果与历史 baseline](README.md)独立保留，收益和退化均不删除，不跨窗口补项后声称完整时间区组。不将未验证的 decoder 互斥称为完整 SM 分区。
- EPD 的[独立项目页](../../epd/README.md)及公平 PD 工作保持分开；本页不构成任何 EPD 模型或性能结果。

公开原件按字节和 SHA 复制；含其他用户历史预约等信息的完整 claim/API 原件保留本地，其指纹列入索引供获授权者核查。没有提交环境、模型、缓存或凭据。两项目完整 GPU 对照目标仍未完成。
