> GitHub阅读副本：仅修正链接；[封存原文](../../../../outputs/epd-profile-a/plan.md) SHA256 56577d637e0fe99c922894e6e1d3011a4b26fd47650dc23e39e2f35bbdb17cd3。原数字及解释不变。

# qjh003 EPD 方案 A：观测实施与验收

> 本文为启动前的历史计划快照，文内“待审/未运行”描述属于当时状态。当前实际状态见status.json；G5发现缺口及受限范围处置见reviews/g5-delivery-subagent.md和g1-limited-delivery-subagent.md。


用户已授权原模型/三卡/请求协议下 2400 正式+160预热；范围 G1 已批准，见 reviews/g1-scope.md。旧结果封存不改。专属远端 /local/boyjiang/epd-profile-a-20261023，环境/模型/原生通信库只读链接旧目录，源码独立复制；本批脚本及源码补丁独立保存。

## 具体采集方案（待G1/G2复核）

使用已经安装的 Nsight Systems 2024.6.2 与 opt-in NVTX，不同时运行 torch profiler。EPD API 父进程由 nsys 启动，其 Ray 子进程是否实际获得 CUDA 捕获必须由pilot证明；baseline TP1 的 Worker.execute_model 加运行期标注，需证明三副本分别捕获到真实kernel。禁用 CPU sampling 和 context-switch capture，不申请系统权限、不改驱动。

关闭模式不导入 torch NVTX、不包裹被装饰的方法，也不生成新标记；开模式保留相同调用顺序、时间戳位置、模型/采样参数，不加 CUDA synchronize。双方响应均增加 request ID 供时间线对账，另提供本机观测状态接口；原generate协议/输入/输出token不变。

正式模式每组仍20warm+100×3，第三次重复第84号请求获取并发槽后、请求提交计时前，向所有本机端点发送capture start，覆盖末段16个新请求与正在执行的请求。start控制会改变这一段客户端提交节奏，属于开启组扰动，须量化并披露，不称完全无侵入。所有正式重复计时结束后stop，服务结束后才导出SQLite。off不执行start/stop。每配置保存配置、逐请求及三次摘要、全进程显存采样、前后RGB buffer SHA、实际库/worker PID/GPU UUID。

标注CPU调用范围包括编码/LLM迭代、Ray提交（同步分派，不代表await完成）、embedding/KV迁移；原始lifetime逐事件在覆盖前标注，API输出记录API时间与orchestrator callback时间。父进程异步范围仅表示CPU等待，不当作GPU区间。GPU关键路径必须由CUDA activity与launch关联，并用request IDs、step和stage匹配；并行kernel耗时不简单相加。

## 门槛和分析

- G2之前只做CPU测试/源码准备，脚本无模型执行。关闭模式身份函数、异常后范围闭合、异步返回、迁移块ID语义及补丁失败不写入已有CPU测试；真实固定源码fixture全补丁compile通过，重复应用无修改而拒绝。
- pilot先分别跑EPD和三个完整模型副本，在捕获窗口内做标准与C8正确性检查，导出各自报告；另做一次服务重启后正确性。核对三张实际worker GPU在trace中有CUDA kernel，匹配E/P/D或baseline执行事件和API/callback标记，确认handoff及稳定decode覆盖。缺一个阶段、缺kernel或导出失败均不进入formal。
- G3只在实际证据完整且独立审查通过后写G3_APPROVED，formal脚本检查此文件。正式时重新检查GPU空闲/boot ID/库版本/输出目录不存在。
- off与旧选用数据的平均吞吐差异超过5%时调查环境/实现变化；on与同批off的平均吞吐或E2E P50变化超过5%标为显著观测扰动，结果只能用于诊断，不替代无观测性能结论；需要减少窗口时先复审，不自动扩展范围。5%是预设诊断阈值，不是统计显著性检验；同时报告三次值/波动，分别列有采集的第三次。
- 窗口包含稳定解码、P末→KV→首D、baseline prefill与decode间隔。若本次窗口未出现历史尾延迟，不宣称解释了其原因，只解释实际捕获到的区间。按GPU关键路径、无GPU活动的CPU/API等待和未解释余量分解；不能由NVTX await直接推断通信带宽或GPU完成时间。
- G4核对2400正式记录、失败/长度/视觉token/输入/缓存、观察扰动与trace证据和结论，G5核对交付。指标保持原请求吞吐、输出tokens/s、TTFT/TPOT/E2E P50/P95、峰值显存、失败率和重复波动。

尚未运行GPU pilot或正式测量，所有机制结论待实测。
