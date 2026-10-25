> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g4-points-prompt-draft.md) SHA256 a64116b4dad98578ab33da4c29e3be2242016f1e0144f4697759ad644efdf67a。原数字及解释不变。

# G4：三组首轮低／高两点（待真实数据齐全后提交）

独立只读审查者，先读D:/Documents/codex/AGENTS.md。不得改文件、访问GPU、启动实验、读取凭据；可在本地CPU读取/复算现有原始数据。主执行者负责所有实现/GPU。Claude同批额度失败证据outputs/epd-profile-a/reviews/g4-cuda-report-claude.json，依3.2.1接替。

当前验收范围：qjh000 Qwen2-VL-7B FP16 TP1 eager，GPU0固定UUID，native/Space/有效encoder SM三组，1图/C1和4图/C8六配置，共1800formal+120warm。每配置20warm、100formal×3、128tokens、实际256视觉tokens/图。先G4通过才允许其余四点；本审查不冒充完整六点/G5。

已通过实际cold+restart G3及正式/采样/统计/绘图G2。旧300formal+20warm因采样起始gap0.310766>0.3s被拒绝，完整保存在results/formal-memory-failed-20261023T2038.tar.gz且不选用；只优化每次NVML PID归属查询后重新从首配置运行，审计阈值/模型/协议没改。审查g2-memory-sampler-subagent.md，前后SHA与CPU证据evidence/。原003 EPD受限交付已封存，不重跑/覆盖。

提交前主执行者必须填实际archive SHA、formal PID、actual code SHA和本地完整性记录。本稿未提交/非批准，严禁预写结论或G4 marker。

实际文件（齐全后才审）：
- results/formal/points/{baseline-space,space,space-mask}/images{1-c1,4-c8}/measurement/{requests.jsonl,summary.json,config.json}，及所有memory/RGB/MPS/runtime/device-records/COMPLETED。
- results/formal/{points.sha256,points-manifest.sha256,POINTS_READY_FOR_G4,mps-start.json,used-scripts/}。
- evidence/formal-points-{transfer,local-integrity,payload-sha}.json、formal-approved-code.sha256和实际boot/GPU容量。
- analysis/space_results.py、scripts/audit_formal_case.py及report/space-points.json、report/space-points-report.md、performance-points.png/svg。
- G3和所有G2真实reviews、evidence/memory-sampler-fix-adoption.json。

请独立核查：
1. 六配置和全1920行完整无重复，正式/预热分开、每次128输出/真实视觉tokens、有效token时间域/端点/请求路由。重复summary从raw自行复算P50/P95、throughput窗口及三次SD，不能仅信savedsummary。
2. 全部320keys输入图序和processedinput IDs在三组一致；保留并准确报告任何output IDs差异，不能凭性能宣称全一致。
3. 真实同一物理GPU与MPS100、actual FP16参数组件（LM保留visual+另encoder）、API/worker/私有MPS边界和全程每显存样本PID/容量/求和/时间覆盖。formal profiler/probe确实关闭、无其它项目负载；边界不代表排除任意瞬时进程。
4. 双层SHA逐项/完整集合/唯一性覆盖points全部实际regularfiles，代码freeze与used-scripts实际一致。仅技术audit与哈希不代表独立G4。
5. 图表/报告数字单位和实际布局目视正确，吞吐三次均值±SD、延迟300formal pooled inclusive线性插值P50/P95、失败率及全进程采样峰值口径准确，既保留收益也保留退化。
6. 机制范围encoder-only、不声称decoder互斥/fullSIS/TPC或资源比例；trace交叠不是加速。固定并发不是SLO，不能因果归属所有差异。权重与额外驻留、processor kwargs被丢弃警告均披露。旧EPD/2B不混作同机数据。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号+理由+建议、NON-BLOCKING、QUESTIONS。仅回主执行者，不写marker。只有有效G4后由主执行者将points-manifest.sha256原bytes复制为G4_POINTS_APPROVED，并先结束CPU分析/导出再让同MPS/同锁扩rest。
