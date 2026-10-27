# 原313预算内的唯一启动修复：G1/G2分别独立审

只读、不GPU/远端/凭据、不改文件。先读AGENTS和plan。实际模型attempt0 producer53 SHAe3feffa72ca74e9aa49bb0ba16c8bf291a1626effaab2f269ef740f1d41a92c4，MODELS_STARTED controller397914/ctime1793047438.3，exit1，原results/preflight-models/cold-baseline-space/{mps-start,mps-stop}.log与evidence/models-{controller.log,exit.json}已抓回。

失败在MPS start：private control endpoint already exists（numeric stop留下socket）。没有API Popen/加载模型/推理；目录只有MPS启动/恢复日志，没有launch/correctness/profile请求；GPU4零显存/空compute，私有daemon PID238752不存在、state stopped/inode7049731。失败/未知身份拒绝均保留，不重写exit1。

G1请求：同单H20/模型/精度/六负载/313=97正确性+216诊断预算不变，允许一次修复后的完整313，因为attempt0消耗0生成请求；不自动正式，不自动第三轮，再失败保留断点按实际已提交数核算。旧53 source实际逐SHA存work/revision-phase/model-attempt0-source，不覆盖旧raw/marker。新结果仅preflight-models-attempt1，launcher唯一MODELS_ATTEMPT1_STARTED/models-attempt1-exit，CPU输入重核另attempt1文件。fresh预约及08:58止不变。

G2 delta：prune_stopped_mps.py从既有已审旧helper缩为函数，仅在已持host锁、root私有700目录、state stopped/token/pipe、记录PID不存在、无MPS进程、control SOCKET UID+inode精确匹配时unlink单个socket，前后证据留存；不动未知endpoint/他人。测试真实AF_UNIX四种fixture owned/wronginode/live/symlink，独立目录，不碰production。run_models每service start前调用prune，未改numeric18；四文件仅prune调用、输出/marker/input attempt1路径及相应test断言。numeric原18/43consumer不改。

请按分工给G1计划或G2代码实际结论，BLOCKING/建议/范围；仍须目标实际CPU、部署SHA/fresh资源才允许retry。
