# SpaceServe隔离MPS数值预检（2026-11-04）

两个指定客户端已在唯一自有MPS server下完成FP16数值计算，逐元素匹配CPU期望；确认客户端清空后退出服务，进程清点与显存核验均通过。**这是MPS可用性预检，不是SpaceServe模型或计算重叠证明。**

| 项目 | 实测 |
|---|---|
| 设备 | 单H20，UUID GPU-6186aa04-e2e2-84c4-0c50-a8d1bb260e32 |
| 客户端 | PID2753710、2753711，torch2.5.1+cu124，FP16各1024元素 |
| 数值 | 两者exact=true、mismatches=0，actual与expected SHA逐一相同 |
| MPS成员 | get_server_list返回2753800；get_client_list恰为上述两个PID |
| 退出 | 两client、controller、outer均0；cleanup_error=null、child_errors=[] |
| 释放 | quit前client列表为空；post MPS进程清点为空、目标卡0MiB |

使用既有环境和[数值脚本](../tools/official_isolated_mps_numeric.py)，版本8ef0c8c1860d55811d774b66e1365edd3062a0a3，SHA256 c64ebacf74a63f4d9589778e58c83f8a0b3d9d8ba763d8bc0987c0c94e14bbd2。官方SpaceServe基线仍66de079af4234b27f7f82ff91d238ef1351324ba，源码未改。官方仓库的enbale_mps.sh提供启动MPS示例；本诊断改用独占0700运行目录、前台控制器和目标UUID，没有使用共享全局管道、sudo或更改compute mode。

两个client的设备属性直接记录目标UUID；control/server/client均核UID、出生时间、ROOT/RUNID和管道身份。MPS成员关系与数值结果共同支持本次可用性。不能仅凭驻留或membership推断同时计算，也不以MPS代替encoder mask。此前未启MPS的C4数据保持原配置与独立批次。

## 原始证据

- [两client成员关系](../validation/isolated-mps-20261104/mp1/membership.json)、[client0数值与UUID](../validation/isolated-mps-20261104/mp1/client-0.ready.json)、[client1](../validation/isolated-mps-20261104/mp1/client-1.ready.json)
- [每条实际控制命令及返回](../validation/isolated-mps-20261104/mp1/control.jsonl)、[工作及清理终态](../validation/isolated-mps-20261104/mp1/terminal.json)、[独立post进程清点](../validation/isolated-mps-20261104/mp1/mp1.outer-exit.json)、[运行中PID/UUID原始样本](../validation/isolated-mps-20261104/mp1/gpu-during.json)
- [原件路径、大小与SHA](../validation/isolated-mps-20261104/mp1/server-manifest.json)、[独立G3/G4](../validation/isolated-mps-20261104/mp1/independent-g3-g4.md)、[G1](../validation/isolated-mps-20261104/g1-isolated-mps-mechanism-20261104.md)、[G2与执行条件](../validation/isolated-mps-20261104/g2-isolated-mps-numeric-20261104.md)、[CPU回归](../tools/test_isolated_mps_cpu.py)

本次实际RPC均返回完整stdout/stderr并被记录；生产RPC超时分支可能没有保留部分输出，其GPU故障恢复尚未实测。CPU假控制器测试不代替MPS实测。没有模型输出、吞吐、TTFT或TPOT数据。

复跑先核本人资源与360秒单元余量、旧MPS服务、固定GPU UUID/占用、源码/脚本SHA；身份不明或无法排除冲突时不启动，不quit旧服务。在既有服务器目录用space环境执行脚本，参数为不存在的新run路径（父目录必须是/local/boyjiang/spaceserve/runs）。保留外层真实stdout/stderr/退出及post清点；不能只凭terminal验收。脚本工作180秒、清理120秒，另留60秒保存。独立管道和日志仅数KB，没有复制环境或权重。

下一步：模型/Nsight采集须新适用代码审查、离机版本及fresh准入；真实请求窗口、角色kernel归属、抢占边界与导出收口仍待验证。有效mask与正式三组公平性能对照未完成。该预检没有大trace，本次未新增Release资产。
