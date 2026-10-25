> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/reproduction/reviews/prompts/g5-final-delivery.md) SHA256 5a6b1faeeddc0676d56b2b4022957285fd49f94196a6f99c5d4a9fbd05da179e。原数字及解释不变。

你是全新独立G5审查者。只读，不改任何文件、不运行实验、网络/SSH/GPU、不读凭据，不发送外部消息；可用本地只读代码解析/哈希核对材料。项目根 D:\Documents\codex\2026-10-23\new-chat-2，先读 D:\Documents\codex\AGENTS.md。

Claude CLI已明确usage_limit_reached，原证据 outputs/reproduction/reviews/claude-availability-20261023.json；用户授权额度耗尽时独立subagent接替。你不承担实现，不继承含凭据聊天历史。

G5：对照AGENTS完成标准，判断是否可以完成既定SpaceServe/EPD小规模复现目标。请给 APPROVE / APPROVE_WITH_NITS / REQUEST_CHANGES，BLOCKING具体文件行号/原因/最小处理，NON-BLOCKING及QUESTIONS。必须自行查看证据，不把主执行者的passed当作独立证明。只审本轮约定范围，不要求论文全量/新增DistServe/跨机实验。

目标：qjh003 H20跑EPD全矩阵1/4图×C1/4/8，qjh005同硬件独立低1/C1高4/C8；每台E:P:D=1:1:1对同机同三GPU的3个完整模型副本；MiniCPM-V-2_6 FP16 TP1，IRP/动态角色off，20预热+100正式×3，128输出tokens。合并既有Qwen2VL2B SpaceServe4090/L20。无加速也可完成，必须保留负结果/限制/原始数据。

入口：outputs/reproduction/{goal.md,README.md,report.md}；report/{completion-audit.md,experiment-status.json,delivery-audit.json}。先检查G1–G4实际审查原文和处理记录，尤其最新G4实际数据复审 `reviews/subagent-g4-cache-fix-data-20261023.md`，勿将代码预审当数据批准。审查者来源均独立subagent，历史补审不伪造成事前批准。G5此刻pending、goal_complete=false正常；审批后主执行者只更新真实审批记录/完成状态/AGENTS快照并重生成报告、SHA清单和最终ZIP。

重点：
1. 两台通信：evidence/<host>/preflight-20261023T*目录、kv-actual-cache.json、epd-epoch1/2及*-c8.json、baseline-reference*.json及runtime快照，report/h20-acceptance.json。G3审查支持P2P、embedding、原生KV、冷启动及一次重启后并发正确；60553是分配规模，每次只传18blocks约15.75MiB，常数模式不足以排除任意维度置换，固定端到端案例补充。基线固定检查首端点，不能称所有图片语义质量通过。
2. G2/G4 B1：旧首1/C1的RGB缓存初态不公平；G2事前批准实际纯RGB预载修复及读真实缓存证据接口，只成对补测4配置，保留原20推理预热/100×3。data/cache-fix/、report/cache-fix-acceptance.json，16前后快照每20源图、PID/UUID/boot/加载库路径绑定；非推理预载，无embedding/KV预缓存。旧其余负载缓存连续性报告h20-cache-continuity.json是源码/顺序/稳定PID支持，不能当实测缓存开销。
3. 全归档15矩阵50配置15000正式1000预热；最终选46配置13800正式920预热：12000有效、1800历史sapphire3 EPD仅诊断，另1200旧H20低点保留被替代。摘要与输出配对相同cache-fix来源；有效配对5400+诊断1800=7200，6416exact outputs，不称全正式等价。194固定服务案例含7历史诊断；SpaceServe参考语义局限须保留。
4. report/raw-preservation-audit.json、pre-cache-fix-SHA256SUMS：189旧文件未变，仅4validity元数据变化；timestamp-order-audit.json全部16000时间戳；h20-final-script-provenance.json与h20-final-replay-differences.diff明确实际旧运行与最终复跑版本差异。运行用7文件SHA对cache-fix-code-manifest.json，final合并EPD补丁epd-h20-cache-fixed.patch，不叠加历史patch。
5. 四问题回答/不夸因果：H20三个GPU预算无吞吐加速，003六点0.89–0.99×，005低高约0.93/0.95×；SpaceServe L20高负载约1.25/1.30×但TTFT更差，4090 SM mask不支持，只有L20mask有实际证据，公开fork非完整论文调度。sapphire3旧纯CUDA损坏是诊断，无维护因果实验证明IOMMU唯一原因。
6. README可复跑命令、模型版本/SHA而非权重入包、patch最小、raw/图完整、SHA清单与work/g5-candidate-integrity.json候选包校验。只读核查，不自行启动命令做GPU复现实验。图表PNG均已主执行者目检；你可查看需要的PNG。

候选SHA/ZIP生成时G5仍pending。若批准，最后新增真实G5审查记录和修改状态会要求重新打包，这是预计的收尾操作，不表示测量数据可以修改。请明确是否有必须修复的交付或证据问题，及批准的具体边界。
