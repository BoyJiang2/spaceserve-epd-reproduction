# EPD修正批次：C五负载性能对照

**候选报告，待实际独立G4/G5审查。分析器不授予任何Gate。**

MiniCPM-V-2_6，FP16/TP1；EPD E:P:D=1:1:1，对照同三张H20上的三个完整模型副本。统一图数上限8、context4096；IRP与动态角色切换关闭。

每cell20预热、100正式；六个时间区组。吞吐为成功请求/整个正式窗口，延迟单位ms。旧三重复结果不混入本批区间。

数据完整性：**未完成或证据不足**；有效cell 53/60。

[完整逐cell统计、错误和源SHA](analysis.json)。分析JSON SHA256：`167382783feabae1d6e34830d407f1da65cd9268cecae20e3bc47830aba8d9f7`。

## 失败分支与解释范围

**EPD lite观察G3失败：冷启/重启worker没有导出CUDA窗口。B阶段（观测开销）正式未运行，未证明观测等效。** 独立G1及失败G4批准后仅执行原预算C-off；不调剂B预算、不增加GPU正确性请求。模型正确性通过与完整观察失败分别记录。

每cell计时窗外保存全机GPU、host load、available memory和swap快照；它们会遗漏窗内瞬态竞争。结果只支持该共享主机条件下的相对性能，不证明纯观察器成本、off阶段关键路径或内部因果瓶颈。

## 中断及唯一断点续接

原控制器完成block0的10个单元（1000正式＋200预热）后，在下一单元启动阶段中断；原退出码未知（null）、原因未知。前10个单元原样保留，计划仅续接原顺序剩余50个单元（5000正式＋1000预热）；实际完成数量以数据完整性与逐cell统计为准，没有重采或调剂B预算。

冻结的执行版本范围（完成情况见逐cell统计）：索引[0, 9]：`9bb1a92b9864bb9ccd837a9258d7079f0dc98d559ab305c906d4bed6d27d4bbd`；索引[10, 59]：`01cab0ae49091effbd6bed8220fee96382d711f761ef7bcfa8652ad287da5ed0`。控制器版本变化不等于推理算法变化，差异与审批见原始证据。

前一区组最后正式窗口结束至续接首个正式窗口开始相隔 2203.29 秒，包含清理、等待、重启及预热，不能解释为纯故障耗时。

## 唯一续接的实际终止

实际控制器PID 3542208，退出码 1，错误类型 `IdentityUnconfirmed`：cannot confirm candidate process identity: 4052597。本次唯一续接额度已耗尽，不再补跑缺失单元；本批为终态部分结果，完整C未完成。身份读取失败的底层原因尚未确定，不能据此断定模型数值错误。

[原退出回执](../../evidence/C-resume-exit.json) · [终态资源释放证据](../../evidence/C-terminal-resource-status.json)。

不生成性能/等效性区间或对照图。所有计划cell继续列出，不能仅筛选完成者计算六区组结论。

| 计划序号 | 区组/负载/系统/模式 | 状态 | 实际记录数 / 记录失败数 |
|---|---|---|---:|
| 0 | 0/E/epd/off | valid | 120 / 0 |
| 1 | 0/E/baseline-epd/off | valid | 120 / 0 |
| 2 | 0/C/epd/off | valid | 120 / 0 |
| 3 | 0/C/baseline-epd/off | valid | 120 / 0 |
| 4 | 0/B/baseline-epd/off | valid | 120 / 0 |
| 5 | 0/B/epd/off | valid | 120 / 0 |
| 6 | 0/A/epd/off | valid | 120 / 0 |
| 7 | 0/A/baseline-epd/off | valid | 120 / 0 |
| 8 | 0/D/baseline-epd/off | valid | 120 / 0 |
| 9 | 0/D/epd/off | valid | 120 / 0 |
| 10 | 1/D/epd/off | valid | 120 / 0 |
| 11 | 1/D/baseline-epd/off | valid | 120 / 0 |
| 12 | 1/E/baseline-epd/off | valid | 120 / 0 |
| 13 | 1/E/epd/off | valid | 120 / 0 |
| 14 | 1/C/baseline-epd/off | valid | 120 / 0 |
| 15 | 1/C/epd/off | valid | 120 / 0 |
| 16 | 1/B/epd/off | valid | 120 / 0 |
| 17 | 1/B/baseline-epd/off | valid | 120 / 0 |
| 18 | 1/A/baseline-epd/off | valid | 120 / 0 |
| 19 | 1/A/epd/off | valid | 120 / 0 |
| 20 | 2/C/epd/off | valid | 120 / 0 |
| 21 | 2/C/baseline-epd/off | valid | 120 / 0 |
| 22 | 2/B/baseline-epd/off | valid | 120 / 0 |
| 23 | 2/B/epd/off | valid | 120 / 0 |
| 24 | 2/A/epd/off | valid | 120 / 0 |
| 25 | 2/A/baseline-epd/off | valid | 120 / 0 |
| 26 | 2/D/baseline-epd/off | valid | 120 / 0 |
| 27 | 2/D/epd/off | valid | 120 / 0 |
| 28 | 2/E/epd/off | valid | 120 / 0 |
| 29 | 2/E/baseline-epd/off | valid | 120 / 0 |
| 30 | 3/A/baseline-epd/off | valid | 120 / 0 |
| 31 | 3/A/epd/off | valid | 120 / 0 |
| 32 | 3/D/epd/off | valid | 120 / 0 |
| 33 | 3/D/baseline-epd/off | valid | 120 / 0 |
| 34 | 3/E/baseline-epd/off | valid | 120 / 0 |
| 35 | 3/E/epd/off | valid | 120 / 0 |
| 36 | 3/C/baseline-epd/off | valid | 120 / 0 |
| 37 | 3/C/epd/off | valid | 120 / 0 |
| 38 | 3/B/epd/off | valid | 120 / 0 |
| 39 | 3/B/baseline-epd/off | valid | 120 / 0 |
| 40 | 4/B/baseline-epd/off | valid | 120 / 0 |
| 41 | 4/B/epd/off | valid | 120 / 0 |
| 42 | 4/A/epd/off | valid | 120 / 0 |
| 43 | 4/A/baseline-epd/off | valid | 120 / 0 |
| 44 | 4/D/baseline-epd/off | valid | 120 / 0 |
| 45 | 4/D/epd/off | valid | 120 / 0 |
| 46 | 4/E/epd/off | valid | 120 / 0 |
| 47 | 4/E/baseline-epd/off | valid | 120 / 0 |
| 48 | 4/C/epd/off | valid | 120 / 0 |
| 49 | 4/C/baseline-epd/off | valid | 120 / 0 |
| 50 | 5/E/baseline-epd/off | valid | 120 / 0 |
| 51 | 5/E/epd/off | valid | 120 / 0 |
| 52 | 5/B/epd/off | valid | 120 / 0 |
| 53 | 5/B/baseline-epd/off | missing | 未知 / 未知 |
| 54 | 5/C/baseline-epd/off | missing | 未知 / 未知 |
| 55 | 5/C/epd/off | missing | 未知 / 未知 |
| 56 | 5/D/epd/off | missing | 未知 / 未知 |
| 57 | 5/D/baseline-epd/off | missing | 未知 / 未知 |
| 58 | 5/A/baseline-epd/off | missing | 未知 / 未知 |
| 59 | 5/A/epd/off | missing | 未知 / 未知 |

## 全部计划配对的逐次原始观测

这里只描述已经产生且单元审计通过的运行；未完成矩阵不作合并估计、总体加速结论或CI。单次比值不是六区组结论，缺失项不填零、不筛选有利负载。所有区组/负载均列出；表格排序用于导航，不改变冻结采集顺序。

| 区组/负载 | 三副本 req/s / tokens/s | EPD req/s / tokens/s | 单次EPD/基线 | 基线/EPD状态 |
|---|---:|---:|---:|---|
| 0/A | 0.5311 / 67.98 | 0.4922 / 63.00 | 0.9267× | valid/valid |
| 0/B | 3.7590 / 481.16 | 3.4964 / 447.54 | 0.9301× | valid/valid |
| 0/C | 4.1611 / 532.62 | 3.7458 / 479.46 | 0.9002× | valid/valid |
| 0/D | 3.2778 / 419.55 | 3.2624 / 417.59 | 0.9953× | valid/valid |
| 0/E | 7.3589 / 235.48 | 5.6300 / 180.16 | 0.7651× | valid/valid |
| 1/A | 0.5307 / 67.93 | 0.4922 / 63.01 | 0.9275× | valid/valid |
| 1/B | 3.7706 / 482.64 | 3.5761 / 457.74 | 0.9484× | valid/valid |
| 1/C | 4.2864 / 548.65 | 3.8797 / 496.60 | 0.9051× | valid/valid |
| 1/D | 3.3429 / 427.89 | 3.2953 / 421.79 | 0.9857× | valid/valid |
| 1/E | 7.2722 / 232.71 | 5.7687 / 184.60 | 0.7933× | valid/valid |
| 2/A | 0.5320 / 68.10 | 0.4909 / 62.83 | 0.9226× | valid/valid |
| 2/B | 3.7563 / 480.81 | 3.5425 / 453.44 | 0.9431× | valid/valid |
| 2/C | 4.2068 / 538.48 | 3.8349 / 490.87 | 0.9116× | valid/valid |
| 2/D | 3.2539 / 416.50 | 3.2522 / 416.29 | 0.9995× | valid/valid |
| 2/E | 7.2468 / 231.90 | 5.5982 / 179.14 | 0.7725× | valid/valid |
| 3/A | 0.5299 / 67.82 | 0.4912 / 62.88 | 0.9271× | valid/valid |
| 3/B | 3.7562 / 480.79 | 3.5264 / 451.38 | 0.9388× | valid/valid |
| 3/C | 4.2547 / 544.60 | 3.8204 / 489.01 | 0.8979× | valid/valid |
| 3/D | 3.3331 / 426.63 | 3.2606 / 417.36 | 0.9783× | valid/valid |
| 3/E | 7.4432 / 238.18 | 5.7854 / 185.13 | 0.7773× | valid/valid |
| 4/A | 0.5306 / 67.92 | 0.4863 / 62.24 | 0.9164× | valid/valid |
| 4/B | 3.7376 / 478.42 | 3.5560 / 455.17 | 0.9514× | valid/valid |
| 4/C | 4.2823 / 548.14 | 3.8582 / 493.85 | 0.9010× | valid/valid |
| 4/D | 3.2772 / 419.48 | 3.2618 / 417.50 | 0.9953× | valid/valid |
| 4/E | 7.3514 / 235.25 | 5.7381 / 183.62 | 0.7805× | valid/valid |
| 5/A | — | — | — | missing/missing |
| 5/B | — | 3.5219 / 450.80 | — | missing/valid |
| 5/C | — | — | — | missing/missing |
| 5/D | — | — | — | missing/missing |
| 5/E | 7.3922 / 236.55 | 5.7498 / 183.99 | 0.7778× | valid/valid |

具体解析错误、阶段完成标记错误、时间/boot冲突及额外目录在analysis.json中完整保留。

## 原始证据与限制

[逐cell原始目录](../../results/performance) · [配置及代码清单](../../configs) · [G3及运行证据](../../evidence)

TTFT为服务端首token时间减客户端提交时间，不含首token回传；TPOT为首末token间隔除以输出数减一。显存为三卡自有进程采样合计，不称连续精确峰值或论文E-worker容量收益。

六区组t区间依赖对数配对差近似正态，样本量小；固定并发不是到达率SLO。输入/长度/路由通过不保证全量逐token或语义等价。阶段窗口不能求和成独占GPU成本，也不能从on观测反推off关键路径。失败与退化均保留。

本报告需结合实际独立审查、清理及资源释放证据验收；仅保存文件或绘图成功不表示复现完成。
