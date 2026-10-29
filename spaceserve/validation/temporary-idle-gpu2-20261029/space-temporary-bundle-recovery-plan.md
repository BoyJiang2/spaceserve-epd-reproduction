# 临时GPU2部署：一次Git bundle恢复

实际CPU deploy 9754419已exit1，GitHub HTTPS fetch在60秒超时，migrate.command_output记录向其自有session PID1194829/1194832发TERM；roothelper1194798也须只读重核终态。三原件已从目标读回并逐SHA匹配，原terminal SHA=b4dda733def170f1d7a840e4ee9160648b7f02c5dedaccac96c3972b78097584。实际HEAD仍beadff9c4cc4693cd2ea8675020f757e313659e8且Gitclean、run与candidate均不存在，GPU2 0MiB/0%/compute空。没有CPU suite或GPU启动，原失败不可覆盖，非UNKNOWN重启。

请求仅一次受审CPU recovery，不重试网络：本地/GitHub发布新C1（只维护CPU部署/控制器与tests，Space84源/共享reproduction_paths等GPU代码不变），构建HEAD ^beadff增量Git bundle，经SSH固定owned staging文件conv=excl/oflag=nofollow传输；目标核regular/UID/size<=16MiB/SHA、bundle verify与exactC1 HEAD，再fetch本地bundle/checkout/fsck。其他下载源、环境、模型、SM实现不改。

维护原prepare_space_temporary与controller新增唯一deploy-recovery阶段；只允许已存在的原deploy失败terminal/SHA/log完全匹配、HEAD仍beadff clean、run/candidate仍无、fresh条件scope/boot/UID/CPU50nice10/GPU2空闲、无自有project进程时执行。记录独立deploy-recovery claim/log/terminal，绝不覆盖旧deploy文件，不删除staging来绕guard。prepare只在匹配的C1 recovery成功后接受；若无recovery则原deploy成功路径照旧。controller新phase本地raw目录独立，其API beforeSSH/Git/source/input fileFD/UNKNOWN不杀不重启不弱化；bundle传输用实际受审固定命令/字节pin，非server任意路径或vN工程复制。

配置只把source_commit从975改为已push C1，其他每字段须与原ebe8ae33a2bebd80da88328ef268900c459853bbb913857a311a88059acd1c8f相同（包括run-ID与原13:40:34.579–14:40:34.579/END120），旧配置原文保留。由于尚未创建run，后续首次prepare冻结的源/配置都绑定C1，本地/GitHub/目标同C1；旧失败实际版本仍975。只改CPU恢复工具不改变已审GPU source bytes。整个60分钟窗口不重置/延期，原240+120 CPU单元及完整模型原1800入场不降，超时不够则留断点。

先纯CPU mocks复现guard与不同bundle/旧terminal/重复recovery/新config是否只source变化拒绝；真实失败与postread做独立结果审核、新G1/G2/G5、Git-first/API实际文件前验、fresh idle后才一次transfer/recovery。每单元失败/UNKNOWN即停，不自动切卡/重试。成功才prepare/CPU suite；无GPU运行许可，numeric/model仍依次真实Gates，正式0/54。本轮不问已授权例行许可。
