# EPD CPU 生命周期：连接地址修正与失败保留

本页仅记录 CPU 运行兼容性和下一次四场景验证准备。**没有新增 GPU、CUDA IPC、native36 或 PD/EPD 性能结果**；性能数据仍见[EPD 独立比较页](../../comparison/README.md)。

## 已发生的结果

producer `529d4173a9ad960a246964974a107853133ec2d1` 已在 qjh003 实际部署：86份运行文件与本地/GitHub 原字节相同，部署 exit 0。随后第一次 CPU 四场景运行在第一场约30.046秒超时，**0/4完成，exit 1，G3不通过**。driver 尚未完成 `ray.init`，没有 `before_actor_create`、ActorID 或创建回执。

真实 stderr 显示传入的 `127.0.0.1:49173` 被 Ray 2.10 改写成 `172.31.35.35:49173`。固定版本的官方 `canonicalize_bootstrap_address` → `resolve_ip_for_localhost` 确实进行这项改写；只给 driver 增加 `_node_ip_address`，仍不能避免 bootstrap 地址被改写。官方函数原文的本地独立复现见[证据](evidence/canonicalization-reproduction.json)。

经另外的单次清理审批，先处理该 driver，再确认没有创建 WAL，随后按原UID/boot/start/root/RUNID和稳定 pidfd 收口其余五个登记进程。**清理命令也保留 exit 1**：最后的全局只读检查遇到了权限受限进程，原时点该进程身份未闭合。独立补充核验在 `1793323320139` 观察到六个登记PID全部消失、本run范围为空、未知候选为空；仅该后续观察的服务例外使用已发布代码验证完整新鲜父链、ctime、cgroup和命令摘要，没有按名字或同UID猜测。该观察通过独立结果审计，不追认先前失败进程身份或终态，不代表未来无限期 quiescence。

失败数据与所有旧封存批次继续保留，不重跑这个run或清理命令。

## 最小修正范围

- 仅 `gpu_count=0` 的私有 CPU head 使用 `127.0.0.2`；driver、父入口和CPU GCS reader统一该地址，driver显式传原生 `_node_ip_address='127.0.0.2'`。
- 三GPU head 的原参数逐字段保持不变；本次未修订或验证其GPU连接策略。没有修改Ray安装文件、退出hook或调度算法。
- 最终只读范围核验复用已有的精确 PAM/SSH 服务身份校验器。未知例外拒绝通过；`cwd`缺失而PID目录仍在，不能算已退出。
- 新部署必须将固定版本的 `tools/` 物化到 EPD sparse checkout，并核验运行代码及这些实际工具字节；旧86文件manifest不能代替新部署证据。

本地 **175项CPU测试＋11项既有服务校验器fixtures通过，0 skip**。新增CPU地址反例在修正前确实失败；这些测试与官方函数AST复现都不启动Ray或GPU。真实修订版四场景尚未执行，源审、精确发布、部署、具体运行审批和实际G3分别记录，不从旧批复制通过。

## 入口与证据

- [CPU父入口](../../runtime/numeric_cpu_lifecycle.py)、[driver](../../runtime/numeric_cpu_driver.py)、[head参数](../../runtime/numeric_head.py)、[CPU GCS reader](../../runtime/numeric_gcs.py)。
- [代码清单](evidence/source-candidate.json)、[175项原文](evidence/cpu-tests.log)、[11项服务校验原文](evidence/service-tests.log)、[修正前反例](evidence/before-tests.log)。
- [真实失败G3](reviews/first-real-run-failure.md)、[实际清理及补充结果审计](reviews/cleanup-actual.md)、[失败终态](evidence/failed-run-terminal.json)、[清理终态](evidence/cleanup-terminal.json)。
- [补充核验原件](evidence/supplemental-scope-verification.json)、[初始失败逐文件inventory](evidence/failure-inventory.json)。
- [首版准备与版本记录](../qjh003-cpu-lifecycle-20261030/README.md)。

本地CPU测试方法与首版相同，仍不授权直接在服务器启动。原失败run的最终下载封包为 **2,611,837字节**，SHA256 `df93f8cb1f0dc865cbf741d4f1820c826c828932bfe4a78001f1d8076ef422fa`，含8份物理原件；66,053,977字节的原始生命周期journal单独保持SHA256 `05888ed58bef4a070010d897b5eebff435def19bc4aec43dcf9a07070a4d2f85`。封包当前本地保留，尚未发布下载资产，本页不提供候选下载链接。

下一次必须使用新的run、命名空间、目录和批准；不会将此失败批标成修订版通过，也不会将CPU通过当作原生跨卡或公平PD通过。
