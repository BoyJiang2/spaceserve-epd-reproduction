# 单phase server launcher — 独立G2

reviewed_at_utc: 2026-10-29T18:31:19Z
reviewer: /root/gpu2_report_g4

**REQUEST_CHANGES / BLOCKING 1。未授部署/执行/GPU/formal许可。**

实际SHA重算：tools/run_space_window_20261030.py `5efdaa7422574c3f2ca434d301405fcf4879398f2dcf91bf97e2fdfbf5b0366d`；test_run_space_window_20261030.py `fd821baa194c09a5fc497e38efd0281150cae4a2f50c069eab971d36449df8cf`。只读核两源码、window policy、已审proposed/plan、既有监督器逻辑、launcher CPU日志/JSON；没有执行项目或测试、网络、SSH、GPU或改实现，仅保存本审查。

## B1 — 完整预算准入发生在准备/refresh之前，实际spawn前未重验

run_space_window_20261030.py:53–54在本地加载新snapshot时固定now并调用policy.validate；其后仍有helper Git对象加载、SITE与asset清单SHA、目录与claim落盘以及GPUphase独立refresh（101–102，timeout20秒）。103–104直接把原limits.work_seconds交给supervise，后者从实际Popen阶段重新开始完整工作预算。此时没有用当前clock再次确认完整work+120以及snapshot仍fresh。check:92只核boot/END120，不能证明还剩完整phase预算，也不检查freshness。

具体边界：在policy允许的最后1毫秒进入numeric（END-1020000）后，任何合法加载/refresh耗时都会使真正启动时不足900+120秒；它仍可能开始新numeric工作，最后被END120收口，违反G1每阶段启动前必须有完整预算的条件。formal底层自身还会再次核201分钟，未发现本缺口可越过formal201或授权他人资源；但这不能代替本launcher对所有phase的统一完整准入要求。新单元应在实际spawn前拒绝，而非在不足预算时启动后依赖中途截止产生partial。

最小修正：在refresh之后、supervise之前，以实际当前clock对相同原始snapshot与exact配置再次policy.validate，确认work+120/fresh/双lane等仍满足，再启动；失败写真实phase.exit，不重试或伪造新observed_ms。应保留初始验证以避免未经准入先做写入。若改为将全部预启动开销算入同一phase预算，也须从第一clock连续扣账并在spawn前要求子阶段真正最低预算，不单纯缩短模型/正式验证。

补一个有意义CPU回归：用可控clock/注入delay模拟首次准入通过、refresh后越过phase最晚点（以及snapshot跨300秒）时，断言实际supervise/Popen未调用而保留失败终态。现有3项仅command argv（prepare绑定commit、其他phase不重prepare、phase/ref拒绝），完全没有main生命周期/时间消耗覆盖，因此不能覆盖该缺口。不要为补测实际运行远端或GPU。

## 认可的其余边界与非阻塞提醒

- 单次明确phase，指定commit40hex、checkout clean、hostUIDboot/CPU50nice10、GPU2严格0/apps空、独立phase execution approval，canonical migrate→validate→supervise对象加载与新RUN/nonce，方向正确。execution approval不写runtime G2/G3，底层entry仍有真实phase Gates，不能称本launcher替代它们。
- proposed字节直接Git比对；frozen配置去掉3个阶段生成源字段后逐字段等于proposed并且source_commit相同。prepare拒已有RUN，stage phase.claim/open x排他，不自动重试/串phase。原idempotence失败留partial而不恢复，符合策略。
- GPUphase refresh委托指定commit对应已发布工具并限制CUDA_VISIBLE_DEVICES空；阶段环境、mask56、CPUprofile与原scope一致。监督器复用既有有界pidfd身份清理，不全组杀、不全局MPS quit。
- claims和phase退出本身没有完整外层监督器PID/start/nonce原件；supervise日志拥有后代身份。具体本地SSH controller/argv审批及外层超时必须另审并记录真实身份，不能据此G2补造实际receipt。
- 当前3项argv测试实PASS与首个Windows路径fixture1FAIL均有原件，最终两sourceSHA与JSON一致。本审未重跑；不评价为Linux/POSIX/信号/cleanup已验证。
- 新helper/配置仍未发布/部署，须精确G5/Git-first和实际新CPU/numeric/model/formal Gates；04前不能远端执行本phase。本审未发现自动延期、复制旧marker或放宽原请求预算，但B1闭合前不批准实际launcher。

GATE_RESULT: {"gate":"G2-space-20261030-launcher","decision":"REQUEST_CHANGES","blocking":1,"source_sha256":"5efdaa7422574c3f2ca434d301405fcf4879398f2dcf91bf97e2fdfbf5b0366d","test_sha256":"fd821baa194c09a5fc497e38efd0281150cae4a2f50c069eab971d36449df8cf","GPU_approved":false,"formal_approved":false}
