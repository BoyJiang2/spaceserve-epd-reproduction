# G2：显存采样归属查询修复

实际审查者：独立subagent /root/profile_runner_review；Claude额度失败接替依AGENTS3.2.1，范围见g2-memory-sampler-prompt.md。

结论：APPROVE_WITH_NITS，BLOCKING0。

已只读核对新旧monitor、五项Linux CPU测试及CPU计时证据，并从失败包原始数据独立复算：1746条采样，周期中位0.396067秒、最大0.523900秒，第二重复起始gap0.310766秒确实超过未修改的0.3秒阈值。

新实现逐次分类NVML实际返回的全部PID，不缓存归属；API树使用PID和创建时间身份，MPS要求同UID和私有pipe。新增PID每轮检查，进程消失/权限不足归入foreign，保持失败关闭。schema、NVML指标、100ms sleep及审计阈值保留；CPU查询下降解释符合，但不能保证真实GPU采样周期。

NON-BLOCKING：fixture stdout ResourceWarning建议关闭。

可保留失败包、隔离旧formal及runtime记录、重新冻结实际源码SHA后，从首配置执行相同矩阵；失败case不得复用。未变模型/SM G3无需重做，points独立G4门槛仍有效。审查者未修改文件、访问GPU或执行实验。

Codex处理：已关闭fixture stdout，去掉未使用time import；同5项Linux CPU重新执行全PASS且无ResourceWarning，evidence/monitor-ownership-cpu-tests-clean.txt；原警告及最初部署失败均保留。审计阈值及模型/负载/请求设置无改动。仅据此批准已审采样delta，后续正式数据仍待G4。
