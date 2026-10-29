# Windows临时CPU单元controller G2

初审：REQUEST_CHANGES；BLOCKING1。reviewed_at：2026-10-29T05:32:08Z。只读源码/已有日志/摘要，不运行测试、API/Git远端/SSH/GPU或凭据读取，不改实现；仅保存本审查原文。不授目标执行或GPU许可。

冻结controller SHA2565d790f88ef8609e3d80dffac383849e18c00b76c540ac8f39a2d2bbeba8bb0a2；test SHA256c3c52dce8a44e7a5d2d6e79b98eec443237dfd7ce9708834e58492e19b87bee6，与controller-result.json两源相同。现有日志3PASS/0skip/0.003s、exit0，仅WindowsCPU mocks，无真API/Git/SSH。它验证错误repo、bytes/blob差异、自身源码差异早拒，不覆盖实际stdin等待/超时生命周期。

## 唯一必须修正

Popen后同步process.stdin.write(wire)/close在wait(timeout=390)之前。如果SSH未消费stdin或发生管道背压，write可能阻塞，390秒观察超时尚未生效，UNKNOWN和finally关闭都到不了。因此不能称这个controller整体观察过程有界。

最小建议：将已按原bytes保存的input.json以rb打开，直接作为Popen(stdin=input_file)，随后wait(timeout390)，finally关闭本地input句柄；不用额外writer线程或通用框架。启动前核该文件与wire原bytes/摘要一致。观察异常/timeout仍只记录UNKNOWN并禁止重启，不kill未知SSH/远端。补一项文件stdin/timeout路径mock，证明没有同步管道write、保存UNKNOWN并关闭本地句柄；不做真实网络或目标操作。

## 其他闭包与边界

CLI只接受deploy/prepare/cpu，Windows非优化模式；固定repo/API path、public repositoryID、origin/main与官方API main核对。自身文件及CPUhelper/两trusted模块均以指定Git HEAD原blob和匿名API base64实际bytes/SHA1blob核，且自身执行文件再次相同；之后才compile该已验CPUhelper的configvalidator。API response在SSH之前写本地证据，未先import未验localhelper。配置/root/run/user原文/固定≤60min仍由已G2validator严格核，fresh只读resource snapshot原字段保留，不造本人票。

inline source带SHA验证、Windowscommand<30000、原CPU50nice10/240+120、真实PID及精确FILETIME、排他phase输出文件夹和stdout/stderr、非零退出均记录；未知状态不杀SSH/不重启。输入wire实际bytes有单独文件，但建议上述B1修正时在command记录payloadSHA并重读核，便于直接关联真实stdin。每phase独立CLI，受审CPUhelper以前驱terminal/logSHA约束次序，外部controller不因收到前一步普通exit0就绕过helper。

该候选仍不等于完整目标许可：最终发布/G5与指定commit及三端源SHA、实际config/window/授权原件、目标hostUIDboot/idle/CPUprofile以及controller实测行为均须另核。CPUhelper/runtime的现有G2只是对应源码结论；不得继承GPU0PASS或把CPU辅助controller作为numeric/model启动器。G1direct条件授权不需重复推导管理员批准，但foreign/unknown必须只停own，formal不在temporary范围。

GATE_RESULT: {"gate":"G2-temporary-idle-Windows-CPU-controller","decision":"REQUEST_CHANGES","blocking":1,"reviewed_at":"2026-10-29T05:32:08Z","target_execution_authorized":false}

## B1关闭与最终controller源码结论

复审reviewed_at：2026-10-29T05:34:17Z。最终G2：APPROVE_WITH_NITS，BLOCKING0，仅本地controller候选源码及已有mock证据。原B1/旧测试结论保留。

launch_cpu已改用已保存input.json的rb文件FD直接作为Popen stdin；启动前拒直接symlink、核regular fstat及输入SHA，保存device/inode/bytes/SHA并seek0。无同步stdin.write或writer线程，wait390从Popen后正常进入；UNKNOWN/error不kill或重启SSH，with退出关闭本地input句柄。command记录实际payloadSHA，正常exit独立落盘。

新测试用131KB原bytes读取实际文件FD，验证原bytes/seek、只一次Popen、wait390、timeout UNKNOWN、本地FD关闭及kill/terminate均未调用；改变payload在Popen前拒绝。现有日志实际5PASS/0skip/0.019s、exit0，仅Windowsmocks，无实际API/Git/SSH调用。当前两源逐SHA匹配controller-fixed-result.json，receipt SHA2569f767db1483b6e9bb079e8b2ca5ab12ca0d4731134b0317db30baa868b53c5f8；最终controller8dc92fd564690537d8243a131181edfaac5b2388809f860c07f18df6aa93bcc9，test46947298c1989a91a82032bef9871b4124c2dcb12bf010549d1879edd16db1dd。审查者未运行这些测试。

这是完整本地CPUcontroller源码G2闭合，非实际目标执行准入。精确G5发布/三端源原bytes、实际config/window/授权原文/当前资源身份及目标idle等最终核验仍未由本报告完成；无GPU许可，也不能用此CPU CLI启动numeric/model/formal。未知SSH状态仍保留并禁止自动重启，后续真实远端terminal另核。原runtime/CPUhelper各自G2的边界及GPU2新actualGates要求保持。

GATE_RESULT: {"gate":"G2-temporary-idle-Windows-CPU-controller-final","decision":"APPROVE_WITH_NITS","blocking":0,"reviewed_at":"2026-10-29T05:34:17Z","local_controller_source_only":true,"target_execution_authorized":false}
