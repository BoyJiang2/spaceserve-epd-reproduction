> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-model-runner-prompt.md) SHA256 f26b7a9a4a491f589a74e6b203046307a750f1c475cda8eb672492aa00153385。原数字及解释不变。

Claude独立只读G2小范围：qjh000 7B cold/restart服务预检启动链。先读D:/Documents/codex/AGENTS.md，禁止改文件、GPU/实验、凭据。不审批formal。用户已确认qjh000/Qwen2-VL7B FP16 TP1 eager单H20 GPU0，无需再问。环境已154固定包pip check/CPUimport/FP16计算通过；driver535.161.08 API12020。

只审本批scripts/preflight_model.sh,start_server.sh,baseline_server.py,env.sh和scripts/capture_mps_clients.py,check_correctness.py,cleanup_owned.py,stop_server.py。其余hook独立G2审中，不扩成全项目。

支撑：本批gpu_exclusive/mps_owner/mps_control已由native G2批准（reviews/g2-native-sm-subagent.md及g2-sm-layout-claude.md），残留runID安全修复及Linux实际CPU测试通过；prune_stopped_mps及在preflight_model:37的调用又已Claude G2批准，g2-stopped-mps-claude.md。旧005同版本startup/预检原先G2通过，本批仅换host/root/model固定7B、管理env与新增实际MPS边界采集。不能把旧批准当新host批准，所以本次明确复核上述8文件。

baseline-space/space/space-mask在同一100%私有MPS会话顺序启动GPU0，448策略每图256视觉tokens，4096上下文，prefix和预处理缓存同关，FP16/TP1/eager/生成参数同。7个标准案例（单/多图）+8并发不同图路由，先native保存golden，restarter重用参考。原始输入/output IDs保留，模型语义弱项区分native参考质量，不借此放宽真正路由错误。capture实际MPS客户端/整卡PID来源、所有进程显存、GPU参数/运行配置；诊断Kineto覆盖encoder/decoderCUDA真实活动，不拿诊断速度作formal。等待health有500s上限，失败/TERM按精确同UID/root/runID清理，私有MPS身份符合UID/PID/创建时间/token/pipe inode才stop；残留supervisor持锁。

只有SM_NATIVE_APPROVED才加入mask**诊断**；start_server在REPRO_SM_PROBE=1+G2_MODEL_APPROVED+SM_NATIVE_APPROVED下可启动服务探针，即使SM_EFFECTIVE还没有。诊断不自动写SM_EFFECTIVE/G3，不等于第三组批准。native+实际stream布局/还原G3全部通过后另行决定组。正式driver另G2/G3。

请核公平性、启动/复用golden/重启、子进程清理和MPS实际边界、异常数据保存。输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号+理由、NON-BLOCKING、QUESTIONS。全范围旧审查15min无返回记录g2-model-service-timeout.json，非quota错误非批准；本次拆小且不加载MCP，不改任何用户设置。
