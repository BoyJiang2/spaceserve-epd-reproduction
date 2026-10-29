# 04点部署第一次写前拒绝：最小恢复计划

原session35549/SSH10768实际exit1，在旧guard_processes读取PID3818273 cwd时PermissionError；该PID随后已absent，不能追认其为PAM。实际只读确认deployment stage/newrun都不存在，首次无bundle/fetch/checkout。原stdout/stderr/exit和readback永久保留，不重标首次成功、不直接重试。

第二独立只读观察发现当前UID2147的user systemd3831926与子(sd-pam)3831927，parent为root PID1；boot65f保持，cmdline SHA/exe/cgroup已采原件。旧730 PAM例外钉死2565253/4，不能套用新PID，更不能只按进程名放宽。计划仅修改本地部署工具，增加单一窄的新user-service结构验证供cwd PermissionError分支使用；原ssh例外和其他未知拒绝保持。

新PAM例外要求真实PID UID2147、comm=(sd-pam)、cmdlineSHA971490059d839d27af3ded30a476216b92689d837b0236a700723fb13640e370、cgroup精确user-2147.slice/user@2147.service/init.scope；直接父UID2147/comm=systemd/PPID1/exe=/usr/lib/systemd/systemd、cmdlineSHA8e5650cd3e49f78d40815491e0e012c21acac998215dd4338c62ac0eaed3bec0、相同cgroup。根PID1须UID0/comm=systemd/PPID0/startticks856/cgroup0::/init.scope与cmdlineSHA6628c1ade33319fc12730a87856ccdb1e4eaed9a0aa2b0bce0535a97a232f272。全部在boot65f，父子startticks正整数/child>=parent；三进程相关identity字段前后两读完全一致，不比较会自然变化的CPU计数。不能接受PID复用、父链/可执行/哈希/cgroup不符或读取失败；只有cwd确实PermissionError时可用，cwd可读且在项目内仍拒绝。

此结构分支是可审查的新本地源码，不修改系统服务/PID/预约/旧封存；需要源G2/有意义CPU反例/G5、新commit与新bundle，再实际执行审批，不在服务器手改或猴子补丁未记录版本。实现可在新部署工具中声明显式例外回调，继续用旧guard的项目cwd扫描和原SSH校验；任何替换必须属于新发布工具原字节，不能宣称旧730例外未变。

范围保持单次CPU部署与04–10/240+120，新nonce/output恢复目录，目标checkout仍必须clean730、新run和stage均不存在。独立审查明确恢复后仅一次；如又partial/UNKNOWN保存并重新审，不建无限重试。新source发布后旧3a3/04efa审批失效于新版本，不能复制旧通过JSON。04任务已实际delete，本线程执行，避免重复dispatch。

CPU测试覆盖真实观察字段前后稳定和每个关键字段/父链/UID/boot/exe/cgroup/hash/start复用拒绝、可读project cwd不豁免、PAM失败后其他未知仍拒绝；日志不写敏感cmdline原文，仅SHA。此次不改变模型/请求/卡数/SM或正式预算，不GPU，后续新CPU/numeric/313/formal Gate全部保留，不能为修复而缩减正式。
