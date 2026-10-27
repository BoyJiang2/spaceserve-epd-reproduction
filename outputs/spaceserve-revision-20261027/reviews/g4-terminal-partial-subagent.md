# 实际SpaceServe部分矩阵G4

审查者：/root/numeric_g3_review。Claude额度耗尽依AGENTS只读接替；以下原文主执行者落盘。

**实际partial G4：APPROVE_WITH_NITS；BLOCKING = 0。** 批准已完成部分的证据描述；不批准完整54单元复现、发布G5或总目标完成。

已独立只读核验：

- 1713件传输文件bytes/SHA、G3 consumer347项及dataset26项全部匹配；实际producer15/57/18链保持一致。
- 000—047共5760条原始请求：4800正式＋960预热。图片序列、输入IDs、128输出长度、时间戳、正式窗口均通过；吞吐、tokens/s及TTFT/TPOT/E2E P50/P95重算与报告48行数值一致。
- 58039条监测记录中未见foreign或PID归属异常，正式窗最大采样间隔约0.805秒。runtime、RGB、FP16、导入路径、库SHA、MPS身份、预约边界及服务身份未发现冲突。
- analysis的1472项raw sources及14项input sources SHA匹配；完整列出54计划单元及54计划配对，六项缺失，`global_errors=[]`、`intervals=[]`。候选analysis/report SHA与审查提示一致。
- 已实际查看图：48个单次点、六分面；B2的1图C8和4图C1三组均留空，无补零、均值、拟合、CI或裁点。
- 原日志明确在048进入service前触发900秒余量门槛，exit1；没有048推理记录。终态及预约后快照分别记录GPU4释放、MPS stopped、父子进程消失，结论限各采集时刻。

**NON-BLOCKING：** 主报告第15行可直接链接`report/terminal-status.md`，让已知余量门槛与退出原件更易定位。现有组合证据已说明，不构成数据阻塞。

保留全部限制：矩阵未完整、实际位置平衡未全部达成、共享主机瞬态影响未排除；kwargs200704被忽略；decoder仍含visual＋language权重；不证明decoder互斥或off关键路径。本G4不授权自动补六项或新增GPU预算。

**QUESTIONS：无。**

主执行者落实nit：保留受审报告及analysis原字节，在publication-status.md和项目页直接链接terminal-status.md/退出原件，不回写已核SHA报告。G4 analysis SHA a0d68aff7e3b21bade5b04509290dc8dce2ac5a28711efac191f1fdb4608cb9b；report SHA34eee9a20aedc9a4fd9d073f0d446cdb90c18c221e5d030411d4773df2567114。
