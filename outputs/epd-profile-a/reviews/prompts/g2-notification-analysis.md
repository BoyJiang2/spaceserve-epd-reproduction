# G2：EPD现有trace通知间隔离线补分析

先读D:/Documents/codex/AGENTS.md，只读，不改文件、不运行实验、不访问GPU。Claude实际usage_limit_reached接替证据同批g4-cuda-report-claude.json。G1受限范围已/root/profile_plan_review APPROVE_WITH_NITS/BLOCKING0，原文待主执行者保存；高EPD>5%仅路径存在性，不执行本新数值分析、不重采。
新增analysis/notification_intervals.py、tests/test_notification_intervals.py。现有trace_analysis.py/旧raw/performance统计不改。
复用G4 helper，新的reader同进程correlation、同线程完整worker range关联；128步P+127D或baselineprefill+127decode，逐rid排序对应128 API通知，逐步核GPU非空/worker及GPU在通知前完成/API原始timestamp一致，缺失整个request列未匹配。源trace SHA/API PID绑定已G4的cuda-analysis.json。
每个匹配API NVTX输出marker间隔分割：全trace实测CUDA kernel/memcpy/memset并集+api.disconnect在CUDA外时长+未解释=总长；无记录CUDA是补集，不能称物理idle或CPU原因。另列targetstep/CPUworker范围/回调到API/marker与api_stamp误差，不重叠相加。真实GPU依赖关键路径未观测，不伪称测出。
三类：稳态D；低EPD第1->2通知同时覆盖P/KV/首D，copy块标签仅时间相关、非rid依赖；baseline高负载其他新请求prefill与既有请求通知间隔重叠，显式别的batch IDs/对应GPU活动。每case期望16*127，匹配/未匹配理由/分布输出。只跑阈值内低EPD+低/高baseline共48请求；超阈值高EPD明确排除。
3项CPU回归PASS，evidence/notification-cpu-tests.txt。尚未执行全数据新分析，G2批准后qjh000 CPU运行，结果再G4/G5。请关注同step绑定/时间分割/报告命名与边界、关联漏计/重计和可复跑性；输出结论/BLOCKING具体行号/NON-BLOCKING/QUESTIONS。
