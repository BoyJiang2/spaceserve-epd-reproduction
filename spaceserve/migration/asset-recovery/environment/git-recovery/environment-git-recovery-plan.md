# Git warning引起的环境bootstrap安全恢复

首个bootstrap实际exit1，failure Frozen runtime is dirty。原始log显示Git exit0但stderr包含 /nonexistent/.config/git/ignore Permission denied；command_output合流后触发dirty保护。未复制uv、未创建env、其他四action未运行。只读复核显式core.excludesFile=/dev/null的status为空，两目标不存在，uv venv帮助实际包含必要选项。

仅三行生产修改：status指定空excludesFile；evidence与TMPDIR切换至staging/env-build-git-recovery。旧env-build原件完整保留。新目录必须不存在，不删除失败目录，不吞stderr或忽略退出码。新G2/G5、公开Git-first原字节核验、fresh CPU/API/host准入后，仅一次恢复bootstrap；成功后才依次lock/install/framework/verify各一次。所有240+120秒、API300、CPU50nice10、09点END-120、154exact/hash锁/原2582pins和GPU0边界不变。再次失败停止，禁止自动重试。

本机原4CPU mock复验全PASS，不能代替实际环境创建、安装或CPU/GPU门槛。首失败、诊断、测试原件均留存。
