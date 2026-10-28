# 原始资产物化的本地软件准备

生产工具SHA为b521ccfccc423598c467802ecd4cc1258f0c90073ff226c8a759aac55bbae957，测试最终SHA为c45a87e1d762b02f2e2a0871fba610219f793ce52ebaa16716e12802de49a401，依赖迁移工具9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405未改。

首次Windows CPU-MOCK实际6PASS/1ERROR；原日志保留。复制后fsync+chmod的Windows3.13 lstat/fstat仅ctime字段不同，两个独立微诊断保留。经G2恢复批准，仅Windows fixture不比较ctime；生产Linux工具所有守卫不变。一次纠正7PASS/0skip，0.086秒（父驱动0.252秒），源码前后不变、临时根空。该结果不证明Linux ctime/nofollow、POSIX信号、目标套件或GPU机制。

执行前两runtime保持a3f03b9dd5956db92add454f9b3afd5663f84609，辅助工具另记实际push commit。远端wrapper通过SSH标准输入接收JSON source payload（避免Windows命令长度限制），每个模块先base64解码并核原始SHA，再在独立标准库module命名空间执行。migrate_code_cpu先载入sys.modules，后执行materialize_assets_cpu；只传固定unit、真实API证明、runtime SHA和tool SHA。payload及实际argv、stdout/stderr、PID创建时间、exit全部持久化。远端外层CPU50/nice10、900秒TERM、120秒kill-after；Python内部deadline900秒与API300秒更严格。每unit新fresh票、源目标条件、boot/UID/核验不可省略。执行不更改冻结runtime源码，也不从旧源码树导入工具。

[具体范围与命令约束](../asset-materialization-plan.md) · [代码部署独立审查](deployment-audit.md) · [G1](g1-asset-materialization.md) · [G2](g2-asset-materialization.md) · [Windows恢复G2](g2-asset-test-recovery.md) · [首次失败](asset-tool-tests.stderr.log) · [纠正结果](asset-tool-tests-corrected.json)

远端尚未复制资产。成功后也仅RELOCATION_PENDING，IPC RUNPATH和环境shebang尚未重定位；Space环境及Qwen完整模型仍缺。源旧目录、旧raw/七ZIP/Release资产不改不删。
