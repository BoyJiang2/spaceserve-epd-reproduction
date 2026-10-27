# G2 新窗口CPU stage与runtime候选

/root/profile_instrument_review 原文：

G2：**APPROVE，BLOCKING 0，NONBLOCKING 0**，限候选代码范围。

已核对55份来源 SHA、当前56脚本清单及迁移差异：除已声明的 root/Ray/stage/时间替换、新 booking ID和预算记录外，未发现额外语义变更。stage 保留独立复制、源前后核验、内部链接重定位及拒 hardlink；runtime 保留新预约、freshness、清理截止、身份和 G3 门槛。201分钟入场检查实现为额外拒绝条件，不放宽原守卫。

执行仍须满足：13点后 fresh 预约/资源核查；目标 Linux CPU 测试无 skip及真实 TERM/ALARM通过；复制清单匹配固定 `504760…`；另行冻结部署 manifest、签新 G2并完成新 G3。预算策略须待独立 G1批准。本结论不授权提前部署或 GPU 运行。

本次未运行代码、联网、访问凭据或改文件。

主agent后续：G1预算窄审已通过；记录标签/decision_utc小delta另G2补核，不将旧批准冒称包含未审增量。尚未远端部署/GPU。
