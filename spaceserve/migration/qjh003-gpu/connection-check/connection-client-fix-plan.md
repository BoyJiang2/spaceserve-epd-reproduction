# 仅正确性客户端连接复用修复候选

旧f5ec run保持实际124尝试/123响应/一次C8 ServerDisconnected；native/解耦冷启动各15正确性+36诊断通过，mask组15尝试14响应，restart未启动。MPS stopped/GPU0显存0，独立numeric数值成功不能冒称完整model G3。

现有固定aiohttp3.14.5池keepalive默认15秒，Uvicorn0.54默认5秒。请求时间与首C8触及5秒空闲边界一致，但没有packet/socket原始日志证明根因；连接复用只是候选解释，不归因SM数值或实现调度。

先CPU-only真实127.0.0.1临时端口故障注入：在重用已有连接时模拟对端断开，保持POST计数且禁止retry，比较默认池与force_close=True。只对correctness_suite的一次ClientSession构造增加TCPConnector(force_close=True)，共同作用reference与三个role；模型输入、并发、token数、检查阈值不变。profile/formal benchmark和API服务器配置不修改，因此不能用本修正宣称正式性能改善。

新增有界CPU回归和既有共享资产7+15协议测试先失败后通过；原实际失败保留。通过G1/G2/G5、指定Git source部署、目标CPU60、新numeric/G3和新model G2后，才一次完整新313；每请求无重试，失败停。313是新修复版本的独立验证预算，不拼旧结果或忽略旧失败；1800+120且现预约仍09结束/08:58收口。本窗正式54禁止启动。
