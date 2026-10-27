# qjh000 本次 CPU 验证：新用户授权与独立CPU lane

用户最新明确“我预约了000，你在000跑吧”，接续CPU单核测试说明；fresh19:31 API确认本人boyjiang/h20/qjh000 CPU bk-20261027T1130-99a32163，2026-10-27 19:00→28日08:00（start1793098800000/end1793145600000）。同host GPU19→次日04为他人，不授权本项目GPU，也不因CPU票启模型。

19:33只读SSH：UID2147、boot c57aee5b-05dd-4c39-81fc-4c76b492d3d6、180CPU、CPU50在affinity内、Python3.10.12、/var/tmp可用约917GB，新专属root /var/tmp/boyjiang-epd-cpu-qjh000-20261027 不存在。主机已重启，旧Space boot与任何历史CPU PASS不继承。qjh001原19点前单元已关闭，没有执行也没有获得其handoff。

一次有限任务：EPD/PD候选的全部标准库CPU单元与真实POSIX/asyncio回归，含9身份测试。单CPU50、nice10、每进程1GiB RLIMIT_AS、主任务300秒+最多30秒受控清理、一次无自动重试。仅CPU；禁torch/ray/vllm/pynvml/CUDA导入、模型、NVML采集、包安装、TCP/UDP服务和外发请求。允许已审git本地只读及自有Python POSIX helper与AF_UNIX selfpipe。不能声称cgroup整个进程树RSS≤1GiB，实际限每进程虚拟地址。

本机CPU/GPU预约lane独立；用户本次指令明确将这段CPU验证放qjh000，不要求qjh001旧四domain释放凭据，也不伪造不存在的旧release。新root/新boot/这次用户CPU授权/freshCPU票绑定，无同root活动单元/拒覆原件和唯一intent约束。不重启、驱动修改、root权限或第三方信号。仅识别UID/root/RUNID/PID/startticks/cwd的自有子进程/helper可受控清理，身份不明拒杀并报告未确认。

Git-first：从v10新建v11，仅CPU准入host/时段/fixture调整及该9测试suite接线；先独立G1/G2/代码发布G5→commit/push→server新独立sparse checkout指定commit→51项逐SHA/clean→fresh5分钟内CPU预约与实际host/boot/affinity/无同root任务→taskset -c50下唯一CPU runner。source位于root/epd/code/fair-pd-candidate-20261027-v11；runtime与tmp在其下，源码前后SHA/Gitclean，bytecode关闭。许可与日志记录精确commit/argv/Python/环境关键限制/hostUIDboot/CPU50/主子PIDctime/真实退出/全test IDs与skip/清理状态。结果下载回本地后SHA验证。SSH0不代替testsPASS；任何失败完整保留，无盲重试、零skip不伪造。

实际任务必须在08:00前完整覆盖300+30秒与准备余量，CPU票过期/归属或boot变更/CPU50不可用/同root有live任务则拒绝。新工作不改旧Space/EPD runtime或封包。Space预检大包发布可同时做本地网络I/O，但不在CPU测试时进行本项目远端重型编译或数据分析。

CPU成功仅证明该受限目标Python下适用CPU逻辑，不能替代真实Ray/vLLM/Torch UUID/跨卡传输/模型G3。controller与全量1440/340候选预算仍有后续准备门槛，本次不授GPU/预约新增/模型请求/正式性能。完整Space54与EPD公平PD目标仍未完成。
