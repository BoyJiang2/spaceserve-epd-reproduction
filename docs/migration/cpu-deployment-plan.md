# qjh003 CPU迁移入场与代码部署

本阶段仅请求CPU部署/目录和资产可迁移性盘点，不批准GPU、正式测量或清理。用户已经授权迁移，最早使用时间是本人CPU票 bk-20261028T0925-0332cf80 的北京时间2026-10-28 21:00；结束次日09:00，最终结束前120秒停止并保全。GPU票不替代CPU票；不开新预约，不更改备注。21点前仅本地准备。

## 本地准备

Space源码G2/G5通过并已push 07358c837c878dccc118283a4bac0cab84f5949e；EPD源码G2/G5通过并已push aae5c8b3f094b80cfc0739f75b0a3150e92e69e0。实际CPU测试仍0，不能继承旧12/87；native36/selected360仍拒绝。本地先核API commit/tree/public，制作完整Git bundle、SHA/bytes及成员清单作为GitHub TLS故障的同版本传输后备，不含模型环境或新成功marker。

## 开窗CPU入场

1. 开窗后重新只读API，保留origin/read_only/observed_ms，确认精确本人CPU票、h20/qjh003、start/end、active，5分钟内实际观察，运行时覆盖当前时间。实际服务器UTC时钟差不可超过2秒。
2. 只读SSH核 hostname=qjh003、UID2147、boot、CPU50 affinity/占用、专属父目录所有权/真实路径、/local空间及两个目标root是否存在。已存在则先读实际原件/PID/ctime，禁止覆盖或重复初始化。只盘点本项目旧根；不触碰同账号其他项目。GPU UUID/NUMA/占用可以在本人GPU窗口只读记录，但不创建CUDA context、不据此批准运行。
3. 在CPU50/nice10下执行一次代码部署，整个单元硬timeout900秒，只有实际本人CPU票还可覆盖900秒＋120秒时才开始。只建两个真实固定项目根 `/local/boyjiang/spaceserve/`、`/local/boyjiang/epd/`，各建 repo/assets/runs/staging/archives；新建根700，祖先不允许软链接/foreign owner。repo由git clone创建，不提前建成非空目录。无删除、rename或sudo。

## Git部署与验收

同一已发布指定commit aae5c8b3f094b80cfc0739f75b0a3150e92e69e0，用两处固定checkout。优先使用已经本地验证SHA的完整Git bundle，复制到Space项目staging后核远端大小/SHA，再clone；bundle传输失败保留partial与日志，不当PASS，不自动重试。也可用GitHub公开origin直接clone同一commit，连接失败同样保留诊断。

checkout采用稀疏检出，仅该项目runtime及根共享配置/必要测试，避免把旧vN/window归档源码放成服务器多个维护入口。Git历史仍完整保留，旧源不丢失。origin设置为公开仓库规范URL，不使用内嵌凭据。

逐步执行git clone --no-checkout（源bundle或公开origin）、sparse-checkout init --cone、sparse-checkout set `<project>/runtime` tests、checkout --detach `<full-commit>`。验证HEAD、tree、tracked/untracked clean及git fsck；对实际检出文件逐一核Git blob SHA和文件bytes/SHA256，并核两项目G2源快照全部对应本地指定commit。G2快照包括README中较早状态措辞，实际审批以审查原文及migration页为准，不追溯改旧SHA。

代码证据写所属staging，保存原路径/目标路径/commit/tree/boot/UID/CPU亲和性/真实起止/命令/逐文件SHA/日志。只在真实校验完成后写CPU_CODE_DEPLOYED（不是CPU套件通过、资产迁移成功或GPU Gate）。传回本地再次SHA并交独立实际部署复核。

## 资产与旧数据

代码验收后，只读核qjh003已有本项目旧根 `/local/boyjiang/spaceserve-epd-qjh003-20261023` 下epd环境、MiniCPM、dataset、IPC编译库的实际位置/SHA/链接/shebang/.pth/RPATH及引用。先形成具体成员表和迁移字节预算，再独立G2；未经具体清单审查不直接cp整个旧根、不继承旧环境PASS。环境不能直接移植则按锁重建，保留旧源。

Space目标尚未发现环境与Qwen7B资产。qjh000源CPU票19点已结束，19–23不远端，不为赶21点越权搬源；本阶段不授权任何qjh000读取/运输。缺失资产须如实记录，后续走有效源CPU窗口或经审查按相同pin重新获取，不能把代码部署称完整迁移。

旧成功/失败数据、claim、四批封存、七ZIP、四Release13资产及qjh000源均不修改。目标资产及原件备份SHA/环境验收完成前不删除旧副本。完成代码迁移后仍需实际新CPU与GPU各Gate，实验矩阵/请求预算不变。

## 成功标准

- 两个稳定项目根内指定commit代码逐文件一致，稀疏检出只有一处维护源码，原始部署证据下载SHA一致。
- 资产已迁移/尚缺/不兼容分别列出；没有实际搬迁/运行的不称完成。
- 不提前入场、不超预约边界、不碰他人、不新预约、不清理旧证据、不调用GPU实验。

本计划本身不是G1/G2原始批准；具体命令和传输清单仍交独立审查后执行。
