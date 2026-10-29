# 单GPU临时空闲预检G1

结论：APPROVE_WITH_CONDITIONS；本地候选设计BLOCKING0。reviewed_at：2026-10-29T04:56:46Z。**只批准本地接线/CPU mocks的设计范围，不授现在GPU执行许可。**

只读审space-temporary-idle-plan.md、当前booking_window.py/resource_guard.py/reproduction_paths.py/mps_owner.py，未实现、运行测试、网络、SSH、GPU查询或读凭据。仅保存本审查文件。plan SHA25677008d58489ca1e2a870e6abfb6a88f06474c820c8230e1852c919033eb7e8c4。

## 授权与规则判断

按本次可信直接任务所传达的最新用户授权：“如果gpu暂时没人用 你可以先暂时用一下”，以及用户已经明确采用监督器CPU50/三组NUMA0logical0–89/OMP4profile，允许设计一个明确的临时空闲资源路径。该最新条件授权可以覆盖此前项目自设的“任何短时预检必须本人GPU预约票”限制；不再要求用户重复确认已明确给出的CPUprofile或临时空闲条件。

当前require_scope要求booking字典、booking_window.require读取BOOKING_VERIFIED并核本人票、migration/helper现有CPU票断言，都是仓库实现的本地准入政策，不是不可覆盖的系统规则。可以经审查新增独立direct-grant分支，不能删掉或伪造旧票验证。实际他人/未来booking仍按原事实保留，临时记录不能命名/签成本人预约PASS。

在本次所读适用材料中，未发现另一个明确禁止该用户授权下临时空闲单卡使用、且必须额外取得管理员批准的外部规则；因此不凭推断添加管理员批准门槛。本结论也不声称已审核整个集群管理合同，不更改任何外部ACL/预约、不授修改他人任务或绕过实际系统拒绝的权力。

## 条件范围

仅qjh003固定项目根、新独立run-ID、单物理GPU2/UUID GPU-c005197e-747d-2dc8-b77b-b123b41efd75、原boot候选65f52a67-afe4-4919-8646-4694255b48ee、同NUMA0及已确认CPU总profile。04:51占用快照仅为选择背景；实施前必须fresh重核身份、完整sysfs拓扑和所选卡空闲。GPU0/1忙不构成停止它们或干预它们的理由；其他卡空闲也不授权扩卡或GPU2忙时自动换卡。

TEMPORARY_GPU_USE须独立绑定真实授权原文来源/时间/SHA、精确config/source/G1/G2、boot/UUID/CPU集合、动作和起止，不将自写JSON本身当人类授权。一个batch绝对上限60分钟，独立monotonic工作截止与END-120收口，不靠重写start或刷新观察自动续时。每phase开始须有完整预算（模型原1800及cleanup，完整313不缩），CPU准备也须走明确direct-grant CPU辅助scope，不能默默放掉原CPU票断言。

临时分支仅Space numeric/model及必要CPU准备，formal/EPD明确拒绝。缺临时字段保持原booking行为；两类scope不得混成owner PASS。原源码/G2、CPU源清单/实际suite、NUMAset/readback、host/projectlocks、numeric及model实际G3、私有MPS所有权及finally收口全部保留。原GPU0/MASK_OFF56实测仅可作为候选；GPU2须独立CPU、新numeric原生/三次MPS、完整313及真实encoderstream/冷启重启/并发证据，不继承旧PASS。

临时占用监控必须是独立可运行的监督路径，在blocking服务启动/HTTP请求期间也能按0.5–1秒节奏发现选卡foreign/unknownPID、查询失败、用户撤回或截止，保存原始触发并停止本项目提交；不能只在phase边界调用一次require。查询自身超时应纳入检测/总截止。PID所有权需UID/start/root/runid/私有MPS证据闭合，AccessDenied/采集异常不能当“没有foreign”。只TERM已确认自有入口，让原finally结束自己的服务/MPS；不得signal外来PID、全局MPSquit或为了恢复显存0而等待/清理外国作业。外来作业仍在时本phase失败、无下一Gate；自有释放证据与“整卡全空闲”是不同事实。

现有mps_owner.py有全主机发现任何MPS就拒绝start的保守检查。GPU0/1若已有其他MPS，不能因GPU2看似空闲就跳过/删除该检查或quit他人daemon；可保留拒绝，或另在G2审明确的选卡/私有pipe隔离实现。当前动态GPU编号校验使用CONFIG.gpu_devices[0]；旧错误字符串GPU4不是GPU2兼容已实测的证明。

## 实施与验证门槛

准许小型temporary_gpu_use.py、纯CPU mocks及最小明确scope接线本地候选。测试应覆盖授权缺失/篡改、host/boot/UUID/NUMA/时间窗及不延长、formal/EPD拒绝、忙卡/foreign/unknown/采集失败→只停own、不信号foreign、原始触发与失败终态、缺scope的原booking回归。实际监控、MPS归属、清理及实际线程放置不能由mocks宣布通过。

实施后须精确G2/G5、Git-first/指定commit与source闭包、受审有界目标CPU验证及fresh idle才考虑实际numeric；numeric实际独立G3后才完整model313。新run原件保全、不重跑旧claim；正式性能仍0/54。他人GPU0/1的背景负载意味着本次只作机制预检，不产生可比较的正式吞吐、延迟或隔离收益结论。不扩GPU预算、不改driver/SM库、不自动延长60分钟。

参考源SHA256：booking_window f2e4086bd93de4dbefd7132121280c16e7605986d14afd961f978d30bc1df4d1；resource_guard4bc7f6d1c5e26c5ef4818f27db79a82bd58a34f4a4b2bf1a749572c1e1107d42；reproduction_paths f5d6e86de8655ecfcf1e7e3e3657e12b24759cdc7f7d5a09d23fdfc146803755；mps_owner62e8b70a0246c2e0ce6961b7bf4385b01578cfa825c119148f50c66392b99e36。

GATE_RESULT: {"gate":"G1-temporary-idle-GPU2-design","decision":"APPROVE_WITH_CONDITIONS","blocking":0,"reviewed_at":"2026-10-29T04:56:46Z","local_candidate_preparation_allowed":true,"current_GPU_execution_authorized":false,"temporary_batch_minutes_max":60,"formal_authorized":false,"extra_administrator_approval_inferred":false}
