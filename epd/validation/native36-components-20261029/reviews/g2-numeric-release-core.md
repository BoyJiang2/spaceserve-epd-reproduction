# G2 — NumericRelease 核心只读审查

- 审查者：`/root/epd_pd_followup`。
- UTC：2026-10-29T07:18:35Z。
- 结论：**REQUEST_CHANGES / BLOCKING 2**。仅新release组件；未测试、编译、改实现、远端、初始化Ray/NVML或GPU。
- 精确源码：numeric_release.py SHA256 `45df3a170f16eb7e6f61b5804162788db4f252a275da620cddd550dace454ec4`；tests/test_numeric_release_cpu.py SHA256 `b4a28810b63ab655e085d9b4a31c0620aed6296963b58a46ab767434b48fe323`。

## B1 — 裸PID信号在持久化间隙可命中复用PID，且可能越过截止

位置 numeric_release.py:125–133（默认send_signal=os.kill）。live_identity虽在发送前复核，但之后record('signal_intent')执行写入/flush/fsync；再直接os.kill(pid)。原actor可在该期间退出、PID复用，新进程会收到TERM/KILL。已有PID复用测试仅在close之前改变startticks；signal_pid_disappeared测试仅模拟ESRCH，均未覆盖“signal_intent写入期间复用且裸kill成功”。再做一次普通/proc检查只能缩小竞态，不能绑定信号目标。

同一区间还可能因日志持久化或NVML读取耗时越过end；当前发送前不再次检查clock，只在while入口检查。即使原身份未变，也可能在已过deadline时发送新信号。

最小修复方向：使用Linux pidfd或等价可证明稳定的进程对象绑定信号目标，先获得稳定句柄、核对应原UID/startticks/boot/root/RUNID，再向该句柄发送；不支持稳定绑定时failclosed而非回退裸PID。信号intent写入后、实际发送前再次核本次end/claim.deadline；超过则不发。关闭自有fd，仍保持一close内有界TERM→KILL、无transfer重试。实际Linux能力以后由独立CPU Gate验证，本轮只需实现与CPU模拟反例。

需新增确定性测试：在signal_intent持久化钩子内令原actor消失、PID被不同startticks进程复用，新进程绝不收到信号；在该钩子或NVML读取中推进时钟越过end，之后无任何新信号。不能用send_signal(pid)模拟器本身自动核身份而掩盖生产裸PID路径。

## B2 — 任意FileNotFoundError被当作整个/proc PID已消失

位置 numeric_release.py:104–123。live_identity读取/proc status/stat/cwd、environ并二次读取身份，其中任一子项FileNotFoundError都会被close捕获为exists=False。它不证明/proc/<pid>目录不存在。例如进程仍在但cwd链接无法resolve（含zombie或被删cwd）、environ读取失败；若此时NVML已无context，validate_release只相信该exists字段，随后actor_released被记录并允许释放exporter。这违背“原PID实际消失 + CUDA context消失”的合同。

最小修复方向：FileNotFoundError后独立观测准确/proc/<pid>目录是否真实不存在（含boot/clock），仅该目录确实ENOENT才记absent。目录仍在、权限/读取错误、zombie或未知都应unconfirmed，不可写released，也不应越过身份校验发信号。保留原错误与实际/proc观察，不把子文件缺失换成目录缺失。

需新增CPU反例：identity或environment读取抛FileNotFoundError，但实际/proc目录观测仍存在，且NVML processes为空/used=idle；此时绝不将importer加入released，exporter仍被阻断。另覆盖实际PID目录确实消失时可在NVML真实idle后确认。

## 已认可方向与范围

mapping_possible先校验双方已注册身份、record并fsync后才更新依赖，适合由supervisor持有且copy等待该方法成功返回；exporter依赖检查、单次close TERM/KILL升级、NVML容量/进程/idle联合确认、无Ray shutdown和已attempted不重复close的方向合理。journal固定本claim目录、排他初建和owned regular检查具备必要边界。以上认可不抵消两项误杀/误释放阻塞。

父driver死亡恢复尚无完整接线：未来独立supervisor须持有此对象、收到mapping持久化完成后才允许driver提交copy、接管driver异常/TERM/KILL，并处理所有已知actor及daemon；本组件不应被描述为完整native36或重启后journal恢复器。启动部分失败、supervisor自身故障与实际终态保存也仍属backend范围。原numeric_unit未变；不能拿旧组件审查覆盖新接线。

## 已有CPU结果的实际边界

只读主线程原件 `numeric-release-cpu-tests.log`，SHA256 `343411ba586688d04c3d6f2e449a70407eadb4c44a71ee5922d8d7f48a187a82`：9项CPU-MOCK、0.107s、OK。主线程说明该run后仅删除unused import；本审没有重跑，也没有将日志外推为真实/proc、NVML、signal、Ray或Linux行为通过。当前9例不包含B1/B2反例。暂不commit/push，Space730/main/bundle保持。
