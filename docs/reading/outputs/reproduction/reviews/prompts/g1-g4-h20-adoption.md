> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/reproduction/reviews/prompts/g1-g4-h20-adoption.md) SHA256 ed9c7ba9b0eafb09f4711af00d517edf47073c1730f1b95a9f761b69328c80f4。原数字及解释不变。

你是独立只读审查者。只读本地文件；不要修改文件，不要调用 SSH、GPU、实验、安装或网络工具。不要读取凭据、用户家目录配置或会话原文。

项目根目录：D:\Documents\codex\2026-10-23\new-chat-2
首先阅读 D:\Documents\codex\AGENTS.md。

审查范围：G1/G2 已有 H20 计划与脚本的补审、G3 两台机制验证及 G4 已归档 qjh005 数据。实验在本轮用户提供这份 AGENTS.md 之前已经启动，没有事前 Claude 批准，不能声称补审是事前批准。qjh003 全矩阵尚在运行，本次不审其未归档性能结果。请判断已有证据与流程是否足以继续归档和分析，指出真正影响有效性的缺口。没有必要仅因新文档晚于启动就重跑有效测量，但发现实现/有效性问题必须明确阻断。

关键设定：MiniCPM-V-2_6 FP16 TP1，同机三 GPU E:P:D=1:1:1，对照同机同三卡三个完整模型副本；003 为图数1/4×并发1/4/8，005 为1图C1、4图C8。每配置20预热+3×100正式。目标输出128tokens，固定 COCO 请求与处理，关闭动态角色切换和请求内编码并行。两边统一将 cuBLAS12.1.3.1 改为12.4.5.8，解决已独立复现的 H20 FP16 SIGFPE；其余主要依赖固定，torch元数据旧声明与实际加载差异有披露。

请分批阅读以下实际文件，无需倾倒逐请求全部原文，可抽查：
- outputs/reproduction/goal.md、README.md、scripts/run_epd_h20.sh、preflight_epd_h20.sh、bootstrap.sh、fix_h20_cublas.sh、start_server.sh、baseline_server.py、benchmark.py、run_matrix.sh。
- scripts/audit_matrix.py、audit_h20.py、compare_outputs.py、summarize.py、probe_h20_blas.py、probe_epd_embedding_ipc.py、probe_epd_kv_ipc.py、capture_h20_runtime.py。
- patches/ 内 EPD补丁及 evidence/qjh005/epd-compat.patch。
- report/qjh005-acceptance.json、report/experiment-status.json、evidence/qjh005/{correctness-checkpoint.json,baseline-runtime.json,epd-runtime.json,blas-after.jsonl,embedding-ipc.json,kv-actual-cache.json,native-source-manifest.json,model-manifest.json,runtime-libraries.sha256}。
- evidence/qjh005/preflight-20261023T002353Z/ 内通信与平台证据、evidence/qjh005/build/ 原生编译参数。
- data/raw/qjh005/{epd-h20-qjh005,baseline-epd-h20-qjh005}/ 内 matrix-config、runtime-config、validity、单配置config、summary以及逐请求数据抽查。
- evidence/qjh005/used-scripts/ 保存实际执行版本；canonical 脚本的通用化/归档补充不应被误当成旧实验已经使用。实际日志在 evidence/qjh005/logs/。
- work/qjh005-summary.json 和 work/qjh005-output-comparison.json（本地分析中间结果）。

现状：005 两个负载点各系统共1200正式请求，零失败；吞吐EPD/基线约0.93、0.95，不宣称加速。固定45服务用例输入输出token一致；正式600对输出589对完全一致，报告必须区分固定用例与正式生成差异。纯CUDA六方向16MiB、原生KV39copies含实际N60553、embedding3copies、BLAS4shapes均已过本地独立审计。两机器总90固定服务用例。旧sapphire3的1800请求仅诊断，不能纳入性能结论；裸机DMA-FQ与数据损坏同时存在，未有维护前后因果实验。

重点：同GPU预算与请求分发公平性、缓存/预热/统计口径、机制证据、记录是否泄露凭据、真实使用版本与交付脚本一致性、AGENTS变更记录是否如实且可执行。不要把不存在的文件或未查阅内容当作已验证。

输出：分别给G1/G2/G3/G4结论 APPROVE / APPROVE_WITH_NITS / REQUEST_CHANGES；BLOCKING列文件:行号、理由、最小修复；NON-BLOCKING；QUESTIONS。不确定请明确。报告整体尚未完成，G5不在本次范围。
