# Existing-checkout deployment helper — 独立G2

reviewed_at_utc: 2026-10-29T19:00:42Z
reviewer: /root/gpu2_report_g4

**REQUEST_CHANGES / BLOCKING 2；不授发布/部署或任何GPU/runtime Gate。**

独立重算源码tools/deploy_space_window_20261030.py SHA `534f1c4833eb0072255e676e4b5d6bc4eb311edccfff2e55bcd89bd7d43cd074`、test_deploy_space_window_20261030.py SHA `59f3d1775207fd72e47172f7ceb2833d59ceef566971874434b5f9a28525477f`，与deployment-cpu-tests.json一致。只读核两源码/日志、已审controller/window/launcher及旧materialize guard，未测试、网络、SSH、GPU、凭据读取或改实现，只保存本审查。

## B1 — 默认SIGTERM不能保证Git变更子进程有界收口，也不会执行finally

server_command生成的bootstrap没有安装受控TERM/INT handler。local外层为timeout --foreground --signal=TERM --kill-after=30s 240s。foreground超时向Python命令发送TERM；默认Python处理是终止，不保证执行try/finally写stage/exit.json，也不保证正在subprocess.run中的Git fetch/sparse-checkout/checkout子进程退出。每个Git command内部timeout45秒又大于外层killafter30；父进程先被终止可能留下继续修改checkout的Git。此时UNKNOWN只是诚实的观察标签，不能替代已授权部署单元要求的受控partial收口。

最小修正可用合作式取消：在任何Git创建前安装只记录取消的TERM/INT handler，当前Git操作保持实际有界、返回后立即禁止后续变更，最终真实写exit/partial；外层保留120秒清理而非30，与full360准入一致。若用主动转发/终止，仍须实际Popen/UID/start身份与已审稳定方法，不能进程组/裸PID泛杀。不要求回滚已完成的fetch/checkout，更不能reset clean；部分状态明确保留，禁止自动第二次部署。

新增CPU注入反例应调用生产取消/command逻辑：TERM在当前Git执行时被登记、当前句柄收口、下一条变更未调用、失败终态写出/原件保留。当前3测试只是构造/编译/字符串，不覆盖该信号生命周期，不应声称受控清理已验证。真实Linux信号验证仍需后续实际CPU Gate，mock不得替代。

## B2 — local三端源码/配置核验遗漏实际导入helper与发送配置

main的verified_file循环仅deploy helper、control_space_window、window policy3文件。它还从control_space_temporary_cpu导入并实际使用CHECKOUT/git/verified_file/process_identity，却未核此本地helper等于指定commit和GitHub原字节。cfg从工作区proposed.json直接read_bytes，经wire送server policy.validate，亦没有与指定commit/GitHub原字节比较。policy只核窗口资源子集，不能证明这个cfg全字段确属受审配置；不能以“source_commit字符串相同”替代调用依赖/配置的三端身份。

最小补齐该循环：tools/control_space_temporary_cpu.py与spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json。发送cfg必须来自已验证相同原字节；不要静默丢弃未审字段或按window部分检查重建。已有controller其自身循环已包含这两项，保持同口径即可。无需更改token客户端或把凭据纳入Git。

## 认可的其余范围

- existing clean730基线、明确host/UID/CPU50nice10/boot、04后fresh本人双lane/完整prepare360、严格GPU2 0/apps空、新run不存在和旧Git730的guard_processes复用方向正确。原PAM/SSH严格例外必须实际匹配才通过，不能因为本G2复制历史PASS；原件exceptions记录保留。
- 独立owned stage/open x/bundle<8MiB且SHA/size、fsync/verify/fetch指定commit；不清理旧run/资产、不reset clean、不运行模型。sparse指定space/runtime/tests/tools，checkout后真实HEAD/clean、materialized文件逐Git原字节及SHA/required4路径检查，描述不将未检出的sparse文件当部署文件。
- 分阶段Git调用前再次policy.validate，保守拒绝过期/不足完整预算；即使因此失败也应保留已有partial，不自动改预算或重试。
- 本地FD绑定/实际Windows PID FILETIME/UNKNOWN不杀不重发复用已审方法，credential处理委托已审snapshot；本源码不构建runtime批准marker。观察超时或本地SSH0/非0均不足证明目标repo最终状态，实际部署审计仍须现场readback。
- 实际日志3构造测试PASS，最初embedded null-byte1ERROR与改raw literal资料保留。本审没有重跑；不把它们当Linux/远端部署验证。

B1/B2闭合后需精确G2复审、新候选清单与G5/Git-first，再指定新commit部署。当前不允许据旧2092发布状态直接运行未发布helper，不改旧730封存批次版本。

GATE_RESULT: {"gate":"G2-space-20261030-deployment","decision":"REQUEST_CHANGES","blocking":2,"source_sha256":"534f1c4833eb0072255e676e4b5d6bc4eb311edccfff2e55bcd89bd7d43cd074","test_sha256":"59f3d1775207fd72e47172f7ceb2833d59ceef566971874434b5f9a28525477f","GPU_approved":false,"deployment_approved":false}
