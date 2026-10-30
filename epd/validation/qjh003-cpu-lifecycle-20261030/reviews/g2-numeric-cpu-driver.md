# CPU 生命周期单次 driver 组件 — 独立源 G2

reviewed_at_utc: 2026-10-29T23:55:27Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，仅本地CPU driver组件源码与fixtures。父四场景entry尚未实现；不授远端CPU/Ray运行、部署、GPU或native36。**

精确源码 `epd/runtime/numeric_cpu_driver.py` 6226 B/SHA `3714b7a8b1cf5cad4e2abd0e30ccde7d4cd654285fe53e220a05083a3b3958dd`；测试实际位于 `epd/runtime/tests/test_numeric_cpu_driver_cpu.py`，5753 B/SHA `956f8cfde0540d9fa717583168f3f307bed6a702e9e5ab0e515fdd8e0a5b32a5`。采用 ponytail 最小接线原则，检查现有接口即可，不新增生命周期框架。仅本地只读源码/官方原件/日志、AST与SHA，不执行项目/测试、网络、SSH或GPU，不改实现。loader/GCS/descendants由另一独立审查负责；本审不替其批准。

## 源码与Ray接口

按既有 `g1-numeric-driver-lifetime.md`：保留普通Ray退出hook，连接已有私有head、不自己shutdown/kill/重试，detached和non_detached仅CPU行为对照。`ray.init(address=...,namespace=...)` 后核实际Node非head、all_processes空、address相等；没有注销atexit或monkey patch。此断言是未来实际执行检查，当前不是实际head ownership或退出结果。

官方runtime_context原件15428 B/SHA `3e3c5c9c1ea66ba4edd83c1c6f920102d613d9542fd20ce2f39bdab4f188e730`，本人重算Git blob `e1ee610fbf45867b23075456bd5ab76720e888fe` 与provenance全同。Ray2.10 `get_job_id()` 返回hex字符串，`get_actor_id()` 在actor返回hex字符串、非actor可返回None，namespace属性返回实际worker namespace；本driver/actor调用位置和类型匹配。既有actor.py明确支持lifetime='detached'/'non_detached'，Node源确有is_head()/address及all_processes，未使用想象的API。

main在Ray导入前核runtime_context pin，再调用既有load_cpu_ray核其余pins/版本/路径与最小dashboard分支；actor构造时重新核原pins加runtime_context。不在本审中把loader已读源码当实际安装包匹配，目标仍须真实preimport Gate。

## 提交、证据与失败状态

spec字段集精确，canonical root/folder/session及归属、无symlink、loopback端口、run/namespace/name、detached布尔和0/15秒延迟限定；实际env要求CUDA_VISIBLE_DEVICES空、EXP_ROOT/REPRO_RUN_ID匹配且cwd在root内。driver意图record先fsync before_actor_create，再单次remote create（CPU/GPU资源0，max_restarts/max_task_retries0），实际handle ActorID核32hex，submitted包含真实driver JobID/namespace/name/lifetime意图；无第四actor、重试或按名称接管分支。

actor验证spec及源后采真实HeadProc自身份、runtime ActorID/JobID/namespace和ray.get_gpu_ids；非空GPU allocation拒绝。constructor-entered.json以O_EXCL/O_NOFOLLOW/0600写入并fsync后才受控延迟；普通ready返回facts，driver按实际handle/driver context匹配身份后才记录actor_ready。record/fsync、remote、get/identity异常均向外失败，不写成功ready、不重发。

constructor可能在driver submitted回执前执行，这是异步创建正常窗口；create前durable intent已记录，不能把submitted缺失当未创建。任何失败，父必须保存未知pending/兄弟与真实GCS/proc/sidecar证据，不依据driver异常退出或registry空判释放。本组件没有声称完成该父收口。

## fixtures与边界

本人核AST中8个测试ID与 `numeric-cpu-driver-final-tests.log` 的8 PASS/0.047s/OK逐项匹配，日志SHA `4c98419ef8faae4e51cc02115a8afadcd01c57e194ff5e37e0f521befa01b195`；没有重跑。覆盖顺序/一次create、显式non_detached、get超时不重试、前置record失败不create、错ActorID拒绝、scope异常、constructor回执在延迟前、非空GPU allocation拒绝。均Windows CPU fixtures/mock，未真实Ray、process或fsync生命周期；constructor durable在fixture被mock，不能用这些测试称实际WAL落盘。

以下是非阻塞但父entry/运行审批必须落实的边界：

1. `ray.init`、remote提交及部分源/文件检查没有该组件内的统一单调截止；ready的20秒与constructor的15秒也不是完整四场景180+120预算。父必须受监督注册driver、按稳定pidfd/真实身份执行控制退出及同一hard deadline，异常/超时保留FAILED与未确认创建。不把本driver当可独立直接执行的受控入口。
2. `name`/`detached`在actor facts中取自spec，属意图回显，不是独立Ray/GCS的实际注册名/生命周期取证；父仍须核真实ActorID/GCS/namespace及生命周期。ready的process字段也是actor自报，父须double-read身份/归属，不能仅凭本ready关闭释放Gate。
3. spec未限定四scenario顺序、namespace/name唯一性或root/folder/session必须彼此分开；它只是窄组件验证。未来父须冻结独立场景/排他路径/唯一intent与预约，不能将fixtures同目录合法例子直接当生产布局。
4. CPUActor禁止已导Torch/EPD、资源0及空GPU ids不证明Ray内部从未查询硬件；loader/最小dashboard source审、实际导入与子进程原件仍独立。没有真实dlopen/IPC/native36/模型/性能结果。

无须为了此组件添加额外driver或协议层。原G1关于non_detached不能隐式替代GPU父唯一释放合同仍有效。精确Git-first发布/部署、父entry源审/测试、实际CPU执行G2/G3之前，保持不可远端运行；不改Space24b冻结或正式预算。

GATE_RESULT: {"gate":"G2-numeric-cpu-driver-source","decision":"APPROVE_WITH_NITS","blocking":0,"source_sha256":"3714b7a8b1cf5cad4e2abd0e30ccde7d4cd654285fe53e220a05083a3b3958dd","tests_sha256":"956f8cfde0540d9fa717583168f3f307bed6a702e9e5ab0e515fdd8e0a5b32a5","CPU_fixture_tests":8,"scope":"local_CPU_driver_component_only","remote_CPU_execution_approved":false,"actual_Ray_lifecycle_passed":false,"GPU_approved":false,"native36_executable":false}
