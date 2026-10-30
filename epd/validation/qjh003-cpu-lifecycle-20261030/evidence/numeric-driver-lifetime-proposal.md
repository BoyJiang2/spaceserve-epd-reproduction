# Native36 driver生命周期：先固定Ray真实退出行为

## 已取得的新源码证据

已用GitHub连接器读取ray-project/ray的ray-2.10.0原件，原字节保存在source-evidence，Git blob身份已重新计算核对。actor.py SHA2567177e5fe、worker.py SHA2565e6a29a4；完整值和原URL见source-evidence/driver-lifecycle-source-pins.json。

- [worker.py](https://github.com/ray-project/ray/blob/ray-2.10.0/python/ray/_private/worker.py#L1795)：Ray注册了自动退出shutdown hook；该路径会断开driver/CoreWorker，并处理它所持有的Node。不能仅凭我们的driver没有显式调用shutdown就声称退出不触发Ray生命周期。
- [actor.py](https://github.com/ray-project/ray/blob/ray-2.10.0/python/ray/actor.py#L1008)：detached/non_detached是不同lifetime选项。
- [官方对应文档](https://github.com/ray-project/ray/blob/ray-2.10.0/doc/source/ray-core/actors/named-actors.rst#L164)：detached actor可越过driver生存期，且不会按普通actor方式自动回收。此事实不证明任何真实创建已经quiescent。

原v3约束是父保持唯一创建/依赖/释放账，driver不拥有head、不在finally代替父清空状态。新allocation校准已经本地13测试及G2通过；仍未实现实际driver。现在必须在写实际driver前区分下面两条路径，不默默把任何一种当已验证。

## 两条候选，当前尚不冻结GPU策略

1. 显式non_detached，正常路径先由父按importer→exporter释放所有真实actor，再结束driver。异常driver死亡可能触发Ray自身的owner清理；不能声称仍由父控制顺序。异常结果需真实GCS/PID/上下文证据，不凭driver退出或NVML暂空签released。若这与既定故障收口合同不兼容，应拒绝此分支。
2. 显式detached，使已建actor不因driver死亡自动消失；driver自己的已pin shutdown hook如需调整，必须明确审查而非偷偷patch。父仍持有真实PID依赖并负责释放。但pending creation可能在driver退出后继续创建，不能把detached当安全证明。是否需要精确取消本namespace/ActorID创建、能否满足原quiescence合同，须真实CPU-only证据及新独立裁决，当前不授权ray.kill兜底。

## 本次申请的最小下一步

先实现一个独立、有限、0 GPU的Ray生命周期取证单元，复用numeric_head的私有Node/registered-spawn和已有父pidfd合同；不先改实际GPU driver。只申请本地设计/代码/CPU mock，具体真实CPU运行须Git-first、部署及单独执行G2。

- 仅冻结Ray2.10.0及既有Node/services/parameter pins，新增worker.py/actor.py实际源校验。全部source pins须在Ray导入前按package文件读取核对；不改Ray安装文件。
- head gpu_count=0，空CUDA_VISIBLE_DEVICES，测试actor num_gpus=0且不导入Torch/EPD Worker/IPC/model；测试实现不调用CUDA/NVML，不抢占Space GPU。Ray自身的发现/读取路径仍须源审，不能把0配置当作所有库均未读取硬件的证明。维持CPU50/nice10。
- 使用本次唯一私有head/address/namespace/root/RUNID/nonce；父不连接额外driver或用重试探测接管；每次实际创建前原WAL，持续保存本次head后代/实际UID/PID/start/namespace/ActorID事实。
- 比较driver正常退出与创建返回窗口内的受控退出，在non_detached/detached两种明确选项下，记录实际GCS actor状态变化、所有已证PID退出/仍活及是否出现迟到创建。pending状态绝不先验视为无actor。
- 每种场景单次、0重试；全部场景合计工作<=180秒、清理<=120秒，绝对截止前120秒停止新工作。私有Node自身和全部CPU子进程仍由可验证pidfd/登记表收口；不清理其他head/同UID其他项目/UID2071任务。
- 如果某未知归属或创建状态不能确认，原样FAILED_RELEASE_UNCONFIRMED，不靠名字、字典空或driver死亡签成功；记录实际残留与下一断点。
- 本地测试和实际CPU证据都不能自动批准GPU native36、CUDA IPC或model，更不是PD/EPD性能结果。只有生命周期证据审查后才冻结最终driver策略、实现handler/collector/完整dispatch并继续原native36 Gates。

## 保持的目标

原三卡/36原生传输/0模型/1680+120、12 fresh groups、slot+allowed UUID实际分配验证、copy前父依赖fsync、importer先释放、无业务重试均不改。Space源码24b、当前实验配置/预约范围及正式54/201分钟不改。本步骤服务于完整backend，不把0GPU生命周期探针替代原实验目标。

当前没有新远端操作、Ray运行、GPU通过或原件释放结论。请独立G1裁决此取证范围和两条候选是否完整；若原v3已有更小且严格等价的解法，应优先指出，避免额外架构。
