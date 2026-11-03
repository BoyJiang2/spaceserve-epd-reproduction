# SpaceServe 单请求工具准备：目标CPU通过，未运行GPU

[执行说明](../docs/official-first-request.md) · [固定脚本](../tools/official_space_first_request.sh) · [CPU原件](../validation/official-first-request-cpu-20261103/)

为不改变EPD已部署工具，Space使用独立绑定自身root/run前缀的收尾助手，沿用同一已审生命周期逻辑；没有引入新服务框架或改动官方模型代码。

| 范围 | 真实结果 |
|---|---|
| 本地Linux CPU进程身份/TERM/KILL/外部fixture保护 | 8项通过 |
| Bash observe/ss失败阻止后续请求 | 2项通过 |
| OpenAI响应解析 | 3项合成CPU fixture通过，不是真实HTTP结果 |
| Bash语法/嵌入Python AST | 通过 |
| 独立G1本地准备/G2 | APPROVE / BLOCKING 0 |
| qjh003部署/CPU工具 | 四文件23394B SHA一致；13项8.533秒及bash-n通过，SSH exit0 |
| 实际模型/GPU/SM效果 | 未执行 |

SOURCE_ROLE只选择固定native内容基点d7ec或fork66de，不自动切分支；单H20、显式half/TP1、V1/eager、NUMA0 CPU0–89 OMP4沿用已批准配置。固定单图、greedy/128目标输出、一次buffered chat请求，真实tokens用API usage记录；TTFT和视觉token数未采集则明确为空，语义/机制标为待验证。

fork是官方默认库自动mask行为，不冒称已实现“无mask”或“有效mask”实验组；不启动或停止MPS，不用单请求证明计算重叠。900秒诊断预算及精确收尾沿用已审方案；此页不是当前GPU/服务器执行批准。完整性能及三组机制验证仍未完成。

目标机[完整stdout](../validation/official-first-request-cpu-20261103/qjh003-stdout.jsonl)、[退出码](../validation/official-first-request-cpu-20261103/qjh003-exit.json)及[独立CPU子验收](../validation/official-first-request-cpu-20261103/qjh003-cpu-review.md)已保存。仅部署到既有/local/boyjiang/spaceserve/assets，未新建目录/环境或复制权重；未执行主脚本/真实HTTP/GPU，不能把13项CPU检查称作模型正确性或SM通过。
