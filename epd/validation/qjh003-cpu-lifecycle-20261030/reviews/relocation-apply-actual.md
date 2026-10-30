# EPD CPU 静态重定位 apply：独立实际审计

reviewed_at_utc: 2026-10-29T23:42:23Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0。仅确认本次唯一 apply 的实际静态结果，满足申请独立 verify 执行审查的前置；本审不直接授权 verify，不授 Ray/Torch/dlopen/CUDA IPC/GPU、模型或 runtime-ready。**

## 原件与来源

实际执行目录 `epd-relocation-CPU-20261030-apply/` 的 command/input/input-file/controller/stdout/stderr/exit 与 `epd-relocation-CPU-20261030-apply-capture/raw.tar` 已独立读取。本审未执行项目、测试、网络、SSH、远端或 GPU，仅本地解析原件、Git 对象、ELF 字节及计算 SHA。

原包 1116160 B，SHA256 `81c69520585ab0202015401d9e489ae7645f8f7ad34ca59067624e79f2559fdc`。实际 122 唯一普通 tar 成员：121 个物理 raw 文件与 1 个生成的 capture inventory；不是 122 个远端物理证据。本人逐一核 121 个 raw 与 inventory 的大小、SHA、UID2147，均一致。inventory 是采集者生成索引，不能代替原件；本审直接读取所有原件核验。

实际 input 的 source/config/base64 review 与独立执行 G2 原文及 JSON 绑定；source/config 进一步与本地 Git 对象 `97a33d5287cfdca69956da0fdabe5bc68ea65d46` 中原字节核对相同。source SHA `0e3031089b7e523309b4cc3fcaab2b91f4ba4382963778cf22ea78cba647acec`，config SHA `218bfc2d53f623d98aa64286c1d132c9c74a8f6db0c75aa8e48cfaa9f82f0e70`。实际 SSH argv 内 base64 operator 解码后与获审原文件逐字节相同，SHA `87e0cd40d438d084c5de5fab12d4ab4310cdf375dad7757217213f1a6f7f4d9e`。input 实际54263 B/SHA `76b5855c441cd8560962ac01677ff35425df8126a189d5d2ed45f27a4895dea1` 与真实 FD identity 回执一致。

helper commit97a33与实际服务器 EPD runtime HEAD **a3f03b9dd5956db92add454f9b3afd5663f84609** 分别保留。没有将新 helper 当作已部署完整 runtime。独立 fresh preflight observed_ms1793316742876 确认 boot65f、UID2147、runtime a3f clean、new stage/flat absent、Space model/formal claim false；实际 operator 在写前再次核 host/boot/UID/CPU50/nice10、runtime HEAD/clean 和 Space claim/started 不存在，成功后 stdout 保留双 commit。这里 CPU affinity/nice 的依据是实际执行获审 operator 的强制断言，不是另一次内核采样。

## 实际变更与完整性

61 个配置 startup 文件全部逐字节核验：56 个重写文件均有原始 before 备份，大小/SHA 与原配置 pin 一致。本人独立重建变换：console 仅精确首行解释器前缀替换，activation 仅唯一 old_env 前缀替换；实际结果与重建字节全等，且每项 journal 的 before/after SHA、kind、长度相符。其余5个 unchanged 文件保持配置 SHA 与长度。未把56项 journal 记录本身当成变换成功的充分证据。

3 条 python symlink 的采集 link/resolved/UID 与配置一致：python→/usr/bin/python3，其余两条→python，最终 /usr/bin/python3.10；未运行这些入口或导入环境。

原 nested ELF 359096 B/SHA `12e4145134ba1697bb745fd51c37a8f275293284d6152c17b42513dd6d07ca20` 不变。新增 flat ELF 398920 B/SHA `fdb86ae5a5658d17c98cc8cc17e3b0d911433bf270fb8bcfbb381a99f66a970e` 与 terminal、capture 原字节一致。本人直接解析两份 ELF64 little-endian section/dynamic/string table，实际 NEEDED 有序列表相同，flat RUNPATH 精确为新配置的 torch/lib、nvidia/nccl/lib、nvidia/cuda_runtime/lib 三目录。不是只采信 readelf 文本或 flat 文件名。journal 中四个实际 readelf/patchelf 子命令全部exit0；这些静态 ELF 操作不等于 dlopen 或依赖实际加载成功。

## 票、身份和终态

实际 claim PID261292/start_ticks25200061、boot `65f52a67-afe4-4919-8646-4694255b48ee`、config SHA 与 terminal 一致。claim `reservation_claimed:true` 是本次真实 owned CPU ticket 检查后的记录，已核原件，并非仅配置开关：availability observed_ms1793316845882，claim started_ms1793316848659，差2777 ms；CPU票 `bk-20261029T1809-58743aa0` 本人boyjiang/qjh003/h20/qjh003/04–11字段完全相符且位于实际窗口，terminal结束仍有远超120秒余量。CPU冲突检查与自有项目进程 guard 由实际获审工具写前执行，不能据GPU票或GPU空闲替代CPU权限。

实际 SSH PID5508/FILETIME134377904458903132，有唯一controller记录；argv为 CPU50/nice10、system Python -I -S -B、CUDA_VISIBLE_DEVICES空、foreground TERM120/kill-after30。stderr为空，远端 apply terminal exit0/start1793316848659/finish1793316848748，实际elapsed0.088881405秒；stdout第一行与保存terminal JSON语义全等，末行明确new_GPU_requests0/grants_no_runtime_readiness true。SSH实际exit0/finish1793316848972，不把旧SSH失败或历史封包嫁接本次。

本审没有新的/proc终态采样；成功同步subprocess返回、唯一SSH退出和完整terminal证明该CPU单元返回，但不外推整机无其他进程。此前GPU2 40989MiB/100%为第三方活动背景，不受本静态维护改变，也不是本项目GPU工作。verify前仍需独立fresh票/现场自有进程/原件pin检查；若身份或现状未知须拒绝，不能凭本审跳过。

## 后续边界

本次实际apply静态前置通过，可据此申请**另一次**精确 verify G2；本审不批准执行verify或重跑apply。原stage、before、flat及失败/封存材料必须保持，不覆盖旧nested/旧配置/七ZIP/Release。不得将这份结果写为 Ray 生命周期、IPC/native36、真实模型或公平PD已完成，也不改变Space main24b/既有实验版本。整个总目标仍未完成。

GATE_RESULT: {"gate":"EPD-CPU-relocation-20261030-apply-actual-audit","decision":"APPROVE_WITH_NITS","blocking":0,"passed":true,"static_apply_audited":true,"verify_prerequisite_satisfied":true,"verify_execution_approved":false,"runtime_ready_granted":false,"GPU_approved":false}
