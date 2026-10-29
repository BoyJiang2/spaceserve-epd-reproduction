# 首次部署写前拒绝与单次恢复准备

第一次真实部署使用已发布3a3源码，因PID3818273 cwd不可读且无法满足旧固定服务例外而exit1，发生在stage/bundle/fetch/checkout之前。随后该PID已消失，不能追认它属于PAM；只读确认新部署目录和新run都不存在，原失败不改写。

第二次独立只读诊断观测到了新的user systemd/(sd-pam)及SSH链。旧PAM例外固定旧PID，不能自动套用。此次窄修正只允许PermissionError分支验证精确UID/boot/父链/startticks/cgroup/cmdline SHA以及已有成功读取证据的user-systemd exe，前后双读稳定才返回服务身份原件。既有cwd扫描、可读project cwd拒绝、SSH例外及其他未知拒绝保留；回调只在调用中显式替换并finally恢复，不写系统服务或旧helper文件。

本目录保存原失败/实际只读诊断、恢复方案与审查以及本地测试。11项新结构/回调fixture和28项既有本地测试通过，不等于真实proc或GPU验证。源码批准与发布批准均不能替代新执行批准；必须新commit/bundle及一次新输出目录，实际fresh票/现场Guard通过才恢复，不使用旧3a审批，也不自动重试。

模型、请求、单GPU2、CPU布局、原54/5400+1080及201分钟入场要求不变。GPU尚未开始，首次失败不是模型实验或性能数据；若无法在原窗口完成全部准入，不缩验证、不拼旧48/54。
