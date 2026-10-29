# EPD native36：真实后端与生产入口接线计划

仅请求本地设计/实现/CPU mocks；无SSH/真实Ray、NVML、Torch或CUDA初始化，无GPU或实际CPU部署许可。目标不是再做一个不可运行的组件：将现有numeric_unit与官方worker连接，并补真实准入入口，随后才可能在有效资源/Gate下跑完整native36。selected360仍另待实现，不能因native接齐提前开放。

## 不变范围与成功标准

MiniCPM-V-2_6 FP16、TP1/PP1/DP1、同NUMA三H20、共同65%、完整原生KV/VE载荷、6有向UUID对×2载荷×3copy=36；0模型请求、0隐含重试、一个1800秒claim（含120收口），全批340分钟预算不变。官方Worker只用DECODING无模型numeric路径，不调用init_model/load_model/execute_model；真实角色链路验证不由numeric替代。完整向量成功与失败raw逐条保留；未确认释放不签PASS、不启动下组/后续单元。

实现结束后本地应能通过真实入口的CPU注入fixture走完 authorize→scope→source绑定→fresh booking/resource→durableClaim→36transfer→逐进程释放→终态；注入fixtures均标CPU-MOCK，不给候选配置签授权或制造G3。原qualification/calibration仍走原HTTP路径，selected360仍failclosed。

## 新核到的实际生命周期约束

已从GitHub connector按ray-2.10.0拿到worker.py完整原文，本地git hash-object=faf532f0351b4561d753dd4f4eafc697d16ad021，provenance见source-evidence/ray-worker-provenance.json。源码1795–1851明确shutdown会终止ray.init创建进程，且自动注册atexit；2945起kill默认no_restart=True且不执行actor atexit。因此**只在numeric_unit.close里保证importer先停还不够**：同进程ray.init+finally/atexit shutdown会在异常时绕过出口依赖，不能直接实现这种方案。

采用独立、唯一归属的本地Ray head supervisor和显式named detached actors，使numeric driver退出不自动杀exporter，head只有全部actor释放已实际确认后才接受停止命令；不连他人Ray、不用ray stop/killall。head启动之前绑定UID/root/run-ID/PID/startticks/boot和独占pipe/地址receipt，actual address只从本head回执读，driver只连该地址。head本身不分配GPU、不导torch；可见GPU仅固定三UUID，Ray各actor仍自行设CUDA_VISIBLE_DEVICES，不能在actor runtime_env覆写它。actor每组新建三份，max_restarts=0/max_task_retries=0，唯一namespace/name；原worker constructor不load权重。具体Ray named/detached与head启动API需继续按同tag官方source核对，未核就不猜API。

清理依赖不被泛化finally绕过：close(target)按原始身份核对后只kill该actor并等待/proc消失和NVML中该PID/context不存在，再释放source，再第三worker；组终态三卡idle才开下组。bootstrap未知/身份歧义一律拒信号；已知兄弟可独立清理。若importer退出不能确认，保留exporter/head，记录release_unconfirmed和依赖链，阻断下一单元，必须显式报告残留并处理真实截止边界，绝不由head自动超时/driver atexit把它伪装成正常释放。此异常可能不能自动满足硬截止释放，属于必须审清的设计风险，不签发GPU许可。G1应明确这一错误路径是否需要改设计；批准本地CPU实现不等于批准实际留存GPU超过预约。

## 源码接线

1. numeric_backend.py/必要最小head入口：惰性导入实际Ray2.10.0；官方EngineArgs经runtime_options构造共同eager/4096/8/.65设置，再ModelConfig(fp16,seed0,pd_fused=false,dummy=false)、CacheConfig(16,256,.65,0)、ClusterParallelConfig六项[1,0,1,0,1,0]、DECODING Worker。identity→allocate→prepare/copy/sync复用现有RPC，不改native IPC或缓存形状。实际UUID/PID身份决定映射，不假设Ray顺序。
2. numeric_evidence.py（若单文件足够并入backend）：在actor bootstrap前开始raw NVML与/proc采集；按组生命周期接受bootstrap先观察后绑定，但只有该head创建的已验证后代可绑定，所有compute PID最终必须对应该三actor。每样本记provider/clock/UUID/bytes/processes，累计65%与未知PID检查。正常退出期间采样接受已验证PID消失；不能重用要求三模型常驻的旧collect。每次RPC前后及持续采样的原始错误都留档，采集失败停止transfer。
3. fixed_unit.py增加exact numeric schema/profile，0batches/HTTP/endpoints、不允许任意argv，model/config/完整向量SHA与36/1800均固定；load_execution numeric不生成HTTP clientargv。preflight_controller run在原actual授权/source/booking/NVML/Claim与两锁之后分派numeric；跳过admit_request(0)，每次copy仍由numeric_unit.admit_transfer在submitted前扣账。所有终态关联claim/source/dep/config及raw SHA，不自行签G3。selected360拒绝保持。
4. 生产源码闭包包含新helper/head/tests；旧运行、Claim、封包、旧main成果不重写，不复制日期/vN整工程。先独立G2/G5、commit/push/API前核，才另申请新实际CPU/GPU scope。

## CPU测试

fake Ray API须验证实际options、三freshactor及真实RPCdispatch/timeout剩余值；异常/超时无retry，无init_model调用；wrongUUID、wrongsidecar、head identity/address mismatch、foreignPID、extraCUDA driver PID、sampler异常、PID复用、同UUID仍有context、importer close失败导致exporter/head不被finally或atexit停。正常36只在原始观测实际idle后关闭head；启动失败及部分actor身份未就绪清理已知而保留未知。完整入口fixture验证候选在Ray/NVML/spawn前拒绝、0requests/36transfers/单claim、HTTP资格回归不变、selected继续拒绝、来源或预约不符无副作用；测试覆盖真正分派而非只验证常量。真实Ray版本/启动/进程行为依旧须后续实际G3，不拿Windows mocks替代。

本计划核心未决是“异常无法确认importer退出”与共享主机硬截止的兼容性；先独立G1审明再编码，发现矛盾不能悄悄选择泛化shutdown。当前GPU正式实验仍优先SpaceServe；本阶段只做本地，不额外占卡。
