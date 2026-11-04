# 官方三卡基线链路预检：EPD、PD与三个完整副本（2026-11-04）

这是官方入口的正确性与运行状态检查，**不是正式性能结果**。

## 来源与复跑入口

唯一官方源码基线为 [`vbdi/epdserve@9b111f7`](https://github.com/vbdi/epdserve/tree/9b111f710dfb4724072b603d626a1e4dad93ef1f)，服务器适配checkout为 `/local/boyjiang/epdserve-official`，本次仍为该commit、tracked工作区clean。PD使用仓库自带 `baselines/pd/distserve`；不将它称为独立DistServe已实测。

- 模型 MiniCPM-V-2_6、FP16、TP=1，qjh003的同三张NUMA0 H20。
- EPD：E:P:D=1:1:1；PD诊断：P:D=1:2，视觉编码与prefill均在P侧。这不是已调优的正式PD分配。
- 同一COCO000328单图，greedy、ignore_eos、目标128；服务器机器比较两次request JSON逐字节相同、返回output正文逐字相同。
- EPD原始记录见[官方单请求报告](20261104-official-single-request.md)。PD使用[短诊断脚本](../tools/official_pd_first_request.sh)、[身份清理助手](../tools/official_pd_processes_bounded.py)与[冻结输入](../validation/official-entry-20261104/pd-first-request-inputs.json)。脚本须在已授权窗口内传入实际预约起止、RUN、GPU_IDS、PORT、HELPER、UNIT_START_EPOCH；总入场预算900秒，不能脱离前置资源核验直接执行。

## 实际结果

| 项目 | 官方EPD r1 | 官方PD pd1 |
|---|---|---|
| 三卡角色 | E1 / P1 / D1 | P1（含视觉编码） / D2 |
| HTTP / curl | 200 / 0 | 200 / 0 |
| 实际生成事件数 | 128 | 128 |
| 请求及输出匹配 | 与PD完全相同 | 与EPD完全相同 |
| 原始work / cleanup / outer | 0 / 1 / 1 | 0 / 0 / 0 |
| 最终资源状态 | 恢复清理exit0，三卡显存0 | 自动清理exit0，三卡显存0 |

PD实际日志：context worker PID1937061在物理GPU0；decode worker PID1937062、1937063分别在GPU1、GPU2。**创建两名decode worker不证明该单请求同时使用了两张decode卡。** 日志实际出现BF16向float16转换。响应含context与migration事件，但未直接核验KV传输数值，且decoding_begin的覆盖语义不支持完整解码阶段耗时分解。

主体描述（三位穿军装者坐在长椅、帽子及书）与固定图片相符；地点、军衔等猜测不当成正确性事实。强制忽略EOS后，输出含重复结束标记及无关尾词，两次原始输出均完整保留，不能把尾部裁掉后宣称生成质量完全正确。

## 统计与机制边界

这两次均为单次冷诊断，EPD r1与PD pd1的CPU亲和配置不同（PD目标CPU0–89、OMP=4），所以不据此比较耗时或推算req/s、tokens/s、TTFT、TPOT、E2E分位数和加速比。这些指标待统一设置的三完整副本／官方PD／官方EPD矩阵测量后提供。

pd1清理记录为known192、known_live为空；另有一个不可读同UID进程1851953，现场ps显示为本次实验之前已存在的sd-pam，未处理。结论仅是已登记本run进程清理及GPU释放，不是整个同UID进程全部消失。

[逐请求输出、终态及完整原件SHA256索引](../validation/official-entry-20261104/pd1-small-evidence.json)和[独立G3/G4范围审查](../validation/official-entry-20261104/pd1-g3-g4.md)可浏览。完整stdout/stderr、Ray日志、请求及输出仍保存在服务器 `/local/boyjiang/epd/runs/pd1`，不复制环境或权重。

仍未完成：并发与多图路由、重启、embedding/KV数值一致性、三个完整模型副本、正式PD分配与公平性能矩阵。此页不替代旧方案A或其他批次的结果，也不宣称总复现完成。


## 三个独立完整模型副本：实际预检补充

使用同一官方基线的 `baselines/d/distserve`，分别启动三个完整模型服务端点，各D1/FP16/TP1、各一张GPU、合计三卡。复用现有模型与环境，不复制权重；各有独立Ray目录、端口和RUNID。这里的D入口执行完整模型，不是EPD中只处理解码阶段的worker。

| run / 端口 | 实际模型worker / 物理卡 | HTTP / 生成事件 | work / cleanup / outer | 与EPD固定请求及输出 |
|---|---|---|---|---|
| d1a / 19264 | PID2002572 / GPU0 | 200 / 128 | 0 / 0 / 0 | 逐字节/逐字相同 |
| d1b / 19265 | PID2002382 / GPU1 | 200 / 128 | 0 / 0 / 0 | 逐字节/逐字相同 |
| d1c / 19266 | PID2002389 / GPU2 | 200 / 128 | 0 / 0 / 0 | 逐字节/逐字相同 |

模块来源均实际解析到官方checkout的 `baselines/d/distserve`。父进程以nvidia-smi分别记录worker PID到完整物理GPU UUID的6/8/8轮映射；有限采样中各卡最高观测69356MiB，**不是绝对峰值显存**。每个端点仅处理一个固定图片请求；相同输出不证明图像因果或一般正确性，也未验证正式客户端均衡、并发路由或吞吐。

各run已登记live为空、对应GPU显存0，三个端点结束后再次查询全部GPU显存0、compute-apps为空。每个清理记录均保留不可读的旧sd-pam进程1851953，未处理该进程。

[三副本逐请求结果、实际设备映射及原件SHA256](../validation/official-entry-20261104/d-replicas-small-evidence.json)、[独立G3/G4范围](../validation/official-entry-20261104/d-replicas-g3-g4.md)、[复跑脚本](../tools/official_d_first_request.sh)和[冻结输入](../validation/official-entry-20261104/d-first-request-inputs.json)。完整原件仍在服务器 `epd/runs/d1a`、`d1b`、`d1c`。

至此三个官方候选的单请求链路均有真实记录；公平性能、多图、不同图片并发、重启及传输数值验证仍未完成，不拼接这些冷诊断为正式实验。
