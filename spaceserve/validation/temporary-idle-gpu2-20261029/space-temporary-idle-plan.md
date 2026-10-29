# SpaceServe GPU2临时空闲使用：预检准入计划

直接用户授权：“如果gpu暂时没人用 你可以先暂时用一下”；同时已明确确认监督器CPU50、三组共享NUMA0 logical0–89/OMP4新profile。2026-10-29 04:51:24Z实际qjh003 boot65f：GPU0/1分别88633/87195MiB、100%，GPU2–7为0MiB/0%；不碰GPU0/1。拟选同NUMA0物理GPU2，UUID GPU-c005197e-747d-2dc8-b77b-b123b41efd75，须实际重新核全部拓扑/占用/主机身份，不把当前快照当执行时许可。

当前bookings CPU10–16 yxt、GPU11–17 caicaiis，本人17–20；**本计划不把他人预约、未来票或本地锁写成本人当前票**。用户最新条件授权覆盖此前“必须本人GPU票才可短时预检”的本地限制，但仅当前空闲单卡temporary模式，不改变正式性能要求，不拿其他活跃GPU背景下预检做吞吐结论。正式仍需足够真实有效窗口和冻结范围；临时模式不得运行formal。

本阶段目标是在真实GPU2临时空闲时完成新CPUprofile下的CPU suite、native/MPS numeric、完整313 cold/restart模型机制预检；不缩验证、不重跑旧cohort或混旧48/54。模型/精度/请求/缓存、MASK_OFF56候选和54正式预算不变，旧GPU0实际SM证据只作候选背景，GPU2必须重新实际测mask78→54及并发等，不能继承PASS。实际CPU90共享profile已用户确认，不再问一次。

## 最小接线与成功标准

1. 保留真实booking路径；新增独立temporary_gpu_use.py与CPU-mock tests。config加独立temporary_gpu_use结构和绑定的原始用户授权SHA/独立G1/G2、GPU2/UUID/boot/CPUprofile、开始/终止时间及动作numeric/model；不造BOOKING_VERIFIED。真正使用窗口自限一个不超过60分钟batch，END-120受控收口，开始前实际确认全单元能在window内完成（model仍需原1800余量），授权文件/证据单独命名TEMPORARY_GPU_USE，不把临时许可签成预约。
2. ProjectLayout.require_scope仅Space numeric/model可接受这个明确条件scope；formal拒临时路径。booking_window.require在明确numeric/model临时分支调用该小helper；没有该config保持原ticket精确验证。真实ticket与临时条件字段不能混用成owner PASS。共同GPU锁/源码与G2/实际G3、owner身份/finally、CPUprofileset/readback与raw证据不弱化。原已运行cohort/封包不改。
3. fresh phase开始前真实nvidia-smi选定UUID/0compute/<=100MiB，记录原始行；临时运行每0.5–1秒只监测选卡，若出现非本run可证明UID/root/RUNID/PID-start/私有MPS归属的GPU PID、身份/采集失败或用户撤回/截止，停止本项目提交并通过当前自己的监督器受控TERM→原finally cleanup。绝不signal外国PID、改别人MPS或清理别人的任务。raw触发样本保存，未确认释放按真实失败收口，不签下一Gate。只监测选卡，不因GPU0/1已活跃而终止mechanism预检；它们的背景明确在报告说明。
4. 临时单元仍由指定已push commit部署、逐文件SHA、新frozen config/cohort，实际CPU suite及fresh G2后才numeric；实际numeric独立G3后完整313；实际313独立G3前不称机制已过。当前无目标任务，不重复已有run。外部launcher现有真实预约限制不能仅删断言，必须同样改为明确的用户temporary CPU/GPU辅助作用域，保持CPU50nice10/原生prepare身份与boundedaction，各CPU动作都不碰GPU。new helper/test/source-files成员闭包全审。

验证：纯CPU fixtures覆盖伪/缺原文授权SHA、错误host/boot/UUID/非NUMA0、时间倒置/超过60min/开始前/END120、formal/EPD临时scope拒绝、GPU忙/外来PID/身份变化/采集失败导致own supervisor STOP而从不signal外来PID、记录原始触发、清理gate不伪PASS；缺临时字段时原booking测试继续通过。mock不能证明真实MPS归属/线程监督可靠，必须真实numeric验证，任何阻碍保留失败不绕过。用户只授权暂用空闲，不授扩卡、驱动/SM库修改或同机并行正式测量。

本次G1请求本地接线/CPU mocks及该明确单GPU临时预检范围审查；实际启动仍待G2/G5/Git/API/目标部署/CPU suite和fresh idle，没有现在执行许可。若G1认定临时使用预约中的闲卡仍需资源管理员额外授权，请精确指出适用规则出处，不把旧已被直接用户条件授权覆盖的本地限制当不可覆盖系统政策；有真实外部规则才请求必要补充。
