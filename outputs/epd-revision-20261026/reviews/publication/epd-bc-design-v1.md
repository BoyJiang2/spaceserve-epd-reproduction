# EPD新批次B/C详细设计 v1

状态：详细G1已于2026-10-26经独立subagent修正跨负载配对后APPROVE_WITH_NITS/BLOCKING0；实际记录reviews/g1-bc-recheck-subagent.md。不是整体GPU批准，G2/G3及各阶段范围必须分别落实。用户已授权推进讨论方案；本文冻结实现前的具体候选，审查意见和用户已授权范围共同决定是否可执行。qjh000是测量主机，qjh003只作只读环境来源，不使用其GPU。

## 1. 独立环境与资源

新root `/var/tmp/boyjiang-epd-revision-20261026`。B0仅迁移固定EPD环境、模型、CUDA扩展、HF远程模型模块和dataset，不迁移旧G3/G4批准标记。`CPU_STAGED.json`不表示CUDA/模型通过。迁移由正常客户端SSH中继，两端成功及manifest匹配后才完成；旧root不写。

候选GPU0/1/2，同NUMA0：GPU-d1b595ce-0b57-cdee-c1c0-9b1051aaa07e、GPU-54dd3d98-9c22-b235-34ba-f02a9edcbb9d、GPU-02967d7d-61eb-a053-5cfe-a964f8d35832。盘点仅是瞬时状态；每次启动前重新检查UUID/空闲、主机boot/拓扑/存储、进程及本项目排他锁。出现他人任务即停本项目，不清理他人、不改驱动/IOMMU、不重启。正式测量期间同机本项目不下载/编译/Space负载或导出分析。

执行前固定新root/src实际累计diff、脚本SHA、模型逐文件SHA/实际HF模块、package freeze及实际cuBLAS路径/SHA；旧二进制扩展必须新主机CUDA IPC/embedding/KV数据一致性探针与冷启/重启正确性重新通过。基线与EPD同三GPU预算，禁用MPS，与旧EPD协议一致。

## 2. 保持与必要变化

MiniCPM-V-2_6，FP16，TP1，eager；EPD 1:1:1，IRP/角色切换关闭；原native vLLM0.6.1.post2三完整副本，均衡轮转。RGB预载相同20张固定图、同预处理、同提示词、temperature0、ignore_eos。prefix缓存关闭，不将视觉token传输缓存称为关闭。上下文4096，max_num_seqs8，max_num_batched_tokens4096，gpu_memory_utilization0.65；EPD原阶段batch1/1/8和tokens限额保持。

**需审查的具体实现选择：**为了避免8图点启动上限不同导致额外混杂，新批次所有点、两系统统一图数上限为8，而非只对D/E改上限。实际请求图数仍按五点表。A/B只称“任务负载锚点”，不再称与历史启动协议完全相同；新的8上限及内存profile影响单列。若审查认为需要独立cap4桥接对照，先修订预算再请求用户确认，不自动加点。

8图不扩大dataset：第index请求第j图为既有manifest顺序的`(index*images+j)%20`；20预热、100正式各从index0开始。各系统与观测模式相同请求序列。正式开始前导出每点120请求的图片SHA/顺序、生成参数及实际prompt模板SHA，生成不再shuffle；运行验证processed input IDs和64视觉tokens/图预期。出现图token或切片策略差异立即停止该点，不默默改尺寸。

单请求超时120秒；任何HTTP错误、输出长度不符、图路由/processedIDs错误停止该点并记失败，不丢行、不自动换精度/上下文/batch。OOM不触发重复搜索。不得把CUDA兼容/正确性预检请求加入正式样本。

## 3. 观测事件及可解释性

主性能off：REPRO_OBSERVE关闭，无新GPU事件，无nsys/torch profiler。源码沿用方案A同一类条件包装，明确不是零补丁上游。

新lite-observe：替换专用副本observe模块，保留相同接口，使用进程内有界事件缓冲而非每事件JSON/磁盘输出；formal窗口内无RPC采集启停或导出。新增observer不在窗内写盘；复用benchmark原有逐请求JSONL write/flush仍在计时窗内，两组同样承担，不能声称整个benchmark没有窗内磁盘操作。启停、缓冲重置、完成后导出发生在计时窗外，记录其实际成本，不混入/扣除吞吐。

| 事件 | 身份/时钟 | 可支持的语义 |
|---|---|---|
| client submit/receive、API首末输出 | run/block/load/mode/endpoint/request-ID；same-host perf_counter_ns | E2E、TTFT/TPOT及客户端/服务端通知边界；首token口径保持不含回传 |
| API preprocess结束、orchestrator入队/出队与生命周期 | 显式request-ID，阶段/事件递增序号，同主机CPU时钟 | 主机排队/状态通知，不能自动解释为GPU执行 |
| engine.batch与worker step begin/end | 显式batch/op-ID、request成员、每成员step序号、PID/UUID、E/P/D | batch参与及CPU调用范围；共享batch不按请求累加成独占成本 |
| embedding/KV engine交接begin/end及worker copy调用 | 显式op-ID与request-ID/源目标block索引绑定；begin/end序号 | 交接调用/等待，含RPC、调度和同步；不叫纯通信带宽/耗时 |
| worker本stream CUDA事件对 | 同GPU同stream begin/end、op-ID；仅输出elapsed_ms | stream上该段活动跨度（可含CPU发射间隙），不是kernel忙时、不是跨GPU绝对时钟 |

GPU事件仅包围实际E/P/D batch及迁移调用。一个op至少有一个明确request成员或迁移映射，否则该op只能列未关联诊断。新增可选metadata参数只传op-ID/成员给worker，不改输出/调度/传输算法；基线从execute_model_req记录成员及prefill/decode标志。不能用跨进程时间最近邻冒充依赖绑定。

每进程最多200000条记录；满缓冲显式overflow使观测验收失败，不静默丢事件。每个batch一次GPU事件对，无逐token全设备同步；CUDA事件在所有请求完成、正式计时结束后查询/等待和导出，导出deadline60秒。事件和结果均需覆盖完整GPU stream；自定义copy stream无法证明被包围时，迁移CUDA列明确未覆盖，不据此计算通信成本。

同主机CPU时间直接对齐，GPU事件仅做同stream相对时间，不映射为全局GPU时间。按每请求单调状态边界划分可证实的非重叠主机墙钟区间；相互交叠的worker/API/队列范围另列，不硬凑E2E。原DecodingBegin/await生命周期不作为整段decode GPU时间。无法建立实际依赖链时，保留未解释余量，不宣称得到off逐阶段关键路径。

## 4. G3正确性与观察开销预检

先完成环境加载、P2P/IPC、embedding/KV一致性；冷启与完全停止后重启，各系统/模式各运行固定单图、多图、不同图并发C8与8图正确性。精确token输出差异按原容许边界逐条保留，输入/rid/路由错误为硬失败。新8图至少检查输入视觉token数、无重复首图及输出32/128长度。

G2前固定正确性预算：每个端点每模式每次冷启/重启17个目标案例（标准7例：4单色、4色多图、COCO1/4；C8单色路由8例；8图COCO的32/128输出各1例），共4端点×2模式×2启动×17=272目标；新主机off基线预先生成17个reference，总289生成请求。所有输入IDs、长度、HTTP、图片SHA/预载/路由必须通过；4单色及C8四种路由输出严格正确且相互可区分，多图模型本身不能回答时按旧规则只允许目标与该reference精确token一致，并明确语义覆盖不足；自然图输出差异逐条保留，不能声称逐token一致或全量语义正确。每项验收独立标注，未获可信多图/8图机制证据不得进入对应正式点。无额外无限“试到通过”；修复后若需重跑正确性须G2记录，最多完整重检一轮289请求。CUDA/IPC/BLAS探针为独立数值校验，不计生成请求。

G3可观测性先用少量固定请求验证每个batch/op-ID、迁移依赖、请求输出和buffer覆盖；不得以模型启动替代机制证据。

观察开销正式预检只用1图/C1/128与4图/C8/128，两系统off/lite各6独立时间区组，每次20预热+100正式：4800正式+960预热。每区组4种系统/模式组合各一次，系统先后及off/lite先后在6区组内分别平衡，完整顺序文件事前固定。初始化、清理/重启规则各模式相同。

比较同系统同负载内lite/off的逐区组对数比：吞吐、TTFT P50、TPOT P50分别采用几何均值比及双侧90% Student-t区间（df5），对应预设等效性判断；六对数据不足以确认等效时保留“不确定”。接受界限候选吞吐[0.98,1.02]、两延迟[0.97,1.03]；所有对应区间完整落入界限且无正确性/覆盖问题，才允许将该负载lite阶段观测作为辅助解释。该预算判据须G1冻结，不能事后改宽。

不通过时最多一次与明确开销来源有关的最小修复，经G2后完整复检一次；两轮分别保留。不能只重复不利点或采到通过。仍不通过则lite只诊断，C只做off性能，不称关键路径/因果瓶颈已解释。

## 5. C性能干预与统计

五点A=1/128/C1，B=4/128/C8，C=1/128/C8，D=8/128/C8，E=8/32/C8。采用6个共同时间区组，每个全局区组内五负载各运行一对EPD/三副本。五负载先后使用seed20261026生成的随机化Latin顺序：前5区组使各负载在每个位置恰出现一次，第6区组为另一个事前随机排列；完整序列在看新结果前保存并绑定SHA。同一负载跨6区组恰3次EPD先、3次baseline先；每次20预热+100正式，总6000正式+1200预热。C新增负载没有验证lite等效性，故本批C只检验相对性能随负载变化，不承诺解释这些新点内部瓶颈。可观测辅助样本若需要额外GPU运行，不含于C预算，须在本批G1明确预算后才运行；不默认增加新lite全矩阵。

主估计量：各负载六对吞吐比的几何均值，区组对数比95% Student-t区间df5，保留全部逐区组比值/顺序/开始结束时间。TTFT/TPOT/E2E P50/P95保留每运行与合并描述值，不把请求当独立重复；输出tokens/s、实际tokens、失败率、输入IDs、全部自有进程显存采样及外来进程监测一并交付。6区组区间可能宽，不以“显著”作为必须成功条件；P99仅探索性，标明样本量。

预设干预对比：D相对C（同输出/并发增图），E相对D（同图/并发缩短输出），B作为4图中间点，A为无请求间流水锚点。同一全局区组内D/C与E/D的差异对数比另报95%区间，不把不同时间连续批次的block编号视为配对；属于探索机制线索，不忽略多重比较，也不要求单调或预设正收益。

增图同时改变视觉token/prefill/KV/batch，缩短输出改变驻留；结论只归因到已随机平衡的工作负载干预，不宣称单独E/P内部阶段因果。旧三重复数据不混合计算新CI。没有IRP、角色切换、容量扫OOM、DistServe或完整SIS扩展。

## 6. 顺序、冻结与停止

所有顺序、120请求清单、脚本/模型/package SHA、stat estimator及时间预算写入新配置manifest，G1/G2/G3证据以其SHA绑定。host boot、UUID、输入或模型变化即暂停该批，不继承旧批准。批准文件不从旧目录拷贝。

G1审此设计后再冻结真正可执行配置；有影响公平比较的必要变动需复审并依据用户已给授权确认范围。G2后才部署执行代码；GPU探针/正确性只在对应预检范围通过后启动，G3后才开观察扰动样本；C正式需B结果G4/对应G1确认分支。新增结果各自G4/G5，原归档和原Release始终不变。


## 2026-10-26 实际失败后冻结C-off分支

完整289模型案例正确，但EPD lite CUDA窗口cold/restart实际均0，完整observer G3失败；B正式未运行，不能称开销等效。G1失败分支及独立G4均APPROVE_WITH_NITS/BLOCKING0（reviews/g1-C-off-fallback-subagent.md、g4-C-off-fallback-subagent.md），采用原设计失败fallback，跳过B，保持C全部60 off cell/6000正式+1200预热与冻结顺序/请求/推理，不调剂B预算、不新增GPU正确性请求。
模型/off分项G3通过，lite继续REQUEST_CHANGES。consumer52清单9bb1a92b9864bb9ccd837a9258d7079f0dc98d559ab305c906d4bed6d27d4bbd仅runner gate/窗外snapshot及CPU回归变化，G2及G3delta通过，目标24CPU+真实ALARM1通过。明确C_SCOPE_APPROVED范围，不伪造B_RESULT_ACCEPTED。
共享主机限制：每cell计时窗前后统一采集全机GPU/compute PID/load/meminfo（含available/swap），不增加连续全机监控；所选三卡连续外来PID停止保留。继承affinity/NUMA记录不证明无竞争或实际内存放置。报告只能说本共享主机相对观测，不能称纯observer成本/内部阶段关键路径/因果瓶颈。
实际boot838160b3-4eb7-4a24-accc-f7720e0ac78a、物理4/5/6同NUMA1；预约系统fresh本人GPU lane21:00–次日09:00，08:58受控清理。原0/1任务已退出，不据此假定全夜独占。
