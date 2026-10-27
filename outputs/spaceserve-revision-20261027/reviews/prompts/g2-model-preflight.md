# Space模型/实际服务预检 G2

只读，不改文件、不远端/GPU/凭据。AGENTS规定Claude额度耗尽用户授权subagent独立审查，证据work/repository-upload/g1-plan-claude.json。

读取plan.md与next-stage-handoff.md。当前实际numeric G3 APPROVE0，producer13a553...清单18项不变；模型/正式请求0。本次新model_guard.py在原numeric锁/部署proof上额外要求独立G2_MODEL_CODE_APPROVED与model-code-manifest，numeric原G2/18成员/40G3绑定完全保留，不覆盖或静默迁移。模型scope仅preflight-models，不授权正式54cell。

审scripts/run_models.py、model_guard.py、model_launcher.py、verify_model_inputs.py、correctness_suite.py、check_mask_sets.py、test_model_control.py、test_correctness_suite.py、test_mask_sets.py。以及实际会用的新root迁移helpers baseline_server.py（新增actual import metadata）、start_server.sh、record_device.py、service_sm_probe.py/.cu、benchmark.py、capture_mps_clients.py、capture_runtime.py、rgb_cache.py、check_rgb_cache.py、wait_for_traces.py、analyze_trace.py、owned_processes.py。迁移原快照在configs/relocated-helpers.json和relocated-guards.json，最终以后续新model manifest为准。

97正确性（7reference+3组×2启动×15target）+216诊断（6×20warm+16profile）=313，不加点、不第三轮或自动正式。模型前CPU重哈希16模型/26dataset/fork与native源和CUDA扩展，实际tokenizer冻结两图数120请求清单，fresh预约才启动。device/FP16/actual import、native/forkcache参数/MPS100相同；encoder mask strict子集/clear恢复/reapply相同/首次实际stream一致，不要求decoder互斥。

MPS daemon用独立run identity，API/worker用service identity，避免owned stop直接杀MPS；每次start前持久intent，任何启动异常finally stop(service)后recover-stop(mps)，未知不信号。全程截止前120秒guard，预约不足停止保留，不缩验证。profiling在正确性后独立20+16，trace CRC/workerPID齐后关闭服务，解耦两组必须实际kernel overlap。phase完成marker不自行授予G3。

请输出G2结论/BLOCKING/NON-BLOCKING/QUESTIONS，重点检查预算、cleanup/信号、proof bindings、公平参数和机制证据。若批准，仍需实际目标CPU测试、部署逐SHA、fresh预约/空闲后才允许preflight-models。
