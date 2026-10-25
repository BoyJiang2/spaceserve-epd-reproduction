# G2：实际服务stream探针及startup设备hook

实际审查者：独立subagent `/root/profile_plan_review`。Claude新明确session limit证据为outputs/epd-profile-a/reviews/g4-cuda-report-claude.json，按AGENTS3.2.1接替。此前15分钟审查超时不作为quota证据或批准。

结论原文：APPROVE_WITH_NITS。本次8文件G2范围BLOCKING：0；不批准formal或第三组验收。

已读真实源码及CPU日志：探针使用实际stream句柄，core在原调用前后、零mask恢复/重施采样；首次worker执行hook记录current stream并恢复原方法。未设REPRO_SM_PROBE时不安装执行hook，设备记录仅加载阶段，native与fork同入口。helper错误向上传播，不伪造void接口返回。真实patcher二次SHA相同、first-execution mock/语法通过，不代表实际CUDA机制通过。

NON-BLOCKING：warm_model早于encoder stream创建，G3必须确认首次执行记录同core的PID/stream，未被更早warmup消耗；wrapper可自动发现系统/同目录库，launcher须拒绝角色与库发现不匹配；诊断失败必须结束本次并留证；G3核全部before/after/zero/reapply/first-execution集合、UUID、MPS实例及校准库SHA。仅编码器受限，不能称互斥划分或完整论文SIS。

Codex：launcher已增加角色/lib实际发现CPU守卫；实测无划分fork发现None，evidence/unmasked-sm-discovery-cpu.log；该launcher改动由runner G2复审覆盖。其余均作为服务G3验收项，未提前生成SM_EFFECTIVE。
