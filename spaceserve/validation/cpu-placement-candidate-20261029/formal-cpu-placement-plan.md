# SpaceServe新正式批次CPU放置候选修正（仅本地准备）

依据formal-cpu-placement-audit.md：外层CPU50限制会默认继承到服务/worker/client，OMP4不解除单logicalCPU限制；旧raw无实际affinity/CPU利用率，不据此声称已定位性能瓶颈。旧全部批次保留原样，新候选不与其绝对性能拼接。

候选最小行为：监督器/CPU准备保持CPU50/nice10；仅GPU工作负载entry在已冻结新config中明确设置workload_cpu_affinity为GPU近侧同一NUMA的logicalCPU集合。已有qjh003同boot topo原件GPU0–3为node0/CPU0–89，候选共享0–89，实际新窗须fresh核boot、UUID/PCI NUMA与node0 cpulist/online一致，OS设定后读取回验失败即停。三组native/解耦/mask共享同一个总集合，不按角色增加CPU总预算。OMP4、模型、请求/缓存、精度、单GPU预算、54/5400/1080及201分钟入场不变。现有17–20不足201，候选不授启动或缩矩阵。

实现只新增小型stdlib cpu_placement.py及tests，entry.py仅对numeric/model/formal且明确配置时设置，CPU/prepare不改；不存在该field的历史配置保持旧行为。record_device/capture_runtime增加worker与server实际main/thread affinity及OMP字段（启动/测量边界，不加高频监测扰动）；run_models/run_formal用同一个小校验拒CPU集合不匹配。source-files成员更新，不改框架、权重或SM实现。

成功标准：纯CPU tests拒bool/重复/负CPU/非法NUMA/跨node CPU，配置缺失不偷偷放宽，CPU-only action不set，mockOS set/readback必须一致；worker/server记录错mask或线程超集合拒绝，允许线程在该统一集合内更小subset但main必须精确匹配。测试不调用真实sched_setaffinity、不导Torch/Ray或GPU，不SSH；原文/代码/测试/审查绑定SHA。

G1本次仅请求本地候选实现与CPU测试许可；这是把工作负载CPU资源配置变得明确的可评审变更。实际采用该新profile须独立G2、确认其属于已授权资源范围或按AGENTS1.2③取得用户确认、Git-first与新窗实际CPU/numeric/313/G3，不能直接复用旧CPU50模型Gate。正式前再核真实长CPU+GPU预约；当前不触碰他人10–16CPU/10–17GPU。
