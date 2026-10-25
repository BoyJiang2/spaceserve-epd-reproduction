# G2：000冷启MPS idle状态最小兼容修复

先读D:/Documents/codex/AGENTS.md。只读，不改文件、不跑实验、不访问GPU。Claude实际quota错误见outputs/epd-profile-a/reviews/g4-cuda-report-claude.json及本批g2-model-runner-claude.json，按3.2.1接替。

前runner G2已APPROVE_WITH_NITS/B1关闭。实际预检PID3757566在任何模型启动前，capture_mps_clients.py拒绝driver535空私有MPS的精确响应Server not found；自动清理退出1、GPU空。原始control.log记录Cmd:ps后Server not found，且二进制strings有该原文；重试前将原failed目录精确保留。

仅审查新增delta：outputs/qjh000-migration/scripts/capture_mps_clients.py、test_mps_status.py。
- parse_clients仅allow_no_server=True且text.strip()完全等于Server not found才接受空clients；只有args.api_pid is None时传True。加载后仍拒绝。
- 输出status.txt保留原始响应，再解析。
- 其余UID/root/runID/私有pipe/物理UUID/NVML/加载后非空clients守卫不变。
CPU回归5项包含首次失败复现/活动模型拒绝/数字PID混合和未知错误拒绝/正常客户端列/坏列拒绝。本地通过，Linux实际证据outputs/qjh000-migration/evidence/mps-status-cpu.log（若尚未复制请等主执行者补齐，不推断结果）。

请判断是否仍fail-closed，允许同一冻结preflight_model.sh重新cold/restart诊断，不批准formal或服务G3。
输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号与理由，NON-BLOCKING，QUESTIONS。
