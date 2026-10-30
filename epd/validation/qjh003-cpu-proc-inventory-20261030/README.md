# CPU /proc 采集窄修与失败边界

实际运行版本 `9a63ae36d4b555e53bccbdafee0af1b2dea3ab02` 保留了 DeepSeek 的 smoke 入口和 actor handle 修正；本次实际未传 --smoke，CPU50/nice10、无GPU、完整四场景入口。唯一实际运行 exit1，0/4。

父进程在单调时间268562.700345702记录 FileNotFoundError，早于 driver 连接完成268562.822181883、提交268563.193180255、ready268564.205044915。原错误未记录 traceback/filename，不能确认具体哪个 /proc 节点消失。TID退出竞态是待验证假设，不能把本地修正或下次通过当作此前异常已定因。

本地仅处理可独立复现的线程目录退出问题：线程 children 读取 ENOENT 后，两次确认该TID不存在且父PID start不变，记录显式缺失观测（raw=null），不授进程释放或静默成功。TID仍在、父PID复用、TID重现、权限错误继续拒绝；原collector PID/UID/root/RUNID/stable checks未改。另在原失败事件写入完整traceback和filename，防止后续清理错误遮蔽首因。

新增7项必要测试：6项线程目录边界、1项原异常证据保留。旧源码183测试出现3ERROR；修后183 numeric测试通过，加既有4项[policy测试](../qjh003-cpu-collaboration-20261030/policy-tests.log)，共187。本地中间错误日志保留。本页发布前，窄修尚未部署或实际复测。

失败原包246015B，SHA256 `78a7c23bf036b2d1d02eb4e8021edebbf3378a69286da58f2e710122bb5168b8`；清理原包6092B，SHA256 `14a6ca00b76bc3d6e404035e485129d977f1a37d7ef4368ca4fcd044fcce103a`，均本地保存、尚未上传Release。实际清理exit0/1.2080468秒，只清9个登记PID；晚到actor仅对账、不给信号权限，fresh GCS DEAD且原PID absent之后才清head，最终原9PID全absent/scope空。旧失败保持失败，不能称CPU完整验证通过。
