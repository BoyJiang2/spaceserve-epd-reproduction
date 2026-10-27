# SpaceServe H20补充：事前方案 v1（G1候选）

## 成功标准与状态

EPD本批已获窄受阻收口G5（../revision-proposal/reviews/g5-C-terminal-blocked-closeout-subagent.md），完整C未完成，不再补七项。本阶段只继承用户授权的单H20/Qwen2-VL-7B三组补充目标，不继承EPD或历史Space的Gate。当前仅本地计划、预约/远端只读盘点；未部署、未启动Space GPU。

成功须同时具备：当前环境和源补丁SHA；实际设备放置、并发和encoder mask可撤销/重施的G3；固定六负载三组顺序平衡的完整逐请求对照；G4/G5、独立项目页和新资产远端核验。失败/不完整照实保留；mask未证实不标第三组有效，不将encoder-only称完整decoder互斥分区。

## 资源与隔离

新root `/var/tmp/boyjiang-spaceserve-revision-20261027`，旧root `/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023`及封存结果/ZIP保持不变。复制既有环境、Qwen模型、源码和构建物到新root（可使用本机reflink，禁止共享可写hardlink；拒绝越界链接；原地路径/二进制重定位须实际验证）。旧源只读，保存复制前后manifest。模型、环境和缓存不上传；记录各模型文件SHA和安装版本/实际加载库。

候选只用物理GPU4，UUID `GPU-79214c80-7778-37d9-282b-89228debbb69`，不自动追加卡。北京时间27日03:25盘点GPU4空闲、boot838160b3-4eb7-4a24-accc-f7720e0ac78a；GPU0/1有其他任务，原样保留，共享主机不能称独占。root盘918GiB可用，部署预算先算实际占用。复制/编译/分析在正式计时前完成，不在同机正式测量时运行本项目EPD/下载/编译/分析。

本人GPU lane/h20/qjh000实际预约bk-20261026T1355-92661e0f至27日09:00，北京时间08:58前受控释放；每阶段启动前用5分钟内API凭据重验owner/start/end，boot/UUID/空闲及自有进程。沿用08:30/08:58自动收尾。锁不能代替预约。预算不足就保存断点等有效窗口，不缩负载/预热/正确性，不自动预约或继续越窗。

三组均在该卡、同私有MPS（active thread100%，专属pipe/log），同FP16/TP1/eager/max_model_len4096/max_num_seqs8/max_num_batched_tokens4096/gpu_memory_utilization0.65、图数上限4、prefix缓存关闭及greedy/ignore_eos。原生vLLM同fork对应版本；native从已安装vLLM导入，解耦从固定66de079af423源码加累计必要补丁导入；每个实际进程保存import路径和库SHA。两组均不加载libsmctrl，mask组仅加载固定mysmctrl6ff57356968a3f04158b9273aa881ee6bdf04229构建库与官方encoder mask，未改decoder分区。

## 预检与机制预算

1. CPU部署逐文件SHA/路径、版本/源差异、无GPU导入检查，真实POSIX SIGTERM与短SIGALRM finally测试，身份不明只停止本项目控制器而不杀未知进程。新的G2绑定本阶段代码，历史marker不复制。
2. CUDA FP16小矩阵一次、实际私有MPS mask独立数值probe三轮（unmasked/masked/clear/reapply），保留SMID原值，不把SM数量当吞吐份额。实际服务stream探针同样记录mask前/后/清零/重施及首次encoder执行，确认一张卡的encoder/decoder参数设备、FP16和进程身份。可执行判据：同一进程/实际stream identity，masked集合为unmasked严格子集，clear集合等于unmasked，reapply集合等于masked，首次执行stream等于该stream且实际集合相符；仅数量变化不通过。不同GPU不沿用旧78→64数量。三组正式均关闭profiler和SM诊断kernel。
3. 正确性沿用已有7个Qwen语义/多图案例与8个C8异图路由：先native产生7个reference；每组三组各冷启/重启15目标=90，加7reference，总97生成请求。按新实现显式reference-only避免旧脚本同端点重复请求。自然图单图4类输出需可区分且关键词通过，多图reference语义失败仅允许逐token相同并明示限制；processed input IDs/实际输出长度/图SHA均核验。
4. 每组三组各冷启/重启，另独立诊断profiling固定4图/C8/128，20预热＋16采集，共216请求。只诊断并发/设备/实际stream，不计正式性能、不将profiler片段推断off关键路径。native预期1worker，解耦/mask预期encoder+decoder实际流；trace必须实际导出并独立审G3。合计模型预检313请求，另非模型数值探针；失败不无限补请求，修复后追加运行需先记录G2/G1具体预算。

## 正式矩阵与顺序

沿用六点：1图和4图 × C1/C4/C8，128输出tokens，原COCO20图/提示词/固定预处理（记录实际视觉token与RGB），相同请求序列：第i请求第j图为(i*images+j)%20。各cell20预热＋100正式，所有计时前RGB/模型/请求SHA冻结，禁重复图片特征缓存混杂；每cell前后核RGB摘要与配置。

总三时间区组×六负载×三组=54cell，5400正式＋1080预热，不增加卡数或第四重复。每cell新启服务、结束清理（对三组相同），正式无profiler/SM诊断kernel；每运行记录参数设备/MPS客户端、峰值显存、0.1s监测和计时窗外全机GPU/load/mem/swap快照。请求/身份/模型/图序变化、foreign compute、OOM、持续超时即停止保全，不择优删点或重试到好结果。

冻结seed20261027生成六负载在三个区组的先后排列；每个负载三次组顺序采用全局随机重命名的3×3 Latin方阵，三组各在第一/第二/第三位恰一次。跨六负载各三次正向/反向，且全矩阵每对先后9:9；负载内仍为2:1。正式冻结配置为configs/schedule-v2.json，SHA7248d8829180d3df25f04204cd7e1e89b7b7462ea5f39651986f118418c0d8d3；早期schedule.json未运行候选保留且禁止作为正式配置。全部54顺序在看数据前保存。三次对同负载的两两先后不可能精确各半，明确保留2:1不平衡/残余时间混杂，不把位置平衡说成完全carryover平衡。每cell服务重启减少持久状态混杂，不能消除主机时间变化。

## 统计与交付

主比较解耦/native、mask/native、mask/解耦，六负载全部展示。逐次req/s、tokens/s、TTFT/TPOT/E2E P50/P95、显存采样峰值及失败率保留；三次吞吐均值SD、配对几何比及95% t区间df2（假设对数差近似正态，三次很弱，宽区间允许）。同一区组配对，不能把100请求当独立重复。合并延迟仅描述，不对请求bootstrap冒充区组CI。三对六点探索比较不作多重检验后显著性宣称。

任何缺cell或机制未证实则输出完整计划清单/原始逐次数据及缺项，不生成完整三重复总体CI或完整矩阵加速结论，不用局部低高代替全矩阵。新批与旧4090/L20/H20分别列，保留退化。共享机快照不能排除瞬态干扰；未测SLO/极限容量标未测。

G1冻结后G2实现，再实际G3通过才正式；正式后实际G4和交付G5。更新GitHub spaceserve/独立comparison/、原始数据/代码/复跑入口；大trace新Release附真实URL/bytes/SHA，不改旧Release。EPD partial发布独立审查，与本阶段GPU测量不混。总目标在未交付前保持未完成。
