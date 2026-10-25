> GitHub阅读副本：仅修正链接；[封存原文](../../../../outputs/epd-followup/source-notes.md) SHA256 4299a7b5cb6208354222e33768b0b9c2c13b4138ed9fd61b1774463f646299dc。原数字及解释不变。

# 事件及token打点的源码核对

此处是待G3复核的源码事实，不是新的GPU profiling结果。完整commit、原始Git blob和重放后SHA见source/replay-manifest.json。源码从本地官方bundle导出，仅分析副本叠加第一轮归档的H20最终合并补丁；未SSH、未导入模型、未执行GPU代码。Windows导出产生的换行已恢复原Git blob字节；仅api_server.py与llm_async.py有预期补丁变化。

1. `source/epdserve/lifetime.py:68–69`：事件默认用time.perf_counter；`orchestrator.py:249–266`检查dont_add_if_dup时用Enum成员查询，而字典保存event_type.value字符串。`engine_decoding.py:303–308`每个解码迭代再次调用DecodingBegin；因此相同字符串键覆盖。隔离AST测试执行实际callback两次，dont_add_if_dup=True时字典仍只有一项、timestamp变为第二次值。所有事件类型都采用后写覆盖，是否重复调用另按源码逐项核对。它不是追加多个同名记录，也不是可靠的第一次D调度时间。dict初始化在orchestrator.py:129；Finished在最后yield之后记录，不用于阶段跨度；IRP关闭，本协议不适用分片键路径。
2. `engine_context.py:335–343`先记录ContextEnd，再回调该请求第一个StepOutput；之后请求进入context_bridge_queue。`engine_decoding.py:255–273`记录KV迁移调用跨度。第一token来自P的设计顺序本身也会使D事件晚于它；须结合记录是否靠近最后token来支持覆盖解释，不仅看“晚于首token”。
3. `orchestrator.py:245–246`虽然给StepOutput.timestamp赋值，随后入队；226–232行在消费队列后yield，因此API观察时刻不早于callback。实际API返回的timestamps来自 `api_server.py:140–144,158`：消费异步生成器后，先await request.is_disconnected，再取time.perf_counter。不能把响应里的时间戳直接称为该orchestrator callback时间，更不能称GPU完成时间。这个每token的API等待是后续profiling候选，不从现有记录定量归因。
4. `source/baseline/*`四份实际归档适配器的generate函数AST一致。基线在vLLM异步输出yield后取perf_counter，若一次yield新增长度多于1，会为多个token填相同时间戳；与EPD相同的只是服务输出通知这一观察层级，具体callback/轮询路径不同。须保留零间隔和重复时间戳；合并通知不能被解释为零GPU执行时间。
5. 只有EPD保存lifetime_events；基线没有等价阶段事件。CPU接口跨度只描述EPD，不作跨系统kernel/通信带宽比较。分析输出的窗口重叠数由同端点首末输出通知重建，不是实际在执行batch的请求数。

原始decode覆盖说法在历史报告已有文字，本批用固定源码和隔离CPU测试提供具体证据，不改封存报告。完整数据尚未运行，观察比例待G2批准后生成，源码语义待G3独立批准。
