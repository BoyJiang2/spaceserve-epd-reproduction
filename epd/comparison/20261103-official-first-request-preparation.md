# 官方 EPD 首请求准备：CPU 验证，未运行 GPU

[固定执行说明](../docs/official-first-request.md) · [脚本](../tools/official_epd_first_request.sh) · [CPU原始记录](../validation/official-first-request-cpu-20261103/)

官方运行源码保持 `9b111f710dfb4724072b603d626a1e4dad93ef1f`，本次只准备单次诊断的外部启动/收尾工具，没有修订官方模型或调度代码。工具版本由本页所在结果仓库commit确定，与运行源码SHA分别记录。

| 范围 | 实际状态 |
|---|---|
| Linux进程登记及TERM/KILL、外部进程保护、身份拒绝、自身保护、优化Python拒绝 | 本地WSL真实CPU进程8项通过 |
| observe/ss失败不能继续到请求阶段 | Bash故障注入2项通过；POST仅printf哨兵，无HTTP请求 |
| 独立代码审查 | CPU助手及固定脚本G2 APPROVE，BLOCKING 0 |
| qjh003部署与真实信号行为 | 尚未执行，不能由本地测试代替 |
| 实际模块加载、模型请求、CUDA IPC及GPU释放 | 尚未执行 |
| 吞吐/TTFT/TPOT/E2E对照 | 本次没有测量；历史批次另页展示 |

修前失败完整保留：僵尸environ拒读误判、助手继承run标签后误杀自身、优化Python删除assert保护、Bash条件上下文吞observe/ss失败。对应回归先失败再修正通过。测试不修改真实预约或GPU环境，没有伪造G3通过。

诊断保持三卡E1:P1:D1、MiniCPM-V-2_6、FP16 TP1、单图及128目标输出；600秒准备/就绪、120秒请求、120秒清理、60秒保存，共900秒。收尾子步骤最坏79秒，外层timeout提供失联兜底；目标机实际行为及资源绑定仍须验证。一次buffered HTTP不作为客户端TTFT，实际生成事件与目标长度分开，语义正确性另查图及输出。

明日预约记录为11月4日15–18点，但执行前必须刷新实际窗口、CPU权限、GPU UUID/NUMA/占用、官方SHA及dirty、工具部署SHA、端口和已有任务。此页不是GPU执行批准。不会用本诊断冒充正式矩阵，不改变同三卡baseline/PD/EPD公平测量范围。
