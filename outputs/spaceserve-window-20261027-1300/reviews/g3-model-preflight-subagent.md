**实际模型/机制G3：APPROVE_WITH_NITS；BLOCKING 0。**
`reviewed_at_utc = 2026-10-27T08:42:52Z`。仅批准本批固定模型、输入和配置的正确性与机制证据。

独立只读实核结果：

- **版本及完整性：** producer75清单SHA为`d542d1ac…9a138`；75成员、170项numeric consumer绑定、261项实际采集文件（384,109,378字节）全部逐bytes/SHA通过。numeric原producer`b767…60d`及99归档映射保持原身份。runtime Git`83edff…643f`的61部署blob、独立collector Git`6a9dd8…ab35`的5项blob均匹配，未追溯改写模型版本。
- **313次实际请求：** 7 reference＋90 target＋216诊断（120 warm＋96 profile）。97条正确性请求逐条与原始HTTP journal核合；90条target的实际处理后输入IDs、输出IDs及文本均与对应reference完全一致。输出长度、有限且非降序时间戳、请求时间边界通过；C8实际并发达到8。bench/dog/bear/cat及四COCO主题多图顺序语义检查通过。216条诊断原记录的图路径、视觉token数、128输出tokens及时间指标均通过。
- **六次真实服务：** cold/restart各三角色具有不同API/worker身份。实际FP16、TP1、eager、context4096、seq8、prefix cache关闭及MM processor cache关闭一致；native与fork导入路径正确。解耦encoder独立加载675,759,104个visual参数；decoder仍保留visual及language权重。
- **实际encoder stream：** 两个未mask服务为78→78→首次执行78；两个mask服务为78→64→clear恢复78→reapply64→首次执行64。各组PID、stream、GPU UUID一致，64集合为原78的严格子集；加载库路径和SHA匹配。
- **10件trace：** 完整解压、CRC、JSON、大小、SHA及worker PID核合通过，未见SM诊断probe混入profile kernel。独立复算四组CUDA kernel overlap精确匹配：cold-space `490225.5µs`、cold-mask `1248131µs`、restart-space `528877µs`、restart-mask `1282624µs`。
- **输入及资源：** 当前CPU实核2564项与输入manifest所需子集完全一致。以本批实际pin核同本地26件数据原件及4份集成源/processor原件，重新计算20张RGB结果匹配六服务before/after；未沿用历史PASS。私有MPS为100%，pipe及worker/client身份匹配。
- **启动与终态：** booking距启动57.68秒，输入核验距启动401.98秒，均满足freshness。同boot、GPU4完整UUID一致。controller3624713/child3624718从`07:24:42Z`至`07:41:18Z`，实际exit0；终态原件确认父子消失、owned空、GPU4零显存/零利用率、compute空、私有MPS stopped。原零请求失败四件的bytes/SHA及exit1仍保留，未掩盖。

必须保留的限制：

1. `min_pixels/max_pixels` kwargs实际被忽略；本结论针对已验证448×448 COCO输入、每图256视觉tokens。
2. 固定COCO主题及参考一致性不能扩展成通用自然图理解质量保证。
3. encoder mask不证明decoder互斥或完整SM分区；MPS边界快照不证明连续排除所有瞬态外来client。
4. 诊断trace overlap不能证明关闭诊断后的瓶颈、正式性能或收益。

最终Gate至少应绑定：75清单及成员、G2原文/Gate、170 consumer与99归档映射链、261 inventory及全部原件、start/exit/terminal与资源快照、booking/input CPU原件、Git部署及collector身份/命令、零请求失败原件和本审查。所用26数据及4集成源原件也应纳入明确SHA映射，避免只引用外批路径而失去冻结关系。

**本结论不授formal许可；201分钟入场时点已过，本窗口不得启动54项正式矩阵，也不代表完整实验或项目目标完成。**
