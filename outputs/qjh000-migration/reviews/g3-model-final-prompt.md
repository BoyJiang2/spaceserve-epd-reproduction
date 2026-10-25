# G3最终：cold与restart三组机制

只读，先读AGENTS，Claude额度接替同本批。承接你的有效cold预审，不重做已核cold。禁止改代码、跑GPU或发送外部消息。
restart PID4055241已三role及全局COMPLETED、退出0，MPS stopped、GPU0表空，批准代码SHA及SM二进制校验通过。
实际新包work/preflight-restart-complete.tar，SHA333026ecdfb93698bbf244f9efdcdbad2bc77d6af7904810cb007ce09492a466，448MiB；抓回/解包后文件results/preflight-restart/和results/runtime-devices/preflight-restart-*，evidence/model-code-check-after-restart.txt、launch日志。主执行者会确认本地SHA/解包完成后请你接着读。
请核三role重启各7标准+8并发输出/input/routing/RGB，并绑定同一cold的7b-native-reference；全部worker/API/MPS重启身份与cold不同、物理UUID相同、FP16/参数真实放置/SM库SHA/所有进程显存证据；cold/restart同一mask实际stream before/after/zero/reapply/first，原生布局减少14SM一致，不声称TPC数或资源比例。
5份restart原始gzip导出CRC/SHA/worker身份和实际CUDA overlap，需要相对时间核对，不能只信自动JSON或HTTP返回；辅助probe在profile前发生。公开实现只限制encoder，不是互斥decoder partition/完整SIS；LM仍保留visual权重。MPS边界不是连续全时排他，formal另外有采样/后台守卫。
核结束clean/GPU空、源代码SHA冷启后和重启后一致，诊断形式20warm+16不计正式数；历史失败归档保留。正式driver G2已有有效条件化批准，服务G3通过后主执行者才创建G3_MODEL_APPROVED及SM_EFFECTIVE/冻结formal全部code/确保无其他项目CPU和GPU工作。

输出最终G3 APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、具体BLOCKING、NON-BLOCKING、QUESTIONS，明确是否足以验收第三组有效SM。不自行写marker或启动formal。整体goal仍active。
