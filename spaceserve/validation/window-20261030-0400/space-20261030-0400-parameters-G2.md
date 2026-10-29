# 04:00新run proposed参数 — 独立G2

reviewed_at_utc: 2026-10-29T18:25:22Z
reviewer: /root/gpu2_report_g4

**APPROVE / BLOCKING 0，仅精确proposed参数及既有prepare/read/require_scope语义；不批准代码新增、部署或CPU/GPU/formal运行。**

实际SHA核：`spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json` = `bed4d393153f41817efd39d44c0548822f793ca976f3e015f582debe57255bd9`。独立逐字段比较旧GPU2 model cfg `677e9179b6f76c2a93de68cf379fb88d9be668a25682df125dc0fb382b56c2ce`。只读核配置、reproduction_paths.py、entry.py、stage_cpu.py、booking_window.py及已审04:00计划，无测试、网络、SSH、GPU或改实现，仅保存本审查。

## 精确参数变化

run_id由space-16-20261029改space-formal-20261030-0400，旧model-only actions改numeric/model/formal，新本人booking a2228913/1793304000000–1793325600000（04–10）。删除旧运行生成的source_commit、source_manifest_sha256、asset_manifest_sha256及旧scheduled_gpu_start_ms、cpu_preparation_deadline_ms、scheduled_user_sha256。其他schema/project/root/state/host/UID/GPU2物理编号与UUID、cuda_home、workload CPU0–89/NUMA0、mask56与兼容性proofSHA、HTTP新连接无重试契约逐值相同。不存在temporary_gpu_use或10–11自动延期字段。

新run组件26字符，满足单路径安全格式和32上限；单GPU型号与模型/精度等固定行为仍由具体源码与真实运行证据约束，不从JSON缺省字段推定模型正确性。

## 三段语义闭合

- ProjectLayout.read读取结构、项目、固定host/UID/root及GPU列表，不授GPU；approved_scope只代表已明确授权的候选范围。允许动作列numeric/model/formal并未提前写任何阶段Gate或成功marker。
- entry.prepare在require_scope之前分派，要求实际--commit，stage_cpu.prepare先核真实host/UID、独立run不存在、资产清单/保护pins；由deploy_commit_cpu生成实际deployment，再冻结project.json中的source_commit、source_manifest_sha256与asset_manifest_sha256，并记录源proposed配置SHA。故proposed不预填自引用commit合理，不会绕过源身份约束。CPU_STAGED只是CPU_PREPARED，不等于实际CPU suite或GPU通过。
- numeric/model/formal入口先require_scope；此函数必须拿到真实source_commit及source_manifest_sha256、本人booking后才可继续，然后entry仍核GIT_DEPLOYED与冻结配置/manifest身份。原始proposed缺source字段，不能直接当完成部署配置运行。booking_window还核实际owner/node/lane/票ID/起止、after-start及fresh<=300秒和END120；本配置没有extension，EXTENSION_ID=None拒绝携带延长receipt。各phase自身G2/G3/锁/idle/预算仍必须执行。

## 不可外推的批准

实际新增配置须依Git-first提交发布指定新commit，再部署且生成新source清单。不能继续将新增文件称属于旧730；已封存GPU2 run仍保持原730。04前他人CPU/GPU范围不可动；04后fresh真实票/boot/NUMA/GPU2严格0/apps空/全SHA由具体执行工具核。监督器CPU50nice10和OMP4是既定方案，OMP4不代表总线程4。本参数未降低原54/5400+1080、全新CPU/numeric/313及actual Gates和201分钟formal入场要求，未授权重试或借旧PASS。

当前只批准配置字段；完整启动/控制/清理命令、具体新commit、生产源码差异及实际执行仍需相应独立G2/G3等审查。本审没有生成marker、测试、部署或访问GPU。

GATE_RESULT: {"gate":"G2-space-20261030-0400-parameters","decision":"APPROVE","blocking":0,"config_sha256":"bed4d393153f41817efd39d44c0548822f793ca976f3e015f582debe57255bd9","scope":"proposed_parameter_identity_and_prepare_contract_only","GPU_approved":false,"formal_approved":false,"deployed":false}
