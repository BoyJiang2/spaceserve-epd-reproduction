# 项目执行文档维护记录

2026-10-23，按用户要求维护 `D:\Documents\codex\AGENTS.md`，作为后续项目工作的执行依据。

本批次已更新两台 H20 的实际进展，修正 qjh005 目录权限仍待解决的过时状态；区分通信数据损坏的实测事实与尚未证明的 IOMMU 因果关系。新增每批项目变更必须记录原因、文件与证据、验证结果、审查状态、未完成项的要求，保留既有目标、实验设定、安全边界与 Claude G1–G5 审查门槛。

已记录实验早于本轮执行文档引入的时间顺序，补审不能冒充事前批准。只读审查提示词保存在项目 `reviews/prompts/g1-g4-h20-adoption.md`，审查完成前不宣称通过。

后续更新：qjh003 的3,600条正式请求与qjh005的1,200条均完成归档和技术审计，报告草稿及图表已汇总。Claude CLI 返回HTTP429、会话额度耗尽，提示上海时间12:50重置，尚无审查结论。本次调用耗时超过执行文档15分钟上限，已记录偏差，后续拆分审查并显式控制时限。

项目整体未完成，G1/G2补审及G3/G4、G5尚待进行；最终状态以 `experiment-status.json`、原始数据和审查结论为准。执行文档快照见同目录 `project-instructions-snapshot.md`；维护仍以用户指定的原文件为准。

## 用户授权后的更新

已在原AGENTS第3.2.1节明确：Claude额度耗尽时立即由独立subagent接替，无需重复确认；只读审查、G1–G5、BLOCKING处理与真实审查来源记录不放宽。此前额度失败是历史事实，不使已取得的subagent批准失效。

G1/G3现为APPROVE_WITH_NITS，G2 RGB具体修复及完整复跑补充均APPROVE。G2/G4发现的首单图C1缓存初态问题已实际完成两台成对补测，原推理预热及正式协议不变。补测1200正式、80预热及16份实际RGB快照均通过技术核对；G4数据复审仍在进行，G5未批准，项目尚未完成。详见reviews/review-followup-20261023.md和report/cache-fix-acceptance.json；最终状态以experiment-status.json为准。

最终更新：G4独立复算关闭B1，G5在Claude额度恢复后由Claude实际APPROVE_WITH_NITS、BLOCKING0。用户的subagent接替规则与G1–G4实际审批保留，完成记录及最终证据已同步；真实最终状态见experiment-status.json，旧待审文字按日期保留为历史。
