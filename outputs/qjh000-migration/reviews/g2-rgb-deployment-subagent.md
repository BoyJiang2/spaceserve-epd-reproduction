# G2：部署遗漏RGB helper补全

实际审查者 /root/profile_runner_review，只读。Claude额度接替依据同本批前审，提示g2-rgb-deployment-prompt.md。
结论APPROVE，BLOCKING0。
已独立核对旧7B、新000及封存reproduction的rgb_cache.py，三份SHA256完全一致：02c81034681535b83e35a03ea5f34970d21b640291965d9ba73553b62bab04c7。仍20图、RGB448x448及像素SHA校验，没有新增推理或采样。已读CPU导入/--help输出。
仅批准冻结代码cold/restart诊断；不批准formal/服务G3。审查者未改文件、执行代码或访问GPU。
Codex落实：首次缺module的cold原结果与启动日志精确保留；补helper无改动后重新冻结完整脚本与实际fork核心SHA。
