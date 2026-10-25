> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-native-sm-prompt.md) SHA256 88a646689a32efb43831c41e3f05d8b3871bef791d427c9031276095f5890296。原数字及解释不变。

独立只读审查G2：qjh000原生SM和运行时小探针。先读D:/Documents/codex/AGENTS.md与outputs/qjh000-migration/plan.md。Claude仍明确usage_limit_reached（先前reviews/g2-profile-runner.json等），按3.2.1接替。只读、不改文件、不跑实验、不访问GPU、不读凭据。

用户最新goal已授权qjh000，允许非数据盘有足够空间的专属目录；000为8H20、535.161.08、实际DriverAPI12020、nvcc12.8，目录/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023(700)。迁移G1 APPROVE_WITH_NITS/BLOCKING0。不是沿用005 API13000的SM失败结果。依赖安装进行中，无000 GPU计算启动。

本次只批准CPU编译及GPU0的小运行时/原生SM探针，尚不批准7B模型、服务内stream机制或formal。实际服务内SM仍必需，native通过不等于第三组通过。

文件：outputs/qjh000-migration/scripts/{env.sh,gpu_exclusive.py,mps_control.sh,mps_owner.py,preflight_sm_h20.sh,probe_sm_mask.cu,probe_runtime.py}。
旧005被批准脚本在outputs/spaceserve-h20-7b/scripts可对照。主要变化是000主机/专属根、manageenv、nvcc12.8、去除不再需要的005双项目优先级，让host锁仅串行本项目作业。固定mysmctrl6ff57356968a3f04158b9273aa881ee6bdf04229。native每组无MPS/私有MPS各3重复，记录实际SM IDs、exit及stderr，失败不伪装生效。

检查：锁持有至所有精确root/runID与私有MPS残留退出；仅控制本UID/PID/创建时间/nonce/pipe inode匹配的私有MPS，不碰外来任务；启动前GPU0空闲且无既有MPS；原生二进制实际sm90而非PTX-only，driver/runtime失败保留；探针结果表达无过度推论。runtime FP16 probe只在G2+host锁且UUID固定、GPU0空闲下，有限小矩阵并与CPU参考比较，所有缓存需由调用env.sh导向本root。实际操作前将保留CPU bash-n/compile/lock测试，审查可先查源码，再补读日志。

按结论APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING(file:line+理由)、NON-BLOCKING、QUESTIONS输出；不确定明确说明。
