> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-model-hooks-prompt.md) SHA256 7f9397dfd64f97a8444bbcd6a10aba070c49dd7d3ba94515552810cc886c2163。原数字及解释不变。

Claude独立只读G2小范围：qjh000服务内SM探针与启动时设备hook。先读D:/Documents/codex/AGENTS.md，禁止改文件、实验/GPU、凭据。不审批formal。模型/主机已用户确认：Qwen2VL7B FP16 TP1 eager单H20 GPU0，固定Space66de079af423/vLLM0.7.2/Torch2.5.1cu124/tf4.49。环境实际READY、154依赖pip check和FP16计算通过。

请只审以下8文件，范围不要扩成全项目：outputs/qjh000-migration/scripts/record_device.py,install_device_record.py,install_service_probe.py,service_sm_probe.py,service_sm_probe.cu,test_service_probe.py；source-evidence/core-with-diagnostics.py,__init__.py。CPU实际evidence/model-cpu-checks.log：源码应用/二次SHA相同/first-execution mock/语法通过。首次import sys注释count造成patcher拒绝，失败保留后已修；无GPU模型启动。其他runner/MPS/清理另G2，不需重复审。

仅startup记录实际encoder/LM参数device/dtype/components/UUID/MPS与实际加载libSHA；native和fork同样hook，计时不运行。core在实际encoder_stream原官方mask之前/之后、零mask恢复/原mask重施采样SMID；首次真正worker execute_vision_encoder采样torch.cuda.current_stream，再恢复原方法，必须匹配同PID/stream。formal没有REPRO_SM_PROBE flag，所以仅诊断触发。helper sm90原生so用实际stream句柄，不依赖PyTorch扩展；nm-D实测无cudart导出，见evidence/helper-exports-before.txt。服务会复制逐位布局实际校准的同一个so，SHA逐字节确认。源码官方wrapper确认[0,0,0,0xfff]顺序无误，decoder mask仍注释，不能声称互斥SM划分或完整论文SIS。

原生SM G3 Claude session7c380db4...通过6次78→64，仅可行性；布局逐位代码及精确已停止socket清理G2同Claude已通过，实际布局G3另做。此G2仅代码，不写SM_EFFECTIVE或第三组验收。请检查最小性、实际stream证据设计、hook还原/正式开销、公平性、异常边界；结论APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号+理由，NON-BLOCKING、QUESTIONS。

先前全范围模型G2超过15min未返回，记录reviews/g2-model-service-timeout.json，**不是批准或quota错误**。本次明确拆小；MCP不需要，本进程只开放Read/Grep/Glob，不改用户任何配置。
