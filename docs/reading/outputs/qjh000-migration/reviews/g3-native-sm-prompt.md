> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g3-native-sm-prompt.md) SHA256 52da7fc45ba04aaa7d96faf10412dc0ce6b98cf808af770bc6a9fc415dfce4b5。原数字及解释不变。

你是独立只读审查者Claude。先读D:/Documents/codex/AGENTS.md与本批plan.md，禁止改文件、执行实验、访问GPU、读取凭据。Gate G3，仅qjh000原生SM可行性，不包含7B服务或正式性能。

目录D:/Documents/codex/2026-10-23/new-chat-2/outputs/qjh000-migration。
脚本scripts/preflight_sm_h20.sh、probe_sm_mask.cu、mps_owner.py、gpu_exclusive.py。G2原文reviews/g2-native-sm-subagent.md，唯一runID残留问题已修并CPU实测，BLOCKING0。CPU日志evidence/cpu-lock-test.log、syntax-check.log；actual source hashes native-approved-code.sha256。

新host qjh000，8H20，驱动535.161.08，DriverAPI12020，nvcc12.8编sm90机器码；固定libsmctrl6ff57356968a3f04158b9273aa881ee6bdf04229。results/sm-feasibility为本次完整真实结果：各3次无MPS和私有MPS，检查每次jsonl/stderr/exit-code、MPS身份及停止、processes-after与COMPLETED、固定库revision/binarySHA。原生unmasked78、masked64，不能直接解读为资源比例/模型收益。

请判定是否支持“本机固定库对实际原生stream掩码观察到SM集合缩小”的限定事实；actual服务encoder_stream还须新G2/G3实际验证，不能据此生成第三组批准。不要将旧qjh005 API13000不支持结论套用此机。输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号+理由，NON-BLOCKING，QUESTIONS。
