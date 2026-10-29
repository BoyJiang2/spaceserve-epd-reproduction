# Native36生产后端：有界生命周期修正

本方案完整继承[numeric-production-backend-plan.md](numeric-production-backend-plan.md)的模型、三卡、缓存、36次原生传输、0模型请求、1800秒（含120秒清理）、整体340分钟、零重试及入口/证据/CPU测试接线要求。仅修订独立G1指出的head所有权与异常截止矛盾；原计划与初审原文保留。本轮仅申请本地实现和CPU测试，不执行远端或初始化实际Ray、Torch、NVML、CUDA，不批准GPU。

成功标准仍为完整可运行的native36生产路径：不是只增加一个mock组件。实现必须连接官方Worker、完整原生KV/VE载荷、实际身份与采样、原source/booking/claim/双锁准入、逐次扣账与有界释放。实际生产GPU开放另须真实生命周期验证和相应G2/G3，不能用本地mock代替。

## 1. 具体head与driver

使用当前已冻结Ray2.10.0环境内的`ray start --head` CLI，明确**不带`--block`**，不调用本地`ray.init()`创建集群。参数固定为私有`--temp-dir`、`--node-ip-address=127.0.0.1`、一个审定的唯一端口、`--num-cpus=3`、`--num-gpus=3`、`--include-dashboard=false`、`--disable-usage-stats`；具体端口和短目录进入后续实际参数清单。已有端口/目录/未知Ray实例冲突时拒绝，不发现冲突后自选新端口重试。实际地址必须从本次CLI/私有session原件核对，若不是本次限定loopback端点则失败，不自动连接默认地址或`auto`。

官方ray-cli-2.10.0.py blob a12df6d3e0acc6b859084941eeda0564902d4801的790–791行将Node的shutdown_at_exit和spawn_reaper都绑定block；970之后全组kill监视也仅在block分支。选择非block规避正常CLI退出导致的全组清理，不保证Raylet/GCS/驱动故障时actor存活。driver只`ray.init(address=<本次地址>, namespace=<本次唯一namespace>)`连接既有head；官方worker.py blob faf532f0351b4561d753dd4f4eafc697d16ad021的connect_only路径与本地创建路径分开。driver不创建Ray head、不用ray stop，也不在finally全杀actor。

三fresh actor采用唯一name/namespace和lifetime=detached，max_restarts=0/max_task_retries=0；实际GPU仅固定三UUID，由Ray分配后核实际UUID/PID，不runtime_env强行覆写Ray的CUDA_VISIBLE_DEVICES。每组三actor、12组、36传输不变。禁止模型load/init/execute。

CLI启动前已存在独立窄supervisor，它不导torch/不分配GPU；记录UID、boot、root、RUNID、nonce、PID/startticks和私有temp/session。启动后在任何actor产生之前将已验证daemon身份（/proc startticks、exe/argv、UID、私有session/端口及原父链）落盘。不能仅凭同UID/进程名/端口认领进程。driver异常或退出不结束supervisor，外层timeout只向supervisor送可控信号；不按进程组/后代列表泛杀Ray。

正常CLI退出是预期事件；启动中异常退出为BOOTSTRAP_FAILED，只处理已证明属于本次且未产生IPC的进程，未知身份不发信号。运行中GCS/Raylet意外消失或进程身份变化为INFRASTRUCTURE_FAILED，保存原始事实、禁止新transfer、不宣称IPC按序释放。启动行为和父链收集必须经后续真实POSIX/Ray无CUDA测试确认。

## 2. 工作、清理与异常终态

claim总期限仍1800秒。最晚1680秒停止一切新allocation/copy/新组；所有RPC获取剩余工作时间。预留最后120秒仅收口，不将worktimeout再延长到清理区。supervisor使用同一单调时钟deadline，信号触发也进入同一清理函数；初始化耗时计入总1800。

清理依赖由窄supervisor保存：在调用目标copy之前先写入mapping_possible及source/importer实际身份，再提交RPC，避免driver在RPC中消失丢失依赖。正常/异常/TERM/driver退出共用同一有界状态机：停止提交→仅终止可验证的importer（TERM后在剩余预算内必要KILL）→反复只读确认原/proc PID/startticks已退出且原GPU NVML中无该PID/context→才终止exporter→第三actor→全部actor真实释放后停止本次可验证daemon。每次信号先重核身份，不触碰他人；轮询确认退出不属于重试transfer，不能重新创建actor、重跑unit或重发copy。

未知bootstrap actor无IPC时可独立清理已确认兄弟；已有mapping_possible且importer未确认时绝不能用通用finally、head shutdown、kill_all_processes或HTTP cleanup_owned越过依赖。numeric走独立最终清理入口，HTTP资格/校准原有清理不改。

如果在最后期限前仍无法确认importer（例如D-state、驱动/查询故障），进入唯一失败终态`FAILED_RELEASE_UNCONFIRMED`：保存PID/startticks/UUID、原始NVML与/proc、信号回执、最后采样、仍可能存活的exporter/head及依赖；通知主线程并阻断下组/后续unit。supervisor在期限停止新的工作和无界等待，不给不明进程发信号，保留失败证据与断点。**这不是延期或继续占卡许可，也不是released/PASS**；属于无法用用户态程序保证恢复的运维故障，需明确报告实际残留和预约影响。不得伪造已释放、默默增加租期或预算。常规可控TERM/KILL路径必须在120秒内真实完成；实现若连此条件不能保证/验证，GPU入口保持拒绝。

原“只有全部释放才接受停止命令”改为上述两种终态：成功时按序释放全部daemon，失败时有界退出并如实记录未确认残留；不再承诺基础设施故障下绝对按序退出，也不把无限retain当作正常策略。

## 3. 验证与接线顺序

先本地实现完整后端与生产分派，CPU注入测试覆盖原计划全部身份/内存/36向量/扣账场景，并新增driver正常/异常退出、CLI退出、head故障、外层finally、1680工作截止、1800终态、importer未确认组合；核source不会被通用cleanup越过依赖，driver不会拥有head/reaper。bootstrap闭包落盘前不能分配actor，mapping记录落盘前不能提交copy。

再独立G2/G5、Git-first发布与部署。真实CPU-only Gate另审范围：在私有无GPU资源head（num-gpus=0、CUDA_VISIBLE_DEVICES空）、无torch import的轻actor上验证CLI正常退出不杀head、driver退出detached存活、监督器TERM、已知PID/startticks单体TERM/KILL清理、故障记录和无残留；这是生命周期证据，不等于官方Worker/CUDA IPC通过。CPU测试须保留原始/proc/进程与终态，不能只看Ray布尔返回。

上述真实生命周期和接线G2未通过前，生产GPU入口明确failclosed；通过后仍需新合法三卡窗口、实际原生numeric36 G3及后续资格/校准/selected360 Gates，不复用旧host PASS。若真实Ray行为与官方源码推断不符，保存失败并修复，不现场切换head方式。SpaceServe正式测量优先，EPD仅本地推进，不在其GPU正式期间部署或跑本批。

本地EPD实现暂不commit/push，以免改变Space scheduled CPU控制器绑定的main/HEAD730及已审bundle。Space实际冻结部署完成后再安排EPD精确发布，不把本地未发布代码称为已部署。
