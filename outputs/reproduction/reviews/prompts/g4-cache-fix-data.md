独立G4实际数据复审。先读 D:\Documents\codex\AGENTS.md；项目根 D:\Documents\codex\2026-10-23\new-chat-2。Claude额度耗尽已有明确usage_limit_reached证据，按用户授权由你接替。只读：不改文件、不运行实验、网络、SSH、GPU，不读凭据，不发送外部消息。

补测现已真实完成，前次代码预审不是数据批准。请对实际归档、统计与报告给G4结论 APPROVE / APPROVE_WITH_NITS / REQUEST_CHANGES，明确原B1能否关闭及剩余BLOCKING数。指出文件行号与具体最小处理；不要因为主执行者审计passed就直接认可。

B1：旧单图/C1全局20推理预热，EPD缓存20图，三副本各7/7/6不公平。修复经G2事前APPROVE：启动只加载同20图实际RGB buffer，无模型前向，无额外推理；实际缓存前后像素SHA逐服务检查。原20预热+100正式×3不变，仅两host各EPD/基线四配置成对补测。其余负载继承原非淘汰缓存。所有旧原始请求保留。

请核对：
1. outputs/reproduction/data/cache-fix/qjh003/{epd-h20,baseline-epd-h20}、qjh005/{epd-h20-qjh005,baseline-epd-h20-qjh005}：各320行(20+300)，1200正式80预热，无失败、128输出token，配置与原预处理/请求一致。每host根的日志、used-scripts、COMPLETED及gpu-processes-after.csv。
2. report/cache-fix-acceptance.json（两host均passed）、实际rgb-before/after快照及runtime-config：16快照，每20源图，实际API PID绑定；独立重解码COCO；库路径集合与旧快照相同。代码 scripts/audit_cache_fix.py、rgb_cache.py、check_rgb_cache.py。基线固定正确性仅endpoint0，RGB及正式请求覆盖所有副本，别扩大正确性范围。
3. report/h20-cache-continuity.json、scripts/audit_cache_continuity.py：原其余配置是否有持续服务PID、顺序图片请求及非淘汰字典证据；这是覆盖推演，不是实测缓存命中成本。report/raw-preservation-audit.json：189旧文件未变，仅4validity元数据变化。report/timestamp-order-audit.json：16000条时间戳检查。
4. report/summary.json/csv与output-comparison.json同时选择新低负载source_kind/cache-fix，同case两端配对，无混旧。scripts/summarize.py、compare_outputs.py、make_report.py、verify_delivery.py。代码预审两建议均已修正：报告/验收断言精确两个target/case配对集合600条；cache验收对照旧实际库路径集合。
5. 全归档15矩阵50配置15000正式1000预热，最终选46配置13800正式920预热；12000有效、1800旧L20 EPD诊断，另1200旧H20低负载被替代。有效配对5400、诊断1800，共7200，6416exact output matches。固定服务194案例范围不可泛化。
6. report.md及report/completion-audit.md、experiment-status.json、delivery-audit.json。qjh003六点0.89–0.99吞吐比，qjh005低高约.93/.95，没有吞吐加速。SpaceServe旧结果范围不变，4090 SM mask不可用，L20可用；不得推导论文规模、SLO或调度因果。

G1/G3 APPROVE_WITH_NITS，G2最终APPROVE，实际review在reviews/subagent-*.md。G4 B1仍开放，G5未开始，goal_complete=false。不要求你批准G5。本次聚焦修正后实际数据与报告能否关闭B1，其他历史review不伪造为事前审批。
