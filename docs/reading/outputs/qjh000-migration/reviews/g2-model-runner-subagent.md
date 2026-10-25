> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-model-runner-subagent.md) SHA256 7712bf784b4cbbfe608a30e0d46b348f627ea2afdc42b1f16e0058436ee3e413。原数字及解释不变。

# G2：qjh000 7B预检runner

实际审查者：独立subagent `/root/profile_runner_review`，明确Claude usage_limit_reached后按AGENTS3.2.1接替。未运行GPU/实验，不改文件。原超时记录不是批准或quota证据，拆分Claude原始额度错误仍保留。

首审REQUEST_CHANGES，B1：stop_server只按命令root子串和UID判归属，先终止整树，后续cleanup_owned不能补救；需精确root/runID及外来后代保留测试。

Codex修复：所有目标先整体核同UID/精确EXP_ROOT/当前REPRO_RUN_ID，不符先存拒绝证据，不发信号；TERM/KILL前再核，已退出zombie不读受限environ或发信号。实际Linux三CPU用例证明本run可清、同root其他run/外来后代均保留；失败时发现zombie二次读environ问题已保存并最小修复，PASS日志evidence/stop-identity-cpu.log。

另按hooks G2建议新增启动时角色/实际libsmctrl发现守卫；未划分forkCPU实际发现None，evidence/unmasked-sm-discovery-cpu.log，避免系统fallback意外划分。

复审原文：**APPROVE_WITH_NITS。B1关闭，未解决BLOCKING为0。** 已读取修补代码与真实Linux日志：整体及逐次精确身份、拒绝存证/保留外来目标、三CPU用例、角色与库发现一致性守卫均通过。

批准仅模型预检runner与上述修补；输入IDs/实际输出长度/C8路由仍须实际G3核验。500次health重试加每次最多1秒curl/1秒sleep，上限可能接近1000秒，并非严格500秒。实际服务G3与formal另审，native布局不能替代。
