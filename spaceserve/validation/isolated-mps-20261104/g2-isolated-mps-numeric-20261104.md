# 隔离MPS数值诊断G2

独立审查者subagent /root/official_epd_runtime_review_1104，2026-11-04。主执行者转送10015B精确源码执行逻辑（身份/共享deadline/RPC/两client/安全清理）、系统控制器help与CPU五项实际回执；没有MPS/GPU执行。精确源SHA256 c64ebacf74a63f4d9589778e58c83f8a0b3d9d8ba763d8bc0987c0c94e14bbd2。

审查返回原文：

G2 **条件式 APPROVE / BLOCKING 0**，限所列 `c64ebacf…` 版本的隔离MPS两client数值诊断，不含模型或Nsight。

代码范围与G1一致：独占pipe、UUID限制、真实membership核查、仅自有child信号收口，以及未知服务／客户端时拒绝quit，均未放松身份边界。CPU fixture不作为MPS可用性证明。

派发前还须闭合：

- 只读清点旧MPS control/server；独占pipe为空不等于整机没有旧daemon，无法排除目标GPU冲突时不启动，也不quit旧服务。
- 实际env必须包含identity所核的同名 `EXP_ROOT`、`REPRO_RUN_ID`、`CUDA_MPS_PIPE_DIRECTORY` 三字段。
- 精确版本发布核同及fresh资源／360秒余量成立。任何cleanup_error都不能继续模型或Nsight；保留现场身份与日志，按实际原因收口，不声明释放成功。
- RPC超时若未保存部分stdout/stderr，应明确缺失，不能称每次RPC日志完整。

成功时也只批准两client经该自有MPS server完成数值操作及相应释放。controller退出和显存0不应自动写成所有server PID均已证实消失，未测部分需保留限制。

本审查依据转送代码与CPU回执，未独立读取或重算SHA；未批准直接跳过上述条件执行GPU。
