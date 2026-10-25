独立只读审查，本次G4离线结论、G5离线批次交付及下一阶段A方案的G1范围。只用Read/Grep/Glob；不改文件、不执行命令/实验/网络/SSH/GPU，不读凭据或聊天历史。最多8次只读调用，输出1200汉字以内，15分钟上限。继续本会话已批准G2/G3；前次G2 B1已关闭。

先读以下小文件，避免递归Grep或大文件截断：
1 outputs/epd-followup/report.md
2 outputs/epd-followup/results/independent-recalculation.json（16格，含三次重复关键值；标准库statistics.quantiles inclusive直接重新读原始请求复核，与analyze.stats独立实现）
3 outputs/epd-followup/results/paired-mean-differences.json（8成对，ΔE2E逐项可算术核对）
4 outputs/epd-followup/README.md
5 outputs/epd-followup/next-experiments.md
6 outputs/epd-followup/scripts/render_report.py（图和报告代码，未改已批analyze）
7 results/analysis.json只读开头约170行的scope/4800来源和before/after，不读全大JSON
8 预算允许抽查results/raw-field-samples.json一个低负载或高负载样本的128stamps/原事件；必要时用具体源路径一格requests.jsonl的一行交叉核对。samples是未更改字段机械摘录，不是生成的模拟数据。

实际完整分析已退出0：16配置4800正式，969原payload+固定原ZIP(3d1253…be38)分析前后哈希相同；每caseTTFT/TPOT/E2E P50/P95对账封存摘要通过。另独立标准库分位数重算全部case首次间隔、后续126间隔P50/P95/P99/mean、TTFT/E2E；0重复时间戳，2400 EPD decoding_begin都更靠近最后通知。mean差异每请求/同样300均值可相加，不加分位数。数据来源两host分开、C1后补会话、诊断/预热/旧被替代都排除。两图已主执行者目检无截断。9 CPU测试通过，首轮合成fixture CRLF失败原日志保留。

请G4核对：结论是否只限通知窗口；低C1增加127.63/131.11ms中后126间隔114.98/118.52、首gap4.87/4.70；高4/C8的基线后间隔P99约147ms、EPD约19–20ms不能推导吞吐更好或prefill因果。reported_decode不作解释。means与tail、n和相关性局限是否充分；无效TTFT链0/2400、KV CPU调用end<=第二API stamp仅CPU/API单向事实。

请G5仅核对本离线批次：可复跑脚本/来源SHA/旧冻结不变/CPU测试/G1–G4范围/报告图与下一阶段具体proposal齐全。若批准，主执行者只更新真实Gate和完成记录，复制本审查/提示词，保存最终AGENTS快照，生成本批SHA及ZIP并逐文件核验；不得改旧包或新增数值/因果。不把第一轮已complete目标重新改active，不创建新长期目标。

另请给A方案的G1建议：next-experiments中保持模型/协议/三卡预算、2系统×2点×2观测模式=2400正式+160预热，有限CPU/CUDA trace、API/Ray标记与启闭扰动对照；实际实现需G2及用户确认后才能用GPU。B的PD涉及原“不做DistServe基线”，这里只做静态候选，未实施，须用户单独同意范围。不将本G5批准当GPU授权。

输出分别G4、G5（离线批次）与下一A方案G1 APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING数量/最小处理、NON-BLOCKING。证据不足时精确指出，不因调用预算而把实际未读范围写已验证。已有独立代码/事件审查可引用，不需要重做全部CPU/GPU实验。
