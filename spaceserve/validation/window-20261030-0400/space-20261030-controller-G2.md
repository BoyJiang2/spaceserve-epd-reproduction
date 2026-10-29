# Local controller/server bootstrap — 独立G2

reviewed_at_utc: 2026-10-29T18:39:09Z
reviewer: /root/gpu2_report_g4

**REQUEST_CHANGES / BLOCKING 1；尚未批准发布、部署、phase执行或GPU/formal。**

独立实际SHA重算：tools/control_space_window_20261030.py `85db771b0adaf5652cbc16dc77bf306fc7f55863a7109803d328d8072b8743c0`；test_control_space_window_20261030.py `156b3702df656d83a7105726f560eb5bc3bbb4be4d8a5201ac2a3490481e25fe`。只读核源码/测试、既有control_space_temporary_cpu的verified_file/process_identity/launch_cpu、已审policy和launcher修正、controller-cpu-tests.log/json；没有测试/项目运行、网络、SSH、GPU、凭据读取或改实现，仅保存本审查。

## B1 — 记录预期payload SHA，却未验证SSH实际打开的stdin文件

control_space_window_20261030.main在写入input.json后，将预期wire SHA保存在command.json；随后重新open input.json并直接传入Popen。未核实际打开FD仍是该regular-file、当前字节SHA等于预期wire，也未保存fstat身份。若在写入和实际打开/发送之间发生文件替换或内容变化，command.payload_sha256只证明意图，无法证明SSH实际收到的snapshot/approval/review正是这组wire。bootstrap会把收到的p原样登记，但没有一个由当前controller绑定的实际FD/payload核验链，不能将本地预期SHA当已完成传输证据。

这不是要求防御能任意改写同UID一切代码的完整敌手，而是保留现有已审transport已具备的具体来源绑定。对照control_space_temporary_cpu.launch_cpu已经对实际FD做is_symlink、fstat regular-file、实际SHA比较、seek(0)，保存input-file.json后才Popen；新controller因需要可变phase等待时限未复用该方法，遗漏了这些校验。

最小修正：保留当前单phase可变timeout，但在真实Popen前对实际打开stdin FD核regular-file/fstat与实际SHA=预期wire，seek(0)，保存device/inode/bytes/SHA；不匹配写前拒绝dispatch、保留原件，不重写payload或盲重试。无需新通用框架。添加CPU回归直接调用生产FD核/transport窄函数：正常文件得到绑定；内容变更/非regular或链接被拒且Popen spy未调用。当前3构造/字符串测试不能覆盖此缺口。

## 其余认可与执行边界

- 本地指定40hex commit/HEAD、逐GitHub API原字节及blob对比含controller自身和policy/helpers/entry/config，正确；远端clean指定Git、hostUID/CPU50nice10及policy后才创建独立owned stage/phase-inputs，排他目录与文件不会覆盖旧cohort。
- review原文base64经SHA绑定approval；server实际launcher随后核完整expected execution approval。它不是runtime G2/G3 marker生成器，真实entry/阶段Gate仍必需。bootstrap仅canonical指定Git launcher，无phase自动串接/retry。
- 原始snapshot来源是实际只读HTTPS API，token只内存加载并经curl stdin配置，不写入input/command输出；失败用通用错误而不回显敏感response。输出snapshot限resource/booking所需字段，无凭据。未读取token验证本次运行，因为本审禁止凭据和网络。
- 已审launcher末次spawn前policy复核覆盖bootstrap/源核/refresh耗时；阶段独立完整budget+120、END120与真实runtime Gates保持。SSHtimeout从remote bootstrap开始计work+120、后kill-after120是外层受控上限，不能据此许诺晚于预约的工作/清理；实际末次准入及绝对END约束仍必须生效。
- Windows process_identity记录真实SSH PID/FILETIME、异常/观察超时进入UNKNOWN、不杀不重发，方向正确。外层timeout或Connection reset不是远端已终态证明，后续必须跟真实PID/start或phase终态；不因观察到期重启。
- 三项实际Windows CPU测试日志/JSON的hash相符，覆盖bootstrap各phase编译、恶意ref/phase拒绝、单phase与排他字符串。没有执行实际bootstrap；不能声称main、文件IO、信号/POSIX清理、真实Git/API/SSH已经过验证。B1补测应覆盖生产路径而非再加字符串断言。

B1闭合前此精确controller不批准实际使用。后续仍需G5/Git-first、指定commit部署与全SHA、04后fresh实票和每phase execution review/真实CPU/numeric/model/formal Gate；本审不授GPU。

GATE_RESULT: {"gate":"G2-space-20261030-controller","decision":"REQUEST_CHANGES","blocking":1,"source_sha256":"85db771b0adaf5652cbc16dc77bf306fc7f55863a7109803d328d8072b8743c0","test_sha256":"156b3702df656d83a7105726f560eb5bc3bbb4be4d8a5201ac2a3490481e25fe","GPU_approved":false,"formal_approved":false,"deployed":false}
