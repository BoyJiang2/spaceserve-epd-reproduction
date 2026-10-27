# 本批终态与缺项

正式54计划单元中，000–047完成并经本地分析有效；048–053未执行。实际记录为4,800正式＋960预热。完整矩阵、完整顺序位置平衡及总体区间均未达成。

原同一控制器ID `6e1efdd0356e4551ab50c0d301122f03` 的 [退出原件](../evidence/formal-exit.json) 为exit1；[原日志](../evidence/formal-controller.log)在048进入service时抛出 `insufficient time for a formal cell plus cleanup`。这是原900秒新单元余量门槛的实际错误记录，不是048已有推理结果或新的性能失败。没有缩请求、补跑或跨窗口拼接。

[终态CPU取证](../evidence/formal-terminal.json)于2026-10-27 00:45:53 UTC（北京08:45:53）核实同一父子消失、自有root进程空、GPU4正确UUID/零显存/compute空、私有MPS stopped。此为观察到释放的时间，不将其当退出瞬间。预约只读API09点前核实原本人窗口仍至09:00，08:58边界未放宽。

完整逐请求、失败/空目录相关文件、runtime设备、MPS原件均纳入[完整1709成员清单](../evidence/formal-files.json)；加四取证原件共1713传输文件。首次网络中断保留；新目录仅复用117份exact bytes/SHA，其余四路只读抓回，四路exit0后全量SHA合并通过。该传输事实不是G4批准。

[实际候选报告](formal-terminal-reviewed-candidate/report.md)包含全部54计划状态及54计划配对，partial无总体CI/均值拟合；仅展示有效单次原始值。最初actual图顶部留白不足的候选另保留在formal-terminal-candidate，不用于最终展示。所有收益/退化保留；decoder互斥、off因果瓶颈、论文完整调度均未证明。缺项须等待下一有效窗口及具体审查，不自动增加预约或GPU预算。
