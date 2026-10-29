# G1 v2 — Native36 生产后端设计窄复审

- 审查者：`/root/epd_pd_followup`，独立只读设计复审。
- 审查 UTC：2026-10-29T07:01:46Z。
- 结论：**APPROVE / BLOCKING 0；原设计 B1 在本地完整实现范围内关闭。**
- 计划：`numeric-production-backend-plan-v2.md`，实核 SHA256 `5cc238a80c56f72ff649c3d0c56693eedb3156693f341a9a76b392c47f722d5b`。
- 许可边界：可推进完整 native36 后端、生产入口分派和针对性 CPU 注入测试的本地实现；本审没有运行任何测试/编译，没有 Ray/Torch/NVML/CUDA 初始化、网络、SSH、GPU或源码修改。不批准真实 CPU 部署、真实生命周期试验或 GPU 执行；本轮按计划不 commit/push。

## B1 闭合依据

v2 已选定非 `--block` 官方 CLI 私有 head，而非继续模糊指定 supervisor 包住任意 Ray 启动方式。已保存且上一轮逐字/实际 Git blob 核过的 ray2.10.0 CLI790–791把 shutdown_at_exit/spawn_reaper绑定block，970后整组kill循环只在block分支；既有address driver的connect_only分支和detached creator独立语义支持此选择。v2正确保留Raylet/GCS/OS故障例外，没有把detached解释成永不随基础设施退出。

独立supervisor在CLI/driver之前存在，daemon身份闭包确认后才创建actor；driver退出不触发通用后代全杀。copy之前先保存mapping_possible及双方真实身份，解决原driver在RPC中消失导致出口依赖丢失的问题。numeric独立最终清理明确排除HTTP cleanup_owned/head shutdown/kill_all_processes，不改变HTTP路径。

工作截止1680秒、总终态1800秒（含120收口）已明确；正常可控路径按 importer实际退出和NVML context消失→exporter→第三actor→daemon收口。未确认时有限结束、保存残留并报告 `FAILED_RELEASE_UNCONFIRMED`，不出PASS、不启下一单元、不续期。这正确区分程序终态与物理释放事实：D-state/驱动或基础设施失效不是无限retain许可，也不要求程序对不可恢复OS状态作绝对保证。

v2另设真实无CUDA Ray/POSIX生命周期Gate，明确它不是Worker/CUDA IPC数值通过；未通过时生产GPU入口保持failclosed。因而已形成可实施、可逐Gate验证的路径，无需改native IPC、载荷或增加预算。

## 后续 G2 必须核实的实现落点（非新增设计阻塞）

1. 固定CLI argv、私有temp/session、exact address/端口与daemon/actor归属证据；CLI正常退出后daemon重新挂父不能仅凭同UID/cwd/名字认领。方案应在实现里真实解决，G2核最少必要代码与尚需补证的同tag官方API；本审不证明当前已有实现。
2. supervisor持有mapping记录并完成规定持久化后，driver才可提交copy；记录与真实group/UUID/PID/startticks绑定。不要让“driver先写文件、尚未被supervisor确认”留下新的竞态。numeric非性能阶段可付此固定持久化成本。
3. 同一次close内固定TERM/必要KILL/轮询的有界子截止；不得把停止升级当追加transfer重试。原numeric_unit对attempted actor不再close的规则须与backend一致；已知无依赖第三actor不能因importer等待耗尽全部收口而被无条件漏清。
4. 常规失败、driver被KILL、外层finally与sampler失败都进入同一依赖清理和原始终态；supervisor自身被SIGKILL/宿主机崩溃不能宣称必有回执或必释放。未知身份仍拒绝信号，所有未确认情况阻断后续。
5. 完整入口确实经过原source/GPU grant/fresh booking/resource/双锁/durable claim，36次先扣账后提交且无重发，0模型请求/0隐含重试；raw采样错误与RPC失败不能被吞掉。mock不能制造实际proof或绕开candidate拒绝。

这些是对已批准设计的可检查验收项，不要求新调度框架、动态角色、额外请求或预算。真实资源、接线G2/G5/Git-first、独立实际生命周期审查和numeric36硬件G3仍各自独立。

## 保持不变

MiniCPM-V-2_6 FP16/TP1、同NUMA三H20、共同65%、官方DECODING无模型Worker、完整原生KV/VE、6有向对×2载荷×3次=36、1800秒含120清理、整体1440请求/340分钟/零重试不变。原qualification/calibration HTTP与诊断口径保留；selected360仍拒绝，后续实现不能因本次G1省略。Space正式优先、当前本地未发布与旧真实运行版本分别记录，不修改Space730绑定或旧root/claim。

原初审与处方文件保持不变；本文件只对精确v2计划关闭设计B1，不追溯重标旧稿或历史CPU结果。

## G1 接线补充 — numeric 非HTTP身份端点（2026-10-29T07:04:40Z）

**APPROVE / BLOCKING 0，仅批准下述最小本地接线设计。** 已只读核对当前 production_identity.environment/worker_identity/publish_service/assemble_services、numeric_unit.validate_identity/execute及numeric_cache.copy_full_cache。当前environment确实只接受HTTP loopback，而numeric身份只需同组一致的非空关联端点，没有HTTP请求需求。允许numeric专用GCS标识比伪造HTTP服务地址更准确，无需新增身份抽象或另一个服务。

实施边界：

- 仅显式 `REPRO_NUMERIC_ONLY='1'` 时接受规范的 `gcs://127.0.0.1:<本次实际私有head端口>`；严格端口1..65535，无userinfo/path/query/fragment，无外网、无ray://，不把它作为Ray Client连接协议。Ray连接仍使用已核CLI实际address格式；gcs标签只供身份绑定。
- numeric必须显式 `REPRO_REQUEST_IDENTITY='0'`，身份env返回值保留numeric flag；原root/RUNID/commit/deploy/profile/UUID校验全部保留，不仅检查地址外观。numeric+HTTP、numeric+requestdiag、非numeric+gcs全部拒绝。原非numeric HTTP资格/校准路径行为保持。
- backend在本次ownedhead原始回执和actor实际身份之间核同一个GCS标识；三actor彼此一致还不足，必须与该head相等，不能仅从输入env自我证明。
- 当前publish_service只比port，assemble_services也不独立限定URL scheme；放宽environment后，不得让numeric路径借这两个HTTP helper产生伪API/endpoint manifest。最小做法是在HTTP服务发布/汇聚入口拒numeric模式（或同等明确的HTTP-only前置校验），numeric仅调用worker_identity，不调用这些helper。普通HTTP路径不重构。测试补numeric不能发布/汇聚HTTP服务原件；这是维护“0 HTTP endpoints”语义的必要小护栏，不是新框架。
- 针对性CPU源码测试覆盖所提拒绝项、missing source字段、普通HTTP回归及head回执地址不匹配；真实Ray/CUDA身份仍待后续Gate。无请求、传输、资源或预算新增。

本补充没有运行测试、改源码、远端/GPU操作或授权实际执行。后续G2核精确代码及测试，不能把本设计批准当实现或实际G3通过。

## G1 设计讨论补充 — 直接持有 Node 的候选（2026-10-29T07:12:06Z）

结论：**值得在v3明确取代非block CLI；在固定Ray2.10.0并补齐RayParams构造证据的条件下，直接Node是更小、更容易核归属的设计。** 非block CLI并非不可用，但为可靠捕获退出前daemon父链另加跟踪，比现有官方Node.all_processes直接持有Popen更复杂。本审不要求继续CLI，也不建议靠全机同UID/root扫描补PID。此为方案讨论，待精确v3计划再窄审；不批准真实运行。

本轮本地git hash-object与provenance实核：Node blob `75ac87f9e3ae22cada48d6848c0ead7908b00020`、services blob `b0a39b293c3d5152451f2c42061b9c02a9905cff`。Node53–86：shutdown_at_exit=False不注册shutdown hooks，spawn_reaper=False令kernel_fate_share=False；305–306不启动reaper。Node400–414的atexit/SIGTERM整组kill仅由_register_shutdown_hooks注册。services966–1007仅fate_share=True时设置Linux父死信号/Windows job；对应Node的GCS/raylet等启动均显式传self.kernel_fate_share。故该构造在这些已核路径上与非block CLI的Node调用语义一致，并去除CLI解析、短命父和session回读的额外桥接。

实施需保持以下小边界：

1. supervisor直接持有Node，不调用ray.init创建head，不将Node放进driver的_global_node；driver另进程exact-address connect-only。shutdown_at_exit=False/spawn_reaper=False/head=True必须显式，禁止Node.kill_all_processes/通用finally全杀。supervisor自身TERM/INT采用本项目有界清理函数，而非Node默认钩子。
2. **all_processes并不使启动绝对无竞态。** GCS/raylet的services.start返回后才写入该dict（例如Node1120–1136、1190–1206），且Node构造器中途可能抛异常，`node = Node(...)`尚未完成赋值。实现需保存可检查的部分初始化对象/同等最小登记，并处理信号在Popen已创建到dict绑定之间只记状态、后续统一收口；不得在构造未返回时直接抛信号导致丢失已创建对象。无需靠猴子补丁/通用扫描解决；具体少量代码交G2核。构造失败发生在actor/copy之前，原始BOOTSTRAP_FAILED/身份未确认依旧如实保留。
3. all_processes给出直接daemon的真实Popen，不自动包含所有raylet后代/agent/actor。沿已登记精确父身份记录实际后代，actor由实际注册绑定；未知helper不盲认、不伪称完整释放。Node构造成功和daemon身份闭包/WAL完成之前不创建numeric actors。
4. 先补同tagRayParams原文，固定构造参数，禁止默认external Redis、地址auto或环境hook引入外部实例；固定temp/session/loopback/GCS端口、3GPU/3CPU及无dashboard/usage口径。安装环境Node/services/parameter实际文件SHA与冻结证据核对，错版本拒绝；这只是版本准入，不能替代真实生命周期Gate。
5. 真实CPU-only Ray/POSIX Gate相应改为直接Node路径，验证Node构造/部分失败、driver TERM/KILL、supervisor可控TERM、实际daemon身份与按序无残留；不要只测CLI旧路径。supervisor自身SIGKILL/OS故障依旧不作绝对恢复保证，保存能保存的故障事实。

mapping WAL、1680/120截止、importer确认后才释放exporter、未确认故障终态/禁止后续、36/1800/340/零重试、无模型load与其它v2接线要求全部保留。直接Node不会解决Raylet/GCS或驱动自身故障，也不因此扩大CPU/GPU授权；它减少的是启动/归属桥接，不削弱清理约束。
