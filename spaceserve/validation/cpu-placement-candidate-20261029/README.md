# SpaceServe CPU 放置候选（尚未采用）

这是下一正式批次的本地代码准备，**不是性能结果，也不是 GPU 运行许可**。新正式矩阵仍为 0/54；旧批次和原始记录保留。

外层 CPU50 绑定可默认被 GPU 服务、worker 和客户端继承。旧记录缺少实际 worker 亲和性及 CPU 利用率，因此只能确认源码继承路径，不能断言已定位旧性能瓶颈。

候选将监督器、CPU 准备保留在 CPU50/nice10；GPU 工作负载三组统一共享 NUMA0 的逻辑 CPU0–89，总预算相同。保持 OMP4、单 H20、Qwen2-VL-7B FP16、缓存与请求协议、54 单元/5400 正式/1080 预热、201 分钟入场门槛。90 指逻辑 CPU，不是90物理核。未验证 decoder 互斥，不称完整 SM 分区。

源码入口：[entry.py](../../runtime/entry.py)、[CPU 放置与证据校验](../../runtime/scripts/cpu_placement.py)、[测试](../../runtime/scripts/test_cpu_placement.py)。[候选配置](../../runtime/configs/project.cpu-placement.candidate.json)没有 run-ID、GPU、预约或允许动作，不能直接运行；历史缺失 profile 的配置不扩核。实现检查实时完整在线 NUMA CPU 集合及 GPU UUID/PCI NUMA，OS 设置后精确回读；worker/server 在启动及请求前后记录实际 main/thread affinity、PID/start ticks/UID/nice 和线程环境。单个线程可绑定集合内子集，主线程须匹配共享总集合。

## 本地验证

```powershell
python -I -S -B spaceserve/runtime/scripts/test_cpu_placement.py -v
```

[候选结果](candidate-result.json)：9 测试 PASS、0 skip；覆盖非法配置、NUMA/在线 CPU 不符、OS 回读不符、线程越界、PID 复用、冻结 helper/manifest 篡改。另按实际部署文件名 `scripts/project_entry.py` 建立[本地冻结布局](frozen-layout-result.json)，同样9 PASS。全部是 Windows CPU mocks，没有真实 sched_setaffinity、SSH、Ray/Torch 导入或 GPU 测试；不能代替目标 Linux suite / numeric / 模型 G3。

初次 mock 的路径后缀在 Windows 上不匹配，6 失败，已改用 Path.name。随后主执行者和独立审查发现冻结入口名及环境变量隔离两项 fixture 缺口，修复后执行上述两种布局测试。9 PASS 仅绑定对应结果 JSON 的实际 SHA；先前测试不覆盖后续修改。

## 采用前剩余条件

按[独立 G1](formal-cpu-placement-g1.md)，新 CPU 资源 profile 属于实验设置变化，仍需用户明确确认；泛化 CPU 可用授权不替代该确认。G2源审查、本地发布与实际运行 Gate 分开。目标执行前还须足够的实际资源窗口、fresh 预约/boot/拓扑、指定已发布 commit 部署与逐文件 SHA、全量 Linux CPU suite、新 numeric 和完整313模型验证及独立实际 G3。201分钟只覆盖冻结正式入场，不能拿180分钟窗口缩验证或拼旧48。

真实 `/proc` 线程可能在取证时消失或拒绝读取，实现会失败并保留现场；Windows mocks 不证明目标无此类运行问题。本候选没有声称性能改善或完成两项目目标。

[独立G2及候选资料G4/G5审查](formal-cpu-placement-g2.md)：最终APPROVE_WITH_NITS / BLOCKING0；两项fixture阻塞及关闭记录完整保留。这仅允许本地候选发布，不授实际资源profile采用或GPU许可。
