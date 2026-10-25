# G2 正式A聚合复审

实际审查者：独立subagent `/root/profile_plan_review`，Claude额度耗尽后接替，只读未执行完整分析或实验/GPU。

首审REQUEST_CHANGES、3项BLOCKING：吞吐重复窗口未绑定真实请求；三物理GPU/显存归属不足；capture状态与request ID不足。修复后APPROVE_WITH_NITS，3项关闭，剩余0。

validate_interval核对重复身份、有限正duration、提交/完成窗口，1秒明确为调度/尾部JSON记账审计上限，输出实际开销，不调整分母。validate_runtime固定003的G3 boot/三唯一UUID/PID/两库路径；memory核对device、PID、bytes和sum。capture核对实际API PID、enabled/capturing、时序、末16barrier；request ID按endpoint命名空间唯一。indexed拒绝实际行重复。旧固定ZIP/源文件SHA保留；分块哈希兼容000 Python3.10。

已读5项CPU用例PASS，允许在qjh000执行CPU聚合，测量仍标qjh003。NONBLOCKING：G4列出八case的实际首尾开销、显存采样间隙并核对完整运行；一个case测试不是八case审计，也不是CUDA关键路径或性能结论批准。
