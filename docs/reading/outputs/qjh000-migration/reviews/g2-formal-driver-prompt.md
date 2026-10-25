> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-formal-driver-prompt.md) SHA256 2b1e9c9afe543087853f66ff1046c90146b460444e68755a4d6cbf02599fc354。原数字及解释不变。

# G2：000正式矩阵驱动（机制G3仍是前置）

先读D:/Documents/codex/AGENTS.md；只读，不改文件/跑实验/访问GPU。Claude明确额度失败证据本批g2-model-runner-claude.json及epd-profile-a/reviews/g4-cuda-report-claude.json，按3.2.1接替。
审输出qjh000-migration/scripts/run_formal.sh及依赖audit_formal_case.py,verify_points.py,check_background.py,monitor_gpu.py,start_server.sh,capture_mps_clients.py,gpu_exclusive.py,mps_owner.py,prune_stopped_mps.py。
旧005formal G2批准仅旧主机，本次需新000整体范围独立G2。000cold正在诊断，尚无G3_MODEL_APPROVED/SM_EFFECTIVE/G2_FORMAL_APPROVED，无formal。不得改正在cold调用的脚本；当前只改了尚未执行run_formal.sh。

具体delta与要求：
- 000专属root、同GPU0 UUID/boot、同私有MPS100%、7B FP16 TP1 eager、20warm+100formal*3/128tokens。
- 显式unset REPRO_SM_PROBE/VLLM_TORCH_PROFILER_DIR/REPRO_OBSERVE/VLLM_LIBSMCTRL_PATH；startup record hook双方相同，探针不进formal。
- prune仅验证已停止精确socket；原native/hook/runnerG2批准继续有效。
- ROLES默认为native+space，只有实际G3后写SM_EFFECTIVE才加space-mask；角色列表写points/roles.txt绑定到SHA。不能以原生探针替代服务G3。
- 所有可用组先1/C1、4/C8，完成后写points内层manifest和外层SHA，持锁等待G4_POINTS_APPROVED完全同bytes；verify_points验证外层/内层/每payload，才跑其余4点。不重复正式请求。
- host空闲与UID/root/runID互斥/清理、GPU/MPS边界身份、原RGB、按真实窗口吞吐/所有本项目GPU进程采样内存/foreignPID拒绝。正式前check_background拒绝本project下载/预检/CPU分析，包括父退出孤儿；不会终止外来。
- 实际Linux bash -n通过；tests/test_formal_guards.py复用旧sealed2B原始格式，仅改fixture模型元数据不冒称7B测量，5项PASS evidence/formal-cpu-tests.txt。新MPS idle6项PASS。当前cold出现psutil.wait_procs的pidfd EINVAL，主清理被cleanup_owned兜住无残留；主执行者待cold结束再修bounded polling并单独G2，此批准不自动覆盖该未来delta。

请给APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，具体BLOCKING/文件行号/NON-BLOCKING/QUESTIONS。本次可批准条件化driver，但任何formal启动仍须真实G3+关闭全部CPU准备/分析并重冻结代码SHA；不允许未完成G3绕过。
