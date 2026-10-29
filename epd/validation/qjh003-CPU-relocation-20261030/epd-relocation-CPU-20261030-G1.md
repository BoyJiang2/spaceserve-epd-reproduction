# EPD CPU 重定位续接计划 G1

reviewed_at_utc: 2026-10-29T22:17:04Z

reviewer: 独立 Codex subagent `/root/fallback_g3`，按 AGENTS.md 3.2.1 接替 Claude 额度耗尽后的审查；本人未实现此变更。

**APPROVE_WITH_NITS / BLOCKING 0。仅批准计划中的最小本地配置/工具修改、必要本地反例与回归、随后提交独立源码 G2；不批准当前远端 apply/verify、发布执行或任何 GPU 工作。**

绑定计划 `epd-relocation-CPU-20261030-plan.md`，实际 SHA256 `844c59aee8bcb128adeb59ded99e9170a88dca7e7822d6078466c41c861ae2f5`。

## 依据与范围

1. 已读取旧 `epd-relocation-apply` 的实际 exit1、stderr 和独立 actual-review。错误位于 CPU/整机预约冲突准入，在该次 stage/claim/资产写入之前；没有成功 apply，更没有可据此启动 verify 的成功回执。此控制流证据不等于本次远端事后检查所有资产均未变。旧失败、旧配置和封包均应原字节保留；本审未做远端读回。

2. 已只读核当前 checkout HEAD 为 `24b441923119581ab1c5e3274eca7d654021675d`；当前旧工具 SHA `117825a06f38c6cd70221132e87ac09aa204ac16c83783c2c181c6d95d9a74c2`，配置 SHA `5e2ad79aaca28dbc9588540ecd8e0e4c4f222176335b30e6063f33a73e5af1d7`。旧配置确为16–17 direct_user_instruction，61项由51 console、5 activation、5 unchanged组成，3条固定 Python links；original nested IPC pin、flat目标及3项 RUNPATH 均明确。受审两旧源无本地变更，新配置尚未出现。不能把旧许可或历史源码 G2 外推给新窗口。

3. 本地已存 `epd-CPU-20261030-booking-plan-read.json` SHA `ff69fac473a5dd748b0b96ad225a7cd71cb9eeab3156811c8824bc3fc2affbd7`，observed_ms `1793311978453`，记录 active h20/qjh003 与本人 CPU `bk-20261029T1809-58743aa0`，04–11，start `1793304000000` / end `1793329200000`。这支持设计新 own-ticket scope；它不是未来执行的 fresh 证明，也不证明当前 CPU50 或项目进程可用。本审没有联网复核。

4. 计划第9–10行的最小改动合理：新增独立配置，保留旧配置；仅把 stage、CPU许可替换为本次精确值，并使工具 CONFIG_SHA/window_end/cpu_permission/claim 与真实 own-ticket 合同一致。无须为此创建新的迁移框架、重新建立环境或改写61项资产规则。原nested库不变、只复制flat库再改 RUNPATH、NEEDED不变；56文本变换仍是固定路径替换，不能顺带修包/依赖/解释器或系统设置。

5. 保留原只读 pin/links/startup 检查、CPU50/nice10/boot/UID、未知或不符即拒绝、排他 stage、先backup再atomic rewrite、逐项 journal/终态、apply120+30、verify60+30及票结束前120秒余量，符合静态资产维护范围。无需导入 Ray/Torch、dlopen、加载 IPC、CUDA/NVML、模型或系统维护；静态 ELF readelf/patchelf 并不构成运行时加载验收。

6. 计划明确独立 EPD 分支发布、Space main/HEAD24b 与服务器 Space checkout 冻结，维护工具 commit 与 EPD runtime repo 实际 commit 分别记账，避免把传入 Git helper 冒称整个 runtime 已部署。后续只能在 Space 无活跃模型/正式单元且本有界维护已结束/受控收口后进入 GPU；原工具另有自有项目进程检查，不能为并发而放宽。Space恢复优先不意味着对正在部分写入的维护强制丢弃或无证据重试。

## BLOCKING

无（仅本地最小续接设计）。

## NON-BLOCKING / 后续实现与准入检查

1. 源码 G2 必须实际核拒绝旧 direct scope、精确 own CPU ticket/core字段及整数类型（拒 bool/非整数）、唯一同ID票、observed时效、起点、完整 work/cleanup 与 END-120边界、缺失/重复/篡改票，以及他人 CPU/整机交叉时段。不得只把配置票号写入 claim 就令 `reservation_claimed=true`；须在实际 fresh proof 完整核验通过后如实记录。旧实现的冲突检查和保守预留不能因适配新票而缩窄，整个允许操作及清理区间应受保护。

2. 新配置与旧配置除唯一 stage 和 CPU许可外，应逐字段/成员验证一致；工具除 CPU scope/CONFIG_SHA/真实 claim 及直接相关测试外，不改 rewrite、pins、links、IPC复制、RUNPATH或原失败处理语义。新增 stage 不能掩盖既有 flat库/partial：原flat或意外stage已存在、源pin不同、未知startup、所有权/链接异常均仍写前拒绝并保存证据，不清除后循环重发。

3. 分支发布前须有独立源码 G2、必要真实本地测试原件及精确候选 G5，再正常commit/push/远端逐字节核验。不得更新Space main/HEAD24b或其运行源。此次G1不是发布批准，亦不把本地mock通过当目标资产或真实环境已迁移。

4. 实际维护需另审精确命令/transport、指定发布commit/tool/config SHA、唯一新本地output和 fresh现场/票据；旧失败命令不重发。只在单次apply真实成功、原件下载逐SHA且独立实际审计通过后，另fresh、另命令审查首次verify。任何partial/UNKNOWN保全停止，不回滚重试、不伪造成功。现有GPU第三方占用不授碰触其进程或探测其环境的权限。

5. 计划第15行“清除环境障碍”是目标，不是已证实结果。成功最多证明静态重定位/特定pins与RUNPATH检查完成；不能推出Ray生命周期、动态加载、CUDA IPC、native36、模型、公平PD或性能通过。后续真实Gates与资源许可独立保留，Space正式54/201分钟/06:37入场及主窗硬截止不受本CPU计划改变。

## QUESTIONS

无阻塞性问题；无需重复询问已授权的本地CPU准备。当前尚无新实现、测试或目标成功结果，须按上述流程提交实际证据。

本审仅读取计划、已存预约原件、旧配置/工具、旧失败与既有独立审查，以及本地Git身份/局部状态；未运行测试、网络、SSH或GPU，未修改源码或原件，仅新增本报告。

GATE_RESULT: {"gate":"G1-EPD-relocation-CPU-20261030","decision":"APPROVE_WITH_NITS","blocking":0,"plan_sha256":"844c59aee8bcb128adeb59ded99e9170a88dca7e7822d6078466c41c861ae2f5","local_minimal_implementation_and_tests_approved":true,"publication_approved":false,"remote_apply_approved":false,"remote_verify_approved":false,"GPU_approved":false,"runtime_ready_granted":false,"Space_source_change_approved":false}
