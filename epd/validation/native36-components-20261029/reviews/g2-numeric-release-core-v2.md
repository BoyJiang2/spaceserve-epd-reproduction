# G2 复审 — NumericRelease 核心

- 审查者：`/root/epd_pd_followup`；UTC 2026-10-29T07:23:40Z。
- 结论：**APPROVE / BLOCKING 0；初审 B1、B2 关闭。** 仅当前release核心，不代表完整backend、实际Linux/Ray/CUDA/NVML通过或任何执行授权。
- 初审 `g2-numeric-release-core.md` 保留不改。

## 本轮精确对象

| 文件（checkout/epd/runtime下） | 实际SHA256 |
|---|---|
| numeric_release.py | a1eb5167daedfbfa4c5e66dab5f804efc05fa504e94f6b06943cc5b7cb67e2b9 |
| tests/test_numeric_release_cpu.py | 54d0e06fded90abc985707461c9d665a3b008100419944dbd218b8805ced92db |

## B1 关闭

NumericProc.open_pidfd/signal_pidfd显式使用os.pidfd_open与signal.pidfd_send_signal，不可用时拒绝，无裸os.kill回退。close取得稳定句柄后再次核live_identity；signal_intent写入/fsync后再次比较end；只向该句柄发信号，fd在finally关闭。PID消失的ESRCH只留下观察并进入下轮，不直接声称released。信号之后的身份改变导致拒绝而非转向新PID。

新增源码反例在signal_intent持久化钩子内模拟PID复用，stable handle仍绑定旧进程，新PID未收到信号、fd关闭；另将时钟在持久化期间推进超过end，之后无新信号。pidfd不可用与open前进程退出分别拒绝/重新观测。它们覆盖初审竞态与截止问题；模拟稳定句柄没有替代生产裸PID路径，因为生产路径已改用pidfd。

## B2 关闭

close遇live_identity任意FileNotFoundError后另调用NumericProc.exists，对准确/proc/<pid>目录stat；仅目录FileNotFound返回False，目录仍在则明确RuntimeError。权限等其它异常不被转换为退出。exists=False后仍需validate_release核boot/原NVML容量、idle及processes空才加入released。因此cwd/environ缺失不再足以触发exporter依赖解除。

新增反例模拟identity/environment子文件缺失但目录仍在，未释放且无信号；实际目录缺失+NVML空的成功与open前退出路径保留。生产真实/proc/zombie、权限及NVML延迟行为依旧需后续合法Linux Gate。

## CPU原件边界

本审只读原始日志，不重跑测试。`numeric-release-cpu-tests-v3.log`实际14项、0.187s、OK；SHA256 `ee7b2e14fd34872ea5b10b497500cd418ba380c8521758dcbd2da52b90e331be`。v2日志SHA256 `477a0ccb5871ad9bfe7f2ad012a42b4c6f663f0b985c736c0b7f0ff5b60b96ef`；旧9项原件仍保留。14项是CPU-MOCK，不证明目标Linux内核pidfd或真实信号/NVML可用。

## 仍待完整接线

NumericRelease由未来独立supervisor持有；driver死亡接管、mapping持久化完成后才准copy、Node/daemon部分启动与身份闭包、全部actor兄弟和daemon清理、失败最终回执及真实生命周期Gate均未由本组件完成。调用方须保留异常/未知身份为未确认并阻断下组，不能在本组件抛异常后泛杀head/source。原numeric_unit未修改，本次不把单组件认可外推为native36已完成。

未运行测试/编译、未修改实现、未网络/SSH/GPU/真实Ray或发布。暂不commit/push，Space730/main/bundle冻结不变。
