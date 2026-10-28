# 系统会话守卫的完整恢复（2026-10-28 22:40）

第二次data恢复仍因另一不可读cwd在写前exit1，三个目标及evidence仍不存在；环境/模型未启动。已完整盘点所有同UID不可读cwd，只有固定PAM及两个sshd会话。源保护，未终止系统或他人进程。

[追加G1](g1-ssh-raw-recovery.md)允许以固定boot下root-owned sshd daemon7347/start19660/PPID1/ssh.service为锚点，要求UID2147子进程comm/固定命令SHA/整串session数字cgroup及直属root父链匹配；全部身份前后两读不变，实际快照及SHA入claim。其他未知仍拒绝；不能据此宣称没有任何源引用，清理前仍须完整引用审计。[G2](g2-ssh-raw-recovery.md)通过后，一次10项CPU-MOCK全部PASS/0skip，0.113秒，父驱动0.305秒；源码前后相同、temp空。Windows限制保持，未称目标suite或GPU通过。

最新工具SHA8ffccf7061b2ebc8ac90543d0d60c79efaf7ff87552cef8fcf1bd6555dbd0c0c、测试4cc8128531a7f39b5ac7f75b5f89f47b60ff717834f9139f61b1b81838418af4、依赖9cf不变。新wrapper仅替换精确工具SHA，其他范围不变；第三次data有条件恢复须G5/push/三端核及fresh现场，原两次失败都保留。成功仍仅RELOCATION_PENDING，不改shebang/RUNPATH，不删除旧源，不运行GPU。

[第二次原始失败](asset-data-recovery-run.stderr.log) · [所有不可读cwd盘点及目标不存在](asset-all-opaque-processes.json) · [root daemon实测锚点](asset-sshd-anchor.json) · [10测试原始结果](asset-tool-tests-ssh.json) · [实际新wrapper](asset-wrapper-ssh.py)

下文保留第一次PAM恢复的阶段记录。

---

# qjh003 原始资产复制的 PAM 守卫恢复

代码冻结仍为a3f。首次资产工具实际执行5236782717cfec8c5c7a0f819abc21a7a090b8d4，在写前因同UID进程cwd不可读而exit1，目标数据集/IPC库和asset-data证据目录实际均不存在。环境和模型单元尚未启动。原始错误及检查保留，不把失败称为资产已迁移。

只读核实该进程是固定boot下的用户systemd PAM服务。窄恢复G1/G2只允许两个实际PID、创建tick、UID/PPID、comm、命令行SHA、cgroup和父exe全部匹配且前后复读不变时，豁免该PAM进程不可读cwd。可读项目cwd、其他权限不明进程、任何身份变化仍拒绝；不发送信号或清理系统服务。实际匹配原件及SHA记录进claim/终态。

新生产工具SHA6cc17ff2dc27abdf2b4681c82a8e3655b221000ff3fe20d41edf0df7cca45b35、测试0bf92476339f6087096ba5c44ac2aa15fd967c3a28ce32ba6ef12449e6beea07；依赖9cf不变。一次9项Windows CPU-MOCK全部PASS/0skip，0.103秒（父驱动0.290秒），源码前后不变、temp空；仅Windows fixture不比较ctime，不证明Linux机制或目标suite。

新wrapper与上版唯一差异是工具SHA由b521改6cc，两个模块仍须全部核SHA后才执行。实际恢复须新G5/push/三端字节和fresh准入，data仅一次恢复且目标/evidence仍不存在；env/model尚未运行，之后各以独立fresh票准入。三单位源保护、300秒proof、900/120秒、排他claim、无自动重试、RELOCATION_PENDING限制保持。

[窄恢复G1及前阶段时间更正](g1-pam-raw-recovery.md) · [G2](g2-pam-raw-recovery.md) · [首次真实失败](asset-data-run.stderr.log) · [无写入证据](asset-data-failure-inspection.json) · [父子身份只读原件](asset-pam-parent.json) · [9测试原始结果](asset-tool-tests-pam.json) · [具体wrapper](asset-wrapper-pam.py)

当前尚无远端资产复制成功，不改环境/shebang/RUNPATH，不跑GPU；旧源、原始结果与旧发布不变。
