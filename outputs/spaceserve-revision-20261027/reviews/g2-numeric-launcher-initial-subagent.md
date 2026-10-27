# Launcher窄G2初审

独立/root/profile_instrument_review：REQUEST_CHANGES，BLOCKING1。subprocess.run未处理TERM/INT，SIGINT异常可kill子runner绕过MPS finally；默认TERM可无回执退出。要求Popen受控TERM转发并等待实际退出，真实CPU子finally回归。

主执行者改为Popen与显式signal handler、子PID/ctime核验、TERM+wait，实际Linux INT/TERM两场景子finally/exit23保存通过；未部署被拒launcher。
