你是Claude独立只读审查者，先读D:/Documents/codex/AGENTS.md及本批plan.md。禁止改文件、运行实验、GPU、凭据。G2：qjh000固定7B冷启动/重启服务预检及实际SM stream诊断，**不审批formal**。用户已确认主机/模型，不再询问。

本批目录outputs/qjh000-migration。000 H20 GPU0 UUID GPU-d1b595ce-0b57-cdee-c1c0-9b1051aaa07e、boot a9617eaa-1638-45fc-8997-a62b528e8f30、Driver535.161.08/API12020。Python3.10.12+torch2.5.1/cu124/vllm0.7.2/tf4.49.0已实际CPU导入、pip check154全兼容、FP16计算PASS；evidence/runtime-probe.json等。固定Space66de079af423、mysmctrl6ff57356。原生G3已由Claude session7c380db4-09f7-4607-8a3e-67849dfd43a5 APPROVE_WITH_NITS，6次78→64，非12TPC或资源比例，尚不批准第三组；逐位布局代码单独G2审中，结果另G3。

当前仅做cold/restart正确性和diagnostic profile。主文件：scripts/preflight_model.sh,start_server.sh,env.sh,baseline_server.py,check_correctness.py,capture_runtime.py,capture_mps_clients.py,monitor_gpu.py,stop_server.py,cleanup_owned.py,gpu_exclusive.py,mps_owner.py,mps_control.sh,analyze_trace.py。旧005同版本基础脚本G2已APPROVE_WITH_NITS/BLOCKING0，见outputs/spaceserve-h20-7b/reviews/g2-basic-startup-subagent.md等；新host/路径必须重新审批，不能套旧批准。

新机制证据代码scripts/record_device.py,install_device_record.py,install_service_probe.py,service_sm_probe.py,service_sm_probe.cu,test_service_probe.py，CPU实际evidence/model-cpu-checks.log（首次失败log保留，import sys注释导致count多于1，已最小修复），patcher真实源应用及二次SHA相同、Python/bash语法和first-execution mock通过，无GPU调用。source-evidence/core.py为实际兼容前源；core-with-diagnostics.py为本次实际部署待测源；__init__.py为官方SM wrapper，能直接核mask参数顺序/仅encoder mask，decoder mask注释保留。

诊断：baseline/space/space-mask顺序，在同一个100%私有MPS。只有SM_NATIVE_APPROVED才考虑mask诊断；start_server允许G2_MODEL_APPROVED+native G3+REPRO_SM_PROBE=1时在SM_EFFECTIVE缺席下进入诊断，不等于第三组验收。实际encoder stream原mask调用前/后SMID、零mask恢复、原mask重施；通过startup-only worker hook在第一次真实execute_vision_encoder采样torch.cuda.current_stream，同PID/stream指针须匹配；之后恢复原方法。正式关闭flag，probe不运行。实际加载lib路径及SHA记录，需与原生库一致。service helper将复用实际布局校准的同一二进制，检查SHA后复制至build，不能用未校准库替代。服务预检不自动写SM_EFFECTIVE或G3批准。

对齐FP16/TP1/eager/4096上下文/输出参数/448图像256视觉tokens/图/缓存与单GPU预算；7B单/4图标准+8并发路由，与原生fixed基线比。保留实际输入IDs/输出IDs、device参数、MPS实际客户端及target GPU身份、所有进程显存。Kineto两个真实worker CUDA kernel交叠只作机制证据，不拿profile测量当formal。清理仅同UID/精确runID/MPS token，自有残留保留host锁；不动他人。

检查公平性、实际stream证明是否充分、原生与fork差异、hook是否偷偷改变formal、首次正确性/重启、异常清理与版本。请输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号+理由，NON-BLOCKING、QUESTIONS。G3服务与formal仍需另审。
