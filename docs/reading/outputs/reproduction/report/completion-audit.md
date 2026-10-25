> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/reproduction/report/completion-audit.md) SHA256 9bd822a97df2466f035f268ec1b84f1621cd299e7b460835ac336208eddd17a6。原数字及解释不变。

# 完成标准逐项核对（G1–G5通过，收尾校验通过）

2026-10-23。这里区分技术检查与项目最终验收。技术审计通过不能替代独立审查批准；用户已授权Claude额度耗尽时由独立subagent接替，当前 `goal_complete=true`。

| 要求 | 已核实证据 | 状态 |
|---|---|---|
| 固定官方代码、模型与环境 | configs/ 版本及模型清单；两台 evidence/ 的 native-source-manifest、model-manifest、freeze、运行库哈希与加载路径 | G1–G4审查通过；版本与覆盖已披露 |
| 修复 H20 cuBLAS 兼容问题 | 两台 blas-after.jsonl 四种 FP16 shape 数值正确；epd/baseline-runtime 中实际加载 cuBLAS12.4.5.8；旧故障 GDB 日志保留 | 技术检查通过；依赖覆盖已披露 |
| 两台 CUDA P2P / 原始 embedding / KV 数据一致 | 各六方向16MiB完整哈希；两形状六方向各三次KV；每台实际60553 blocks补测三次；embedding各三次 | 共78次KV、6次embedding通过 |
| 冷启动、重启后并发路由及服务正确性 | 原H20首次启动与一次重启各单/多图及C8，共90案例；RGB补测另60案例，基线固定检查覆盖首端点，缓存/正式请求覆盖全副本 | 原90+新60均通过；历史sapphire另44（含7诊断EPD） |
| 公平三卡基线与完整矩阵 | 原qjh003十二配置、qjh005四配置；首单图经G2批准纯RGB预载后两台各成对补测600正式请求；16份实际缓存快照均匹配20源图，PID/设备/boot/库路径一致 | 技术审计及G4独立复算通过；B1已关闭 |
| 每配置20预热、100正式×3 | 原11矩阵+补测4矩阵，归档50配置15000正式1000预热；选用46配置13800正式，其中1800仅诊断、12000有效测量；另1200原低负载保留但被替代 | delivery-audit.json技术检查通过；source_case明确来源 |
| 原始请求可复算与输出差异披露 | summary.csv/json、output-comparison.json；有效配对5400，另1800仅诊断；输入顺序与处理后IDs一致；未宣称全部正式输出等价 | 离线核对通过，语义差异未逐项评估 |
| 机制边界与历史失败 | SpaceServe overlap/mask原始记录；4090 SM mask不支持；sapphire3损坏记录保留，不作性能结论，不断言IOMMU唯一因果 | 最终报告已说明 |
| 报告四个问题、脚本/补丁/原始数据/图表 | README.md、report.md、scripts/、patches/、data/、evidence/、report/ 图表 | G4/G5 APPROVE_WITH_NITS；交付目录完整性核验通过 |
| 不终止他人任务、不改共享主机配置 | 本项目 stop helper及运行日志；两台结束计算进程列表为空；无IOMMU/内核/驱动改动或主机重启 | 已记录执行边界 |
| G1/G2/G3/G4审查 | reviews/subagent-g1-g2-20261023.md、subagent-g3-20261023.md、subagent-g2-rgb-followup-20261023.md、subagent-g2-full-replay-20261023.md、subagent-g2-rgb-20261023.md、subagent-g4-20261023.md、subagent-g4-cache-fix-data-20261023.md及处理记录；历史REQUEST_CHANGES保留 | G1/G3/G4 APPROVE_WITH_NITS；G2 APPROVE；B1关闭，BLOCKING为0 |
| G5 APPROVE / APPROVE_WITH_NITS | reviews/g5-claude-final-20261023.md，Claude实际G5 | APPROVE_WITH_NITS，BLOCKING为0；收尾条件已落实 |

附加核对：raw-preservation-audit.json确认原归档189文件未变，仅4个validity元数据更新，逐请求数据没有改写；timestamp-order-audit.json检查全部16000条预热/正式响应时间戳有限且非递减；h20-cache-continuity.json以固定worker PID、顺序请求与无淘汰字典源码支持原后续负载缓存持续填满，不将其解释为直接测量的缓存命中成本。

后续顺序：G2已事前批准具体RGB修复，补测和技术审计完成；G4已APPROVE_WITH_NITS，B1关闭；G5已获Claude APPROVE_WITH_NITS，按其条件更新记录并最终核验完整性归档。不因晚引入文档伪造事前批准，不删重复或盲目重跑其他配置。

最终收尾：候选到交付的data/evidence/configs/patches/scripts全部字节一致，五个主要统计/验收文件逐字节一致；954个文本文件凭据特征扫描未命中。968文件收尾验证包完整SHA与CRC通过，记录在closeout-validation-integrity.json；此后仅同步真实完成元数据和新增验证记录。最终包再次校验，完整差异、外层SHA及CRC输出在ZIP旁reproduction-h20-differences.json、reproduction-h20-integrity.json及.zip.sha256；没有重跑或改动测量审计。
