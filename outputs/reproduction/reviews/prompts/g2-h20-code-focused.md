独立只读审查，仅Read/Grep/Glob；不要改文件、运行命令/实验/SSH/GPU或读取凭据。项目根 D:\Documents\codex\2026-10-23\new-chat-2；先读 D:\Documents\codex\AGENTS.md。

本次仅G2代码补审，既有实验无事前Claude批准。不要宣称补审是事前批准。重点读 outputs/reproduction/scripts/{benchmark.py,baseline_server.py,start_server.sh,run_matrix.sh,run_epd_h20.sh,preflight_epd_h20.sh,apply_epd_compat.py}，以及 reviews/h20-replay-differences.diff、report/h20-script-provenance.json。必要时读 scripts/postflight_epd_h20.sh、probe_epd_kv_ipc.py、probe_epd_embedding_ipc.py。不审全部日志或报告统计；资料不足指出明确缺口。

同机三卡1:1:1对三完整副本，MiniCPM FP16 TP1，同请求/精度/eager、128输出、20全局预热、100正式×3。核心压测、服务、补丁与探针的两主机归档快照及当前版本哈希一致。流程/安装四脚本有已披露diff：后整理版本将实际分别执行的BLAS、embedding、runtime、postflight步骤串联，不能说旧实验已使用新版流程。execution-helpers内保存实际watch/collect辅助脚本。

检查多图路由、timestamp/长度/异常、分发公平性、代码是否给目标不当优势、重放命令是否遗漏步骤、patch最小性、进程清理边界。已发现首个单图配置预热后RGB缓存覆盖EPD20张，基线每副本7/7/6张，详见reviews/h20-fairness-facts.json；不应声称完全相同初态。请评需否补测以及最小修复，不自行改变用户固定预热20。

最多20次只读工具调用，不执行计算命令，输出G2 APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES；BLOCKING（文件:行、理由、最小修复）；NON-BLOCKING；QUESTIONS。若无法验证请明确，不循环尝试未授权工具。本次不替代G3/G4/G5。
