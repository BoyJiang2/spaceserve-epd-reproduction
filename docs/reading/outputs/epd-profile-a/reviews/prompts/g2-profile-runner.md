> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/epd-profile-a/reviews/prompts/g2-profile-runner.md) SHA256 8299e6d6cbae942f48ee7b2abdf54854ade91d77fe5bfe92278cae4197ea8b31。原数字及解释不变。

独立只读G2运行与压测审查，不执行命令、不改文件、不访问GPU/凭据。项目根 D:/Documents/codex/2026-10-23/new-chat-2。
只Read outputs/epd-profile-a/scripts/run_profile_a.sh、benchmark.py、control.py，必要时窄读stop_server.py。最多5次读取，输出限1000中文字。
用户授权qjh003原MiniCPM FP16 TP1 E:P:D1:1:1 vs同机三副本，相同三卡0/1/2，1/C1、4/C8，profiler off/on，20warm+100正式×3=2400正式+160warm。Nsight捕获第三重复index84起末段16新请求；start控制在单请求timer前，但影响该重复总时长，须计入on扰动。stop在全部计时结束后、SQLite export在服务结束后。源码打点另审G2；GPU实际覆盖和正确性/重启另G3，formal须G3_APPROVED。私有新root，旧封包/模型/环境不改。
检查矩阵/请求公平、失败停止、只清理录入的自有服务PID（stop_server校验路径/uid）、监控与Nsight退出/日志保留、重复数据保护。off/on模拟HTTP全320请求(C1/C8)内容和计数相同、仅on在生成304条后start三端点/320条后stop，已CPU测试通过。
给此运行/压测子范围G2结论 APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES；BLOCKING文件行号与理由、建议/疑点。不要扩展审其他阶段。
