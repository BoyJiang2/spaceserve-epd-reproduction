# CPU放置候选实现G1

结论：APPROVE_WITH_CONDITIONS；本地候选实现BLOCKING0。reviewed_at：2026-10-29T03:22:14Z。计划SHA256：35a7519f1fefd956bb6bb4ffc720092922a21023e23751ce4309fbbfd686a75c。

只读审核formal-cpu-placement-plan.md及AGENTS适用条款，未实现、未测试、未访问远端/网络/GPU。仅保存本审查文件。

批准范围仅为本地小型stdlib cpu_placement.py及纯CPU-mock测试、entry明确配置接线、record_device/capture_runtime的低频实际放置字段，以及run_models/run_formal共用的小校验和source-files成员更新。监督器和CPU/prepare保持CPU50/nice10；历史缺失配置不得隐式扩核。GPU工作负载的候选0–89是一个共同总集合，三组一致，不能给每个worker另加一份集合。OMP4、GPU/模型/精度/请求/缓存、54/5400/1080与201分钟均不因本审查改变。无需框架或模型内部重构。

候选测试成功标准合理：拒bool/重复/负CPU/错误NUMA/跨node，CPU动作不set，GPU明确配置的set/readback精确一致；实际main mask须匹配统一集合，线程仅允许该集合内subset，任何线程越界失败。还须覆盖非法配置在OS变更前被拒，旧配置/候选配置保持failclosed。测试仅mock OS/record fixtures，不调用真实sched_setaffinity，不导Torch/Ray、不SSH/GPU。具体源码及测试后续交G2；通过模拟测试不等于已知真实worker/TID放置。

实际采用是否需要用户确认：**需要对这个新正式资源profile取得明确用户确认。** [D:/Documents/codex/AGENTS.md:85](D:/Documents/codex/AGENTS.md:85)原文：“③ 实验设置（不得私自改动，需改须先经独立审查并由用户确认；审查者按第3节选择）”。从单logicalCPU50扩为logical0–89会改变工作负载CPU可用资源及性能条件，即使三组共享同一总预算、GPU数量不变，也属于新的实验资源设置。本审查是独立设计审查，不能代替该用户确认。泛化的CPU可用授权、GPU预约、优先跑正式或允许本地候选实现，不能自行解释为已确认这个90-logicalCPU profile。若后续有明确覆盖该具体profile的可信用户授权，可直接引用，不重复索要确认。

该确认不阻止当前已授权的本地候选实现/测试准备。实际远端采用还须：有效CPU/GPU新窗及资源权限、fresh boot/UUID/PCI-NUMA、sysfs node0 cpulist/online和可设CPU范围一致、set后实际读取回验；不能把旧nvidia-smi拓扑的0–89当当前授权或OS实时可用证据，也不得占用当前他人CPU/GPU预约。

实际资源profile经用户确认并通过源码G2后，须新指定commit/config/cohort、Git-first、真实CPU/numeric/完整313与独立G3，再按真实足够长窗口做formal。旧CPU50预检G3只证明其原配置的机制，不直接转授新profile。0–89可能包含SMT线程；fresh拓扑应明确logical/physical口径，不称90物理核或保证无CPU瓶颈。

旧raw缺少实际worker affinity/CPU利用率，仍不能断言已实测CPU瓶颈、预测加速幅度或回写旧结果。仅启动/测量边界记录实际PID/start/UID、main/threadaffinity、nice、OMP/BLAS环境及线程数，避免高频新测量干扰。CPU50控制器和GPU工作负载分离时，PID/nonce/root/runid归属及原finally/截止收口不能减弱。

GATE_RESULT: {"gate":"G1-local-CPU-placement-candidate","decision":"APPROVE_WITH_CONDITIONS","blocking":0,"reviewed_at":"2026-10-29T03:22:14Z","local_candidate_implementation_allowed":true,"actual_profile_requires_explicit_user_confirmation":true,"remote_or_GPU_execution_authorized":false}
