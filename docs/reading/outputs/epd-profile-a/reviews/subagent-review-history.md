> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/epd-profile-a/reviews/subagent-review-history.md) SHA256 93b13669227bb8219faa1dac8d15ef537b54eacd6ae474fde0a268f3d0f73bdf。原数字及解释不变。

# EPD A 独立审查接替记录

Claude 合并G1/G2调用超时，没有结论；记录 g1-g2-epd-profile-a-timeout.md。缩小范围后三次CLI均明确返回 usage_limit_reached / session limit，重置17:50 Asia/Shanghai，原始JSON保留。本项目AGENTS.md §3.2.1明确授权额度耗尽即由独立subagent接替。以下均为独立只读审查者，没有实现代码、执行实验或访问GPU；主执行者Codex保存原文与处理。

## G1 后端与窗口：/root/profile_plan_review

结论：APPROVE_WITH_NITS；BLOCKING：无。

Nsight Systems + NVTX方案可支持目标：明确要求CUDA activity与launch关联，禁止以CPU等待范围直接解释GPU耗时；捕获窗口覆盖末段请求、稳定解码及阶段交接。Ray子进程和三副本是否实际捕获均由pilot验证，缺阶段、缺kernel或导出失败禁止进入formal，G3须有独立批准。既定模型、三卡、请求协议及2400正式记录范围未改变。

NON-BLOCKING：全配置平均值和第三次重复可能稀释末段16请求扰动，建议另列窗口内与off对应请求延迟；保留capture start控制耗时与实际三卡起止范围。

处理：采纳窗口内对照与控制耗时；benchmark新增capture-control.json，每个端点保存start/end、PID及状态。实际GPU范围留G3/数据分析验证。该G1不代表实际捕获通过。

## G2 打点：/root/profile_instrument_review

结论：APPROVE_WITH_NITS；BLOCKING：无。审查observe.py、instrument.py、实际instrumentation.patch及窄范围固定worker源码。

- off装饰器直接返回原函数，没有wrapper；仅显式启用才导入和调用NVTX。
- start/end token在finally结束，异常、取消与协程交错不依赖线程栈配对；异步范围含await，同步remote_call仅覆盖提交。
- worker入口含request IDs/stage/batch，模型/通信调用保留；engine/lifetime/API marker可串联请求，实际kernel关联留G3。
- 实际diff未改采样、推理分支或原时间戳表达式；baseline仍生成一次UUID交原generate；观测开销仍须量化。
- 所有变换先compile再写入；重复应用检查在正常Python有效。compile不能证明GPU正确。

建议：G3验证Nsight保留异步NVTX范围及launch correlation；禁止仅时间相交就认定因果。拒绝python -O；lifetime marker是覆盖前收到的事件通知，可能多于最终lifetime。

处理：新增if not __debug__: raise RuntimeError。审查者窄读前20行确认解决该建议，保持APPROVE_WITH_NITS/BLOCKING0。其余纳入G3与分析口径。

## G2 运行/压测：/root/profile_runner_review

首审REQUEST_CHANGES，2项BLOCKING：

1. benchmark C8只有index84等待capture start，其余槽可能先放行85+；要求共享屏障和异步模拟。
2. API PID只在就绪后登记，父启动器死后可能漏自有孤儿；要求启动独立会话、身份归属清理及残留核对。

处理：index>=84共享capture_ready，全部端点start后才放行；异步yield测试先复现FAIL、修复后PASS。启动setsid，每次run唯一REPRO_RUN_ID；正常清理API/Nsight后按UID+EXP_ROOT+精确runID扫描孤儿，排除自身/祖先。实际worker runtime要求当前runID。清理失败保留日志。

第二轮复审B1关闭，B2剩一项扫描目标自然退出竞态：日志读取name/getsid可能提前抛错，残留status亦然。改为只记录已知PID、status捕获NoSuchProcess。真实Linux CPU测试覆盖父退出后的孤儿、不同身份进程保留与扫描后一个目标消失另一个仍清理，全部通过。

最终原文：

> 最终结论：APPROVE_WITH_NITS。G2运行/压测子范围B1、B2均关闭，未解决BLOCKING为0。
>
> B1：末16请求等待全部端点capture启动，共享屏障解决C8放行竞态；异步模拟保留修复前FAIL和修复后PASS证据。
>
> B2：精确UID、EXP_ROOT、runID扫描可清理失去父进程的自有孤儿；日志与残留检查已容忍目标自然退出。已只读核对Linux CPU测试代码及通过记录，覆盖孤儿清理、不同runID进程保留和目标消失竞态。
>
> 正式矩阵保持2400正式、160预热；计时、报告保存及失败停止约束保留。
>
> NON-BLOCKING：G3_APPROVED仍是存在性门槛，主执行者须在实际G3通过后创建，并记录对应代码版本及预检证据。实际GPU覆盖、并发与重启正确性由G3验收。

后续仅增加独立pilot-restart分支以完成重启验证，分支窄读复核另记；formal仍不得在G3批准前运行。
