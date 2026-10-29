# G1 — 直接 Node head 补充 v3

审查者 `/root/epd_pd_followup`；UTC 2026-10-29T07:26:43Z。

**APPROVE_WITH_NITS / BLOCKING 0，仅批准本地完整实现范围。** v3可取代v2的非block CLI启动方案；不批准真实CPU/Ray生命周期试验、远端部署或GPU。原v2/初审及处方不改。

精确计划SHA256：`a0337a8b2d56204fc3aa02e47c8f33264663ed661789c7027b9f764bb8d2a3f8`。

本轮实际读取RayParams完整构造参数及文档，`ray-parameter-2.10.0.py` SHA256 `1242f4110da8f8acafeb1a6cd816addc8a8f322aa3f56fad5bf23cdbe3e1a0f2`，本地git hash-object为`1770dd2fa00d9652eab99855c8010d4130c9fb43`，与声称官方同tag证据一致。Node/services源码与前轮已核blob沿用，本轮再读services Popen后返回部分，未执行任何源码。

## 认可的设计

直接Node显式head=True/shutdown_at_exit=False/spawn_reaper=False，与已核非block CLI调用一致，避免CLI退出前取daemon身份的额外竞态。固定版本三文件实际SHA门槛、RayParams固定资源/loopback/temp/端口与无monitor等选择有对应原文参数，不依赖猜API。

小启动区间包装services.start_ray_process，返回实际Popen后立即登记并持久化；不把整个Node构造或网络等待放入信号屏蔽区，构造失败/未知进程仍失败且禁止actor/IPC。这是必要的小桥接，不需要扩成进程框架。all_processes只提供直接daemon，后代/agent还需实际父链注册，不能凭UID/root/名字认领。

释放核心仍由supervisor持有；driver独立connect、WAL完成后才copy、按importer实际退出与NVML确认后再source/daemon，保留1680+120与故障未确认终态。真实CPU Gate明确改测本Node路径，未通过不开放GPU入口。预算/模型/载荷/36/零重试与selected待接齐不变。

## 两项实现时需落实的小点（交 G2 核，无需新架构）

1. **启动信号屏蔽不能无意改变child信号语义。** 在父线程pthread_sigmask阻TERM/INT/ALRM后Popen，child通常继承该mask；已核services预执行函数只是额外阻SIGINT，并未解除父传来的TERM/ALRM。实现须明确让child保持原Ray预期mask（例如采用不向child传播屏蔽的有限信号延迟方案，或精确恢复child原mask的最小受审hook），不能以“父finally restore”证明child也恢复。真实CPU Gate应核child实际SigBlk、TERM/KILL路径，不能只mock父mask调用。原wrapper命令/fate_share及Ray原SIGINT策略保持。
2. 文案中的`/proc/task/<pid>/children`应在实现使用实际Linux路径`/proc/<pid>/task/<tid>/children`（包括各线程），并核父PID/startticks前后不变。Popen→身份登记的包装须在异常/信号路径恢复原函数；services原函数返回前的故障仍可能没有完整ProcessInfo，必须如实未确认，不能因此全机扫描或宣称零竞态。

这些是局部实现正确性与后续G2/实际CPU Gate的明确检查项，不改变直接Node方案可实施性，不要求mock变成真实运行授权。

## 边界

本审没有测试、编译、Ray/Torch/NVML/CUDA初始化、网络、SSH、改源码或发布。当前完整backend仍未实现；已审release组件不替代Node启动、父driver死亡恢复、原资源准入、实际采样和36向量生产接线。Space730/main/bundle冻结、本地暂不commit/push。常规路径必须有界清理；supervisor SIGKILL、磁盘/内核/驱动不可恢复故障只按真实未确认故障报告，不伪称释放或续期许可。
