# CPU 子进程退出竞态修正

本次实际运行版本 a4b2070624b09bbbc3ad3fd3d5fcb451f5e182aa，完整四场景、CPU50/nice10、无GPU。父进程已记录实际 ALIVE/live actor binding，driver在269691.366958607确认parent ACK。随后collector沿旧子PID列表读取已退出actor的 /proc/1181270/status，产生明确ENOENT；详见[原始异常事件](original-exception.json)。四场景仍0/4、exit1，不能将ACK成功等同整体验收。此路径只定位本次异常，旧9a63 FNF具体路径仍未知。

窄修仅覆盖正常退出的采集窗口：已登记父PID在observe/children/stable之间真正消失时沿用原missing观测；子PID在observe/stable之间消失，仅双重确认子PID不存在且父身份稳定才记录显式missing。保留known历史，不注册未观察身份，不授释放/静默成功；live PID字段缺失、PID重现/复用、父不稳定仍拒绝。既有GCS DEAD+原PID不存在、稳定pidfd与最终scope校验不变。

新增8项边界测试，旧源码191测试出现5ERROR；修后191 numeric测试加既有4项policy，共195通过。仅两文件改动，实际复测尚待发布/部署和新审批；不使用smoke、不缩四场景。

旧失败12物理原件包366533B，SHA256 bb51f1585af14d91f9c98c6342ea558c7e9ae649be6fd4ea3737402bc3965844；本地保存尚未上传Release。受控清理actual exit0/1.2489843秒，11原登记PID最终均absent/scope空，原失败不改为通过。
