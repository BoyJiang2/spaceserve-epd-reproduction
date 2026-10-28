# qjh003 原始资产复制的 PAM 守卫恢复

代码冻结仍为a3f。首次资产工具实际执行5236782717cfec8c5c7a0f819abc21a7a090b8d4，在写前因同UID进程cwd不可读而exit1，目标数据集/IPC库和asset-data证据目录实际均不存在。环境和模型单元尚未启动。原始错误及检查保留，不把失败称为资产已迁移。

只读核实该进程是固定boot下的用户systemd PAM服务。窄恢复G1/G2只允许两个实际PID、创建tick、UID/PPID、comm、命令行SHA、cgroup和父exe全部匹配且前后复读不变时，豁免该PAM进程不可读cwd。可读项目cwd、其他权限不明进程、任何身份变化仍拒绝；不发送信号或清理系统服务。实际匹配原件及SHA记录进claim/终态。

新生产工具SHA6cc17ff2dc27abdf2b4681c82a8e3655b221000ff3fe20d41edf0df7cca45b35、测试0bf92476339f6087096ba5c44ac2aa15fd967c3a28ce32ba6ef12449e6beea07；依赖9cf不变。一次9项Windows CPU-MOCK全部PASS/0skip，0.103秒（父驱动0.290秒），源码前后不变、temp空；仅Windows fixture不比较ctime，不证明Linux机制或目标suite。

新wrapper与上版唯一差异是工具SHA由b521改6cc，两个模块仍须全部核SHA后才执行。实际恢复须新G5/push/三端字节和fresh准入，data仅一次恢复且目标/evidence仍不存在；env/model尚未运行，之后各以独立fresh票准入。三单位源保护、300秒proof、900/120秒、排他claim、无自动重试、RELOCATION_PENDING限制保持。

[窄恢复G1及前阶段时间更正](g1-pam-raw-recovery.md) · [G2](g2-pam-raw-recovery.md) · [首次真实失败](asset-data-run.stderr.log) · [无写入证据](asset-data-failure-inspection.json) · [父子身份只读原件](asset-pam-parent.json) · [9测试原始结果](asset-tool-tests-pam.json) · [具体wrapper](asset-wrapper-pam.py)

当前尚无远端资产复制成功，不改环境/shebang/RUNPATH，不跑GPU；旧源、原始结果与旧发布不变。
