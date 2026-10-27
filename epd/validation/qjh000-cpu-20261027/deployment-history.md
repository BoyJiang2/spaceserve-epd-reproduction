# CPU部署期间的实际失败与恢复

这些是部署/传输记录，发生在测试前；不代表模型请求失败，也不计入76项测试失败率。

1. 首次SSH部署session36531返回exit1：`client_loop: send disconnect: Connection reset`。随后实际只读观察新root及`.git`存在，Git HEAD退出128、相关自有Git进程为空。未按观察超时重复启动CPU测试，没有删除目录。
2. 一次经stdin传递的bash只读诊断返回`syntax error: unexpected end of file`，没有修改源代码或运行测试。后改用明确编码的Python只读探针，取得上述实际目录/HEAD/进程证据。
3. 从同一初始化目录恢复缺失的fetch/checkout，session47607实际exit0，固定commit6ca496bb，51文件SHA全部匹配、CPU50/nice10、tracked clean，见原部署回执。
4. 实际fresh预约及host probe、permit原件全部传输成功后，唯一CPU命令才启动；SSH与runner均exit0。claim永久保留，没有重跑或重置测试预算。

所有恢复均只处理本项目新的CPU目录，不修改旧Space/EPD封存、GPU进程、驱动、预约或他人任务。
