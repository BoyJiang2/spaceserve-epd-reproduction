# EPD公平PD后续v8：候选资格→校准→选中配置完整G3，尚无GPU许可

成功标准：同一新主机/三张同型GPU/同模型MiniCPM-V-2_6 FP16 TP1，完成三完整副本、合理校准PD消融、EPD三组；实际数值/冷启/重启/多图并发正确性G3，原始数据及G4/G5，独立epd/comparison及GitHub项目页远端核验。未完成公平三组，不声称E分离优势。旧53/60已失败收口；不恢复、不修改旧数据/封包/Release。

## 顺序与硬边界

Space先完成或明确受阻收口并确认本人进程释放。当前qjh000仅Space GPU4，13–17及17–19本人票不扩展EPD卡数；用户授权止18:00，17:58清理。qjh001只读候选，四系统控制域尚未交接；不访问其GPU或借账号票取得控制权。新三卡预约、明确GPU UUID/控制责任/时段及用户预算批准、完整独立G1、实际代码G2、新鲜资源证据齐备后才部署/运行。当前仅本地文件与CPU测试，不远端编译/搬运/负载，不干扰Space。

## 实现与来源

新目录work/epd-pd-followup-20261027/v8，以固定上游9b111f710dfb4724072b603d626a1e4dad93ef1f的受控拷贝为底，应用现有epd-h20-cache-fixed.patch（包含epd-complete.patch的图片、IRP、输出ID修正及RGB缓存入口）。观测off；patch-check累计观测源码只作差异核对来源，不直接复制其observe依赖。rgb_cache.py复用既有reproduction版本。新补丁/源SHA单独保存。

--pd-fused仅接受E0/P1/D2或E0/P2/D1，TP1/PP1、FP16 MiniCPM；同P Worker一次RPC执行真实视觉编码和prefill，局部vision tensor直接注入现有LLM路径，不创建E actor、不做E→P embedding IPC、不持久化vision cache。P1/P2由输入token积压分发；P→D继续共享队列、来源DP rank及原KV迁移。源KV只在所有迁移RPC实际成功后释放；异常不得生成迁移成功记录。没有部署DistServe，仅称PD消融。

这也是固定三卡下不同P/D容量及系统策略的比较，不是纯E阶段因果实验。P侧视觉/文本同actor可能串行执行；这是融合机制，不能用额外同卡actor人为增加开销。实际内存、各角色权重/缓存驻留、吞吐瓶颈、实际忙碌卡数需G3/G4报告。

## 第一阶段候选：数值→8候选资格→独立校准→3选中配置完整G3

4拓扑：三完整副本(3GPU)、PD P1:D2、PD P2:D1、EPD E1:P1:D1。每次独占相同3UUID，同一模型/环境/数据/缓存/eager/采样，完整停止释放再切换。

|阶段|硬上限|wallclock准入预算|
|---|---|---|
|本地CPU|无模型请求、无GPU|不占预约|
|数值|0模型请求；三次×六有向GPU对×KV及vision两种载荷=36传输；实际缓存边界/分块/校验|30分钟|
|候选资格检查|8个精确候选×15请求=120，限同profile自身有效|40分钟|
|最终完整正确性G3|选中3个精确配置×冷启/重启2×图数3(1/4/8)×长度2(32/128)×(C1的2请求+C8的8请求)=360|80分钟|
|独立校准|8候选×3校准负载×2重复×(4warm+16measure)=960，其中192warm/768measure|180分钟|
|受控清理和确认释放|0请求|10分钟|

第一阶段模型请求上限1440=120候选资格+960校准+360选中配置完整G3（正确性合计仍480），预约至少340分钟；这不是预测完成时长，任何子阶段wallclock耗尽即停止并保全未完成证据。启动/加载/卸载均计各阶段预算，不能借超时追加。完整G3每case请求数=max(2,并发)，C1为2、C8为8；每个最终选中配置120请求（60冷/60重启）。表格按成本分类，不是执行顺序；执行顺序严格为数值→全部候选资格→独立校准→最终3配置完整G3→独立实际G3审查→另批正式准入。预算入口以budget-v8.json为准。

每case须真实达到相应并发，保存请求唯一RID、image路径/顺序/RGB hash、processed IDs、视觉token数、输出token IDs/长度、时间戳、设备放置/实际角色actor数、内存。三副本必须覆盖全部3端点；冷启及完整进程重启后均通过。CPU fake测试不替代数值/模型G3。非零失败/ID或数据不一致即停止该拓扑，不将exit0作为通过。

校准候选：三副本2 profile、PD每分配2 profile、EPD2 profile，共8。profile S/L分别max_num_seqs/阶段batch=4/8；max_model_len与tokens per batch固定4096，decoder cap与profile一致；EPD encoder cap同profile，PD视觉与P同batch。所有组同gpu_memory_utilization=0.65、prefix/MM特征缓存关闭、RGB统一预加载、输入ID策略相同，输出greedy/ignore_eos且实际长度一致。先用源/API支持性CPU检查锁定参数名；baseline当前limit_mm_per_prompt=4须修至8且审查，不能默默用4图限制跑8图。

校准专用数据与正式ID不重叠，预先写入manifest和SHA；3校准负载为1图/128/C8、8图/128/C8、8图/32/C8。两个重复配置顺序相反；每个请求、超时、OOM、启动失败与未执行都记录。全负载选择一个profile/PD分配，不按正式点择优。先排除任何错误/输出长度或该精确profile资格检查不合格/超过显存上限候选；余下按唯一冻结公式S_c=[∏_{l∈{C,D,E}}((r_{c,l,0}+r_{c,l,1})/2)]^(1/3)最高选择，即每负载先对两重复取算术均值，再跨3负载取几何平均；不是先求每重复的3负载几何均值再取重复均值。3%平手严格定义best_score/score_c<=1.03，在该集合中优先较小profile，PD分配仍平手按P1:D2（预先固定）；任何负载失败使该候选不合格，不丢失败cell重算。资格检查只允许该candidate参加校准，不等于完整模型G3，不允许同拓扑S/L相互覆盖。selector输出始终formal_admission=blocked_pending_selected_config_full_G3；选中后须对三个精确配置分别做完整G3并独立审查。任何选中配置完整G3失败立即收口，不自动选择runner-up重试；再次选择/验证需新计划/预算/G2或G3审查。三副本与EPD也按同规则选S/L。profile定义及同预算合理性待G1审查，不把默认弱版本直接当结论。

失败重试：数值、正确性、校准各cell最多一次实际尝试，零自动重试。修复后另需版本/G2/预算差异与重新批准的新增尝试；既有失败不覆盖。无可行PD则结论为PD基线受阻，不进入正式性能比较，不降级两卡PD或虚称强基线。


### 候选资格与实际证据绑定（v2修复B1）

8候选分别为replicas/EPD各S,L和PD两分配各S,L。每个候选精确15请求：1图/32/C1×1、4图/128/C1×1、8图/128/C1×1、8图/32/C8×8、4图/128/C4×4。并发按实际提交/完成区间峰值核对，不能只写concurrency=8。资格阶段允许只冷启，不冒称覆盖重启/完整矩阵。三副本的并发请求须实际覆盖全部3端点并记录；输入集固定，与正式/校准独立，所有candidate同一顺序与图像。原生三副本S的这些15实际输出作为共同参考记录，不追加reference生成请求；S/L参考不一致则资格失败并保全，不能复用其他profile的批准。

每candidate资格receipt需绑定candidate ID、candidate_arguments canonical JSON SHA256（包括S/L及P/D分配）、source_manifest SHA、runtime_binding SHA（主机3UUID、模型/processor/tokenizer/权重、环境、数据/RGB与公共输入SHA），以及原始15请求JSONL文件及SHA。原件含唯一RID/fixture ID/case、实际prompt、按顺序的图像路径及RGB SHA、processed IDs/输出token IDs、图数与submit/end时钟。共同15请求input manifest和原生三副本S的15实际请求reference JSONL独立pin SHA；资格consumer逐值比较实际prompt/图顺序/RGB及processed/output token IDs，不信任reference_match=true布尔。reference使用已计入120资格预算的原生三副本S原始请求，不新增模型调用。reference SHA在其实际生成后、任何其他候选资格认可/校准择优前由独立证据核验冻结，不能修改参考来适配其他profile。selector读取并逐SHA校验原件、精确请求数/各case/实际并发/成功及输出长度；8份资格receipt全部明确passed/failed/not_run，不能静默省略失败候选。

校准48cell都绑定上述精确资格receipt SHA及candidate/source/runtime SHA；裸correctness_passed=true不能代替证据，错profile/旧source/错runtime/缺receipt/篡改log均拒绝。selected结果只产生3份待验证完整G3配置，不产生运行许可。最终3份完整G3需独立receipt绑定selection artifact SHA、精确candidate/config/source/runtime、全部120实际请求及冷启/重启session身份；独立审查通过后formal consumer才能放行。此consumer/实际G3验证器尚未实现，须另G2；不能用selector的候选JSON直接启动正式。

v1/v2/v3/v4计划/预算/源码manifest/补丁/CPU证据保持原字节。审查来源见reviews/g1-v1-relayed-profile-plan-review.md及reviews/g1-g2-v2-relayed-independent-review.md及reviews/g1-g2-v3-relayed-independent-review.md。G1v3独立APPROVE0、两个nit已关闭；G2v3 REQUEST_CHANGES/BLOCKING1（summary rate未绑定raw外层窗口）；v4本地实现与CPU验证后由主线程安排独立G2重审，不是实现者自审。


### 校准实际显存准入（v3修复G2 B1）

所有successful校准cell必须有memory receipt，禁止只填summary peak/boolean。runtime binding原件pin主机/boot/UID及同三GPU UUID的物理capacity_bytes、fresh部署前gpu_admission_free_bytes、gpu_memory_cap_bytes；每卡cap=min(floor(0.65*physical_capacity_bytes),fresh_admission_free_bytes)，不能把.65配置值当实际显存证明，也不能把三卡容量求和掩盖单卡超限。每候选加载前仍须fresh资源守卫证明可用预算及归属，runtime manifest不能代替新鲜API/主机证据。上限包括device_used_bytes（含CUDA/驱动驻留），不是仅torch allocated；任何外来进程不终止、不忽略，直接拒绝该cell。

每cell receipt绑candidate/repeat/load/config/source/runtime SHA、host/boot/UID/runID、完整warmup起至measure末区间；原始20请求JSONL与实际client-window.json均独立SHA绑定。4warm+16measure且唯一RID，真实submit/end、先warm后measure；client外层warmup_start/end及measurement_start/end由benchmark直接记录，consumer核每个请求位于对应外层窗口。显存覆盖外层warmup_start至measurement_end，不允许summary截去峰值，也不以min-submit/max-response span替换外层窗口。实际样本JSONL及process registry原件均SHA绑定：registry逐GPU记录本run PID/UID/runID及proc_start_ticks；每个sample包含GPU UUID、unit=bytes、整数capacity/device-used/process-used字节、monotonic时间及全部可见compute PID身份。foreign UID/runID/PID、PID复用、错误UUID/capacity、缺归属、负数/浮点/bool bytes、单位MiB等全部拒绝。每卡device_used及进程总和均不能超cap，device_used不得小于进程总和。

采样目标100ms，最大相邻样本间隔1.0s；三个GPU都须从不晚于实际warm起点到不早于measure终点完整覆盖，不能缺GPU/缺interval，样本最多在边界各延伸1s。逐样本检查上限并复算采样峰值，缺receipt/raw、SHA错、采样间断或raw请求区间不符均拒绝，不回退summary或仅report-only。successful row与raw超限/归属等证据矛盾时整份selection拒绝；真实失败候选保留raw并如实标failed/not_run，排除整个候选，不丢cell重算。该指标明确是实际采样峰值，不能声称捕捉两次采样之间的连续绝对最大值；NVML/归属采集器及资源guard仍需另G2/真实G3，CPU fake样本不作真实采集证据。

### 评分非恒定重复校验（v3修复G2 B3）

预先固定上述“load内两重复算术均值→跨load几何均值”，G1/G2/selector/report必须同一公式。检验例：重复0=[100,1,1]，重复1=[1,100,1]，得(50.5*50.5*1)^(1/3)≈13.66，因此胜过恒定10候选；被排除的另一公式得到100^(1/3)≈4.64会翻转排名。本例只属CPU测试，未采集校准性能，也未依据真实数据择优公式。


### v4评分证据：实际client外层窗口，而不是summary或min-submit

每successful校准cell额外提交SHA绑定client-window.json（schema=calibration-client-window-v1、scope=calibration_client_window、clock=time.perf_counter），含candidate/repeat/load/runID/UID/host/boot、config/source/runtime SHA、requests_sha256、warmup_requests=4、measured_requests=16，以及warmup_start_monotonic/warmup_end_monotonic/measurement_start_monotonic/measurement_end_monotonic。这些是实际压测client同一进程的time.perf_counter域，与20条原始client提交/结束时钟相同，不能用服务器域、不同主机/boot或墙钟代替。

benchmark.py在warmup gather前后取warm_start/end；warm成功后，在创建/提交16个measurement协程的gather之前立即取measure_start，在await gather全部返回后立即取measure_end。duration=measure_end-measure_start，包括客户端任务创建/排队/请求完成后的gather drain开销，沿用原benchmark外层批次窗口定义。客户端写完并flush20条requests.jsonl后以其实际字节SHA写client-window.json，不从summary反向生成header。calibration模式必须--calibration-metadata绑定candidate/source/config/runtime及实际UID/hostname/Linux boot，且4warm+16measure×1内部重复；全局两重复是两个独立cell，不增加请求。

consumer要求4warm/16measure每条成功且唯一ID，warm请求都在warm外层窗口，measure请求都在measure外层窗口，warm_end<=measure_start<measure_end。逐SHA核raw、header及receipt并复算r=16/(measure_end-measure_start)，评分只使用该重算值；summary.requests_per_s必须在rel_tol=1e-9/abs_tol=1e-12内相等，缺失、非finite、只改summary rate巨大finite都拒绝整份selection。不能默默采用min(submit)/max(response)跨度，该跨度通常较短且不含完整外层开销；CPU反例明确二者产生不同rate并拒绝用内层span冒充。

非恒定重复与3%边界CPU例同时生成对应原始窗口/20条实际计时fake及采样原件；只改summary而不改raw/header不能翻转winner。该CPU测试不冒充真实校准数据；实际NVML/归属collector、资源guard、最终G3 consumer/Git-first部署与用户三卡预算批准仍待完成，不授予GPU启动许可。

## 后续正式候选（不属于第一阶段GPU预算）

较小首阶段正式：3负载C=1/128/C8、D=8/128/C8、E=8/32/C8，3组×3负载×6全局区组=54cell，每cell20warm+50formal，1080warm+2700formal。6区组依次采用三组全排列，保证每组每位置出现两次、先后平衡；全局负载顺序按CDE/DEC/ECD/CED/EDC/DCE。每区组必须三组同硬件同输入完成，否则该区组标不完整，不能只取已跑系统比较。

扩展正式：A=1/128/C1、B=4/128/C8加C/D/E，3×5×6=90cell、20warm+100formal，1800warm+9000formal。这是另批候选，首阶段50条不能偷偷扩写100条；禁止用正式数据重新选择PD。二者独立报告，不拼成原90cell。

每正式cell上限900s（含warm/formal），每系统切换最多10分钟，每区组1次三组启动切换、10分钟清理：小正式每区组9cell需175分钟，6区组合计1050分钟；扩展每区组15cell需265分钟，6区组1590分钟。每cell硬超时即失败、区组保留不完整，不压缩warm、验证、截止保护。预约优先按完整区组划窗；跨窗口须相同3UUID/模型SHA/配置与缓存协议，新鲜身份/预约核验，硬截止前120秒清理。G1可据真实校准耗时调整下一批上限，但须看正式数据前冻结，不在窗口内临时缩水。

## 统计、审查与交付

本地是唯一开发源：本地修改→本地CPU测试→独立审查→主线程commit/push GitHub→服务器只部署指定commit并逐文件SHA核验→冻结后运行。环境/权重/缓存独立于源码。服务器临时改动须回收为补丁并形成新版本/重审，不能边运行边修改；旧批actualSHA证据不追溯改写。本subagent不自行commit/push或部署。

主要配对EPD/PD、PD/三副本、EPD/三副本；每cell报告req/s、实际输出tokens/s、TTFT/TPOT/E2E P50/P95、失败率/实际输出长度/显存。统计主要终点为req/s，tokens/s与时延为辅助描述，不另作显著性筛选。

事前统计冻结：仅完整的6个全局区组作为独立单位，同一重采样索引必须同时抽取所有系统/负载，不能分别抽系统或把请求当重复。每负载/对比令d_b=log(req/s_system1)-log(req/s_system2)，点估计exp(mean(d_b))。95%区间采用配对区组非参数bootstrap：n=6、有放回抽6个区组、重复100000次、Python random.Random(20261027)、按bootstrap mean log ratio的2.5%/97.5%线性插值分位数取exp。不做BCa/正态近似，不把探索区间当同时置信区间；六区组样本小须显示全部区组原值。任一相关正式cell失败或区组未齐则只报告失败/缺失和已得原值，不补样、不缩样、不生成该确认性统计。

Holm的原始p值采用两侧精确配对区组符号翻转检验：枚举2^6=64种d_b符号，统计量abs(mean(d_b))，p=满足T_perm>=T_observed的符号数/64（浮点容差1e-12），不使用bootstrap尾概率作p值。小正式3负载×3对比=9项为一个预先固定family，扩展5×3=15项另一个family，分别Holm step-down FWER .05：升序p_(i)对比.05/(m-i+1)，首次不拒绝后全部不拒绝；调整p为min(1,max_{j<=i}((m-j+1)*p_(j)))。该两侧精确检验最小p=2/64=.03125，在9或15项Holm family下连第一项阈值也无法达到，因此本六区组设计不可能产生Holm校正后的拒绝，须明确报告这一分辨率限制，不能以“趋势显著”替代；所有效应量、退化及未拒绝均完整报告。符号翻转依赖配对差异的对称/交换性假设，系统平衡顺序本身不证明该假设，结论限定为探索性证据。跨视觉/输出长度仅同全局区组配对并描述，不新增事后显著性family或单因素纯因果结论。

独立G1冻结实施语义/候选/数据manifest/所有预算及资源；G2核源码补丁、baseline8图及参数、压测/守卫/CPU测试；实际数值及模型G3；正式数据G4；可复跑EPD入口、epd/comparison、局限及GitHub远端验收G5。新源码目前只是CPU候选，尚无G2与真实G3，不是已完成公平PD或可直接部署的正式包。


## v5第一实现单元：尚无执行入口与新GPU许可

v4本地代码候选已独立instrument_review G2 APPROVE/BLOCKING0，原文转交保存在reviews/g2-v4-approved-relayed-instrument-review.md；不包含部署/运行授权。v5新增preflight_guard.py、live_evidence.py、selected_g3.py、candidate-only静态配置及CPU mocks，接口/白名单/失败保全和明确blocked项见源码PREFLIGHT.md。本实现者不审自身变更。

静态配置必须是同commit的preflight-static.json，精确host/UID/root/三UUID/NUMA/booking ID范围/phase预算及独立reviewer范围经真实user/G1/G2绑定后才能使用；本交付只有null scope、state=candidate_no_gpu_authorization的模板，不借旧Space/账号票。runtime只在ROOT/runtime白名单，原始receipt/版本/命令/API数据另SHA绑定；模型/环境/缓存与源码分开。指定commit推送原件、实际HEAD/逐文件deploySHA及fresh<=5min的原始booking/资源均须核验，锁不算预约。

预算按既定1440/36/340min/零重试精确分unit，非退款、重复unit拒绝，实际durable claim+ledger比对后才有逐request/transfer接口。采集器仅所选三卡NVML真实bytes和PID元数据，不读environ/凭据、不扫描全机、不kill；unknown归属failclosed，保留raw/失败hash。selected3 consumer只读完整cold/restart/request/reference/memory/window/deploy/source/book/claim/release proof及独立原文SHA，不签G3，始终formal blocked。

当前仍BLOCKED：controller未逐request/transfer接线、worker与baseline身份注册adapter未接、实际read-only admission probe/bootstrap未接、实际POSIX持久锁/fsync/超时取消/精确自有清理未测、NVML/NUMA/whole-window采样仅CPU mocks、真实三卡预算/预约/交接与用户许可不存在。不能靠reserved/passed布尔补缺，不把fake proof消费单测记成实际G3。Space收口/新三卡用户授权、完整独立审查及Git-first指定commit部署前不执行。


最新用户CPU落点要求：后续测试/编译/可迁移分析优先合法远程CPU host，local主要编辑/查看/审查。GPU票不自动授权CPU lane，先核CPU预约、项目归属及其他负载，独立审查→commit/push→指定commit专属部署后执行。已跑轻量v5 mocks13项如实保留，不再local重复suite/新重测试，不自行远程/读凭据/预约，不能用Windowsfake当Linux目标验证。此要求不增加GPU/请求/预约/预算。


## v6 G2修复与执行状态

v5独立G2 REQUEST_CHANGES/BLOCKING2，完整来源见reviews/g2-v5-relayed-independent-review.md。v6按source-feasibility-v6.md补实际endpoint/API-worker-PID-UUID及三副本60条20/20/20覆盖、持久claim双clock1600s、NaN/错anchor/跨系统overlap拒绝。benchmark记录真实dispatch-offset及response身份，不从expected metadata捏造；实际producer/薄controller仍blocked。

v6新增短cpu_target_runner.py及未执行回归：仅已审指定commit在qjh001独立CPU50、child AS1GiB、300+30s；原始CPU15–21票/18后四域释放/无接管与CPU50冲突/19前完整预算/G1/G2/sourceSHA必须齐备。保留AF_UNIX自有self-pipe，允许真实asyncio/受审git与own-Python，阻断GPU导入/TCPUDP/未知服务，不擅自远程或处理别域。当前没有实际handoff，runner没有执行，不把Windowsfake或v5旧13PASS写成v6/target结果。

下一driver只做固定单元前一次不可退款claim+精确argv/有限请求向量/sourceSHA，测量内unitID/raw journal，不做每请求重量检查；36数值transfer另阶段。预算1440/340min/零重试不改，formal另批未授权。


## v7最小runner修复（未执行）

统一父TERM/INT/正常退出/wait或log异常的有界finally；只核精确自有PID/UID/start/cwd，未知拒杀并保存真实终态；nice10设/验/记，保留preflight缓存commit、parent identity与实际argv。SIGKILL不可捕获，不宣称保证。新增真实POSIX信号/等待异常回归源码UNEXECUTED。详见source-feasibility-v7.md。CPU50用户确认pending、旧项目final_release缺失，不执行、不降门槛；v1–v6不改。


## v8最小竞态修复（UNEXECUTED）

启动/身份绑定阶段TERM/INT只暂存不抛，Popen对象及身份取得后进入既有统一停止/finally；对象缺失或空cleanup绝不推断released。新增fork后、wrapper返回前的确定性TERM/INT真实回归源码但不执行。只两source文件变动，v1–v7冻结，CPU交接pending，无新资源/预算或运行许可。
