# CPU Ray生命周期实际失败：独立G3诊断与最小恢复G1建议

reviewed_at_utc: 2026-10-30T01:03:40Z

reviewer: 独立 Codex subagent `/root/fallback_g3`，按 AGENTS.md 3.2.1 接替；本人未执行该run或清理操作。

**实际CPU生命周期G3：REQUEST_CHANGES / BLOCKING 2（首场景连接失败；该capture尚未证明释放）。失败证据与地址诊断成立，但该批不能标PASS、不能复用为生命周期G3。最小修复G1：APPROVE_WITH_NITS / BLOCKING 0，仅允许下面CPU路径的本地窄修改与反例准备；不授清理、重新启动、部署或GPU执行。**

## 实际原件与失败边界

run_id `cpu-life-20261030-80d6425a5687c2379dbff33ceccd4027e4cae3a1c4d467869db6e26f5ba79621`，实际source529d；目录 `/local/boyjiang/epd/runs/cpu-lifecycle-20261030`，private session `session_2026-10-30_08-49-28_164035_500374`，port49173。

本审重新计算并解析 `numeric-cpu-lifecycle-failure-capture/raw.tar.gz`：2611809B/SHA `ecbda901809e1613f0a893427b4279741d088bc06bfda67fefe9bf77439fb88f`，解压tar66078720B，8份actual run files加1生成inventory；8份大小/SHA与capture清单全相等，未发现重复成员。lifecycle.jsonl为66053977B/SHA `05888ed58bef4a070010d897b5eebff435def19bc4aec43dcf9a07070a4d2f85`，本次独立解析事件计数及6项原登记身份，与analysis.json完全一致；analysis SHA `0a61978766522bab9432f598e2d83d27de3f7d54ef17fc371c1572ea76118baf`。不是仅信主导摘要。

实际外层exit1，terminal原SHA `343598c91ae95a8d33ed6d707b57f6a39e9345d4e06b4d3c98d94c370aa638e9`，error为FAILED_RELEASE_UNCONFIRMED CPU creation/scenario pending。父journal的首次spawn意图monotonic256523.008247925，首场景Timeout256553.054183341，间隔30.045935416秒；随后记录cleanup_unconfirmed，未进入其余三个场景。

事件计数：CPU_preimport1、head_process_registered4、head_descendant_registered2、head_children_observed2746、head_descendant_verified914、CPU_driver_spawn_intent1、CPU_diagnostic_failed1、CPU_cleanup_unconfirmed1。没有本批CPU_actor_submission_observed、constructor绑定或scenario terminal事件。driver journal只有preimport_verified1，**没有before_actor_create、actor_submitted或ActorID回执**。这说明capture中的业务actor创建阶段尚未到达，不能把“没回执”单独外推为未来永无迟到创建/完整GCS quiescence。

原6项登记PID/start/ppid均UID2147/boot65f/root/run一致：

|角色|PID|start ticks|原ppid|
|---|---:|---:|---:|
|GCS|500416|25652019|500374|
|minimal dashboard head|500697|25652121|500374|
|raylet|501249|25652256|500374|
|dashboard agent|501307|25652259|501249|
|runtime-env agent|501309|25652259|501249|
|driver|501363|25652301|500374|

这些是原始归属，不是当前仍存活或可按数值PID清理的许可。capture的scope明确driver/daemon可能仍活、release未确认；本审没有访问服务器确认之后状态。

## 地址机制诊断

1. 实际 `0/spec.json` 指定 `127.0.0.1:49173`；原登记GCS argv有 `--node-ip-address=127.0.0.1`，raylet和head agents亦advertise127.0.0.1。driver真实 `0/stderr.log` SHA `e54fe8145f6e3764d7b952e8849df7f71334183cf6473a8039c2cd0203fbe1b0`，首行明确worker.py1567正在连接 **172.31.35.35:49173**，后续Node._init_gcs_client失败→ConnectionError，栈在numeric_cpu_driver.py103的ray.init。这个文件是tar里的driver stderr；capture目录自身stderr.log为空，不能把两者混淆。
2. 已重新核本地官方Ray2.10 source raw SHA：worker `5e6a29a4f1c17f02c346eed207e5389dbb77b27cf3398fa373ea769ff5895263`、services `385604d4ecda5febb280435e1129512c5802c3d520581b6a7470ceeef4c8c60f`、node `923e30633a4d2ea2ccfbe67b5c6211bbcb670738abb866825cbc318398c95b24`，与原pins相同。
3. worker1564在连接前调用canonicalize_bootstrap_address；services517–539委托resolve_ip_for_localhost，599–619仅在host字面为127.0.0.1或localhost时调用get_node_ip_address并换成可远程到达的IP。其官方控制流与本次物理IP日志一致，构成地址偏离的明确源码解释。原生 `_node_ip_address` 在worker1397提取，1696–1698传入连接用RayParams；**它不会跳过1564对bootstrap address的转换**。
4. 因而只在driver补 `_node_ip_address='127.0.0.1'`、仍传address127.0.0.1，不足以修复此bootstrap改写；增加等待/业务重试、取消atexit或patch Ray安装文件都不针对这个已见原因。当前证据支持地址不一致为直接待修机制，不声称已排除所有潜在GCS连接/环境问题或新地址必然成功。

## 最小本地修复G1：认可固定CPU loopback127.0.0.2

**批准本地设计/实现/有意义CPU反例准备，真实执行另审：**

- CPU head的node_ip_address、raylet_ip_address、expected Node.address、父scenario bootstrap、CPU GCS reader严格endpoint、CPU driver spec与实际ray.init统一为固定 **127.0.0.2**；driver显式传原生 `_node_ip_address='127.0.0.2'`。该canonical IPv4字面不匹配官方127.0.0.1/localhost特殊分支，原生函数保持它本身；Node connect-only使用同一显式node/raylet地址，避免后续lookup又选物理IP。
- **仅CPU分支变更。** numeric_head是CPU/GPU共用helper，不能全局替换其地址并顺带改变gpu_count=3的GPUbackend。可在已冻结gpu_count=0路径选择0.2，gpu_count=3维持原值；construct_node应从经过精确参数核验的选定node地址核expected address。CPU driver/GCS/父入口同步精确限制，不放宽为任意host、整个127/8或auto发现，也不使用物理IP接别的head。
- 不改Ray安装源码、site/环境/系统路由/驱动、不注销或monkeypatch官方atexit；driver继续连接既有head、不得拥有Node进程。不引入另一个inspector driver、通用ray.kill或额外服务。本原生地址参数修复比更换Ray内部连接入口/修改全局canonicalizer更小，当前没有必要改更底层API。
- 保留四场景、15秒构造窗口、30秒单场景、180+120总界、0 GPU/actor num_gpus=0、所有pins/身份/WAL/pending/原子回执/真实signal outcome/退出后新GCS/双读活PID/迟到进程拒绝。不得借修连接缩验证、放宽UNKNOWN或把旧结果改为PASS。
- fixtures至少覆盖官方正常化分支的127.0.0.1→指定物理IP反例、127.0.0.2原样保留；driver mock核address和_node_ip_address同值；CPU Node/GCS/父spec一致及foreign/旧endpoint拒绝；gpu_count=3参数/原行为不变。用已pin官方源码语义或受控fixture，不为测试导入真实Ray/访问网络。新source/test精确G2、分支G5/部署闭包与新具体CPU execution G2均要重新取得。

这只是固定单机CPU连接身份的候选修复，不能据此称整个Ray所有listener只绑定loopback、网络隔离或运行成功；实际新单元仍需核真实Node/driver地址与进程原件。

## 失败收口与再入场条件（不由本报告执行批准）

1. 先按**另审的**cleanup operator核driver原identity/稳定pidfd并停止或确认原PID已真实absent，保留实际outcome；若PID复用/UNKNOWN拒绝信号。不能以traceback出现就代替已退出，亦不能仅凭本次capture旧absence推断现状。
2. 在driver已终态后重新封存/核driver journal、submission/constructor/ready路径与事件，确认未到before_actor_create/ActorID阶段；已审driver代码在业务创建前fsync WAL，这条事实结合已终止driver才支持本次无业务创建的收口判断。若出现晚的before_actor_create、ActorID或unknown，原样保留pending，停止套用“零创建”简化。
3. 仅对原6登记身份及已另审的原始归属链进行身份复核后的pidfd收口，不按UID、名字、端口或进程组清理，不认领未知晚生PID。收口后记录本run范围的实际absence/迟到扫描及真实终态；不能把旧known列表空/原6离开等同于全host quiescent。清理通过前不重启新head。
4. 原run目录、config/spec、66053977B日志、失败G3和所有审批保留。新修复发布/部署后须新唯一run/root/session/namespace、freshCPU票/现场、完整预算及单次新执行G2；不能复用旧CPU lifecycle G3或简单改地址后重发旧run。新实际四场景结果再独立G3，GPU/native36/模型仍未获许可。

## BLOCKING（对本实际批次及直接重启）

- **F1：首场景没有完成连接/actor生命周期取证。** 实际exit1、30秒超时与driver ConnectionError；四场景完成数0。需新源码/Gates与新run真实验证，不能用源码或166本地fixtures补成该批PASS。
- **F2：原capture释放未确认。** pending保留、head清理跳过，原登记6身份不能仅凭旧记录当已释放；需另审cleanup的真实闭环及独立结果核验后才允许再入场。本审不知道之后是否已完成收口，不会把capture时状态泛称当前状态。

## NON-BLOCKING

官方地址改写是明确可修机制，但真实Ray.init的内部等待超过父单场景30秒，说明父失败后driver仍可能继续初始化，必须按上述先止driver再核WAL顺序。未来具体执行监督与清理合同应继续保存实际超时/残留，不因为新0.2连接预计正确就忽略失败路径。66MB原journal说明实际采集量，不是性能数据或新增GPU探针理由；本次不为日志重构扩大修复scope。

## QUESTIONS

无须修改用户实验设定或再次询问已确认CPU意图。可以并行准备上述本地窄修；清理、新部署与新CPU运行各按真实Gates处理，本报告不授权它们。

本审只用本地Node文件API解析gzip/tar、读取源/日志并计算SHA/事件计数；未运行项目/测试/shell命令、Ray、信号、网络、SSH、GPU或修改源码，仅新增本诊断MD/JSON。

GATE_RESULT: {"gate":"G3-numeric-cpu-lifecycle-failure","passed":false,"decision":"REQUEST_CHANGES","blocking":2,"failure_evidence_accepted":true,"actual_run_exit_code":1,"completed_scenarios":0,"release_confirmed_by_capture":false,"G1_minimal_CPU_repair_decision":"APPROVE_WITH_NITS","G1_minimal_CPU_repair_blocking":0,"local_repair_implementation_approved":true,"cleanup_execution_approved":false,"new_CPU_execution_approved":false,"GPU_approved":false,"native36_executable":false}
