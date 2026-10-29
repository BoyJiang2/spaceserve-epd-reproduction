# 04点部署写前拒绝：窄恢复方案 G1

reviewed_at_utc: 2026-10-29T20:19:34Z

reviewer: 独立 subagent `/root/fallback_g3`

**APPROVE_WITH_NITS / BLOCKING 0。仅批准计划范围内的本地最小实现与适用源码/反例审查准备；不批准重新执行旧命令、服务器手改、部署恢复、CPU phase或GPU。**

计划原件：`outputs/migration-qjh003/space-0400-deploy-recovery-plan.md`，SHA256 `63a20abb0950e91bda184b786d42f230944f850dd487d44f99a66af901343b4d`。

## 实际证据与判断

1. 原 `space-0400-deploy-execution/stderr.log` 清楚记录旧Git730的guard在读取 `/proc/3818273/cwd` 时PermissionError，随后因无法验证自有进程cwd抛ValueError；本地exit.json为1。readback原件记录该PID已不存在、deployment_stage_exists=false、new_run_exists=false。结合已审bootstrap顺序，拒绝在stage/bundle/fetch/checkout之前，不能把这次失败标成成功，也不能直接重复原部署尝试。现存证据不允许鉴定3818273是什么进程或认定失败原因就是PAM。

2. 后续 `space-0400-deploy-first-failure/unknown-cwd-diagnostic.json` 实际记录：
   - child3831927：UID2147、comm `(sd-pam)`、PPID3831926、start_ticks23944191、cmdline SHA `971490059d839d27af3ded30a476216b92689d837b0236a700723fb13640e370`。
   - parent3831926：UID2147、comm systemd、PPID1、start_ticks23944190、exe `/usr/lib/systemd/systemd`、cmdline SHA `8e5650cd3e49f78d40815491e0e012c21acac998215dd4338c62ac0eaed3bec0`。
   - root PID1：UID0、comm systemd、PPID0、start_ticks856、cmdline SHA `6628c1ade33319fc12730a87856ccdb1e4eaed9a0aa2b0bce0535a97a232f272`。
   - child/parent cgroup完整值均为 `0::/user.slice/user-2147.slice/user@2147.service/init.scope`；PID1为 `0::/init.scope`。PAM和PID1的exe原件均为PermissionError，不能虚构已读取它们的可执行路径。

3. 这组候选结构证据足以支持设计一个新窄例外，不能支持按进程名、单UID、任意PermissionError或任意systemd放行。保留boot65f与根PID1/start856静态锚，要求真实父子链、UID、comm、cmdline SHA、精确cgroup、父exe和正数/先后start关系，并对相关身份字段前后双读，是与实际资料相称的最小方案。只比较稳定身份字段，避免把正常变化的CPU计数当作身份改变。

4. 新例外只进入旧guard的cwd PermissionError分支，原项目cwd扫描及原SSH例外保持。可读且位于项目目录的cwd必须先拒绝，不能被PAM候选覆盖。其他未知身份、必要读取失败、父链/exe/hash/cgroup/boot不符、两读变化、PID复用仍拒绝。接受例外应产生完整结构身份记录，不能用一个布尔PASS代替审计证据。

5. 方案不修改系统服务/进程/预约，也不改模型、卡数、SM、请求矩阵、201分钟正式门槛或240+120部署预算。新实现必须属于本地新发布源码，明确记录新例外接线；不能声称旧730 guard原样未变，不能服务器临时猴子补丁后沿用3a3版本身份。用显式回调或可审查的新工具接线即可，不需要引入通用权限豁免框架。

## BLOCKING

无。

## NON-BLOCKING / 实现与后续Gate条件

- 计划“不能接受可执行/读取失败”应按**列出的必需字段**理解并在源码G2中明确：要求parent user systemd的exe成功读取并精确相符；当前诊断未取得child和PID1的exe。若选择将这两者exe也设为必需，则当前材料不够，须fail-closed补证，不能把“PermissionError字符串相同”当作可执行文件身份。无论如何，不能增加一个吞掉任意读取错误的fallback。
- cgroup必须按上述完整值核，至多明确处理文件末尾换行，不能仅做substring、user@服务名或UID匹配。`/proc/PID/stat` 的comm含括号；解析必须正确取PPID/start_ticks，不能靠简单按空格拆整个stat。当前parent/child相差一个tick，不应要求严格更大的额外时间间隔；child>=parent、全身份双读稳定及链关系保留即可。
- diagnostic不是三进程稳定双读的实际成功证明，也没有独立证明该次诊断每项字段与boot原件原子绑定。后续真实Guard必须重新读取并核boot和双读字段，不能复制此JSON成通过marker。原消失PID保持UNKNOWN。
- 所提CPU反例应直接覆盖实际生产验证/接线：正确链、每个必需字段/根锚/父链/UID/exe/cgroup/hash/start不符、读失败与两读变化；cwd可读且在项目内仍拒、非PAM未知PermissionError仍拒、既有SSH规则未被替换。只读mock不能宣称真实POSIX `/proc` 权限/清理已验证。
- 改动后先精确源码G2、有意义本地CPU测试、G5、新commit/远端身份/新bundle，再取得新的具体执行审批，才可单次恢复。旧3a3/04efa审批不能用于新源码。此次批准不是让旧execution输出被复用；新nonce/output/stage恢复策略应在新执行审查中绑定，已有partial必须保留。
- 执行时重新核fresh本人CPU/GPU票、现场boot/UUID/严格idle、clean730、新run及部署stage不存在、完整240+120和原收口规则。任何新失败/partial/UNKNOWN均保留并重新评估，禁止循环重试。不能为了追正式窗口缩减新CPU/numeric/313或formal Gates。
- 原一次性automation是否删除属于主导已报告的应用操作，本审查未调用应用或联网独立复核；不把该报告当作本审查新建任务/重发命令的授权。保持单一主线程恢复、避免重复dispatch。

## QUESTIONS

无阻塞性问题；exe必需字段范围在实现G2中须按上文明确。

本审查只读计划、原stderr/exit/readback/诊断并解析JSON、stat身份与SHA；没有运行测试、网络、SSH、GPU或修改源码，仅新增本报告。原始失败材料不变。

GATE_RESULT: {"gate":"G1-space-0400-deploy-recovery","decision":"APPROVE_WITH_NITS","blocking":0,"plan_sha256":"63a20abb0950e91bda184b786d42f230944f850dd487d44f99a66af901343b4d","scope":"local_narrow_identity_exception_design_only","server_execution_approved":false,"GPU_approved":false,"formal_approved":false,"retry_old_command_approved":false}
