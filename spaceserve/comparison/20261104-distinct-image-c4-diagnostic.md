# SpaceServe 不同图片 C4：原生与跳过 encoder mask 的解耦路径

2026-11-04，在同一张 H20 上串行启动两组新服务，分别提交四个不同图片的单图请求。本次每组4/4成功、各128输出tokens；逐索引请求字节与生成正文均完全相同，未观察到串图或串响应。**这是小并发正确性诊断，不是正式性能矩阵。**

| 项目 | 原生 vLLM c4n | 官方解耦 c4f2 |
|---|---|---|
| 源码 | baseline/vllm-v0.7.2 / d7ec548300d7950c1305231b2aaf970bab7569c1 | 官方固定66de079af4234b27f7f82ff91d238ef1351324ba |
| 来源边界 | tree9887287659a56df6f9744e631667f67893512b8c与官方0408efc相同，commit不同 | 本批无新增适配源码修改 |
| 资源与模型 | 单H20、Qwen2-VL-7B、FP16、TP1、eager、CPU0–89/OMP4 | 同左 |
| 请求 | C4；COCO328/400/623/1146各1张；greedy/ignore_eos/128 | 相同输入字节与设置 |
| 结果 | 4/4 HTTP200；client/work/cleanup/outer均0 | 同左 |
| 终态 | GPU UUID6186…显存0、已登记run进程无存活 | 同左 |
| mask | 原生参考 | 本次日志明确跳过encoder SM划分 |

四图主体分别为长椅上的军装人物、船上的狗、抱大玩具熊的女子、黑衣绿领带戴眼镜男子；两组都对应输入。输出中的截断和尾部多余换行原样保留。输出一致是本固定案例的观察，不是所有输入的等价性证明。

## 逐请求客户端耗时

| 索引 | 原生 client E2E/s | 解耦 client E2E/s | 请求与输出相同 |
|---|---:|---:|---|
| 0 | 3.4971 | 3.2614 | 是 |
| 1 | 3.5099 | 3.2603 | 是 |
| 2 | 3.5098 | 3.2736 | 是 |
| 3 | 3.5097 | 3.3061 | 是 |

成功请求的E2E截至完整JSON响应读完；失败记录则是到客户端异常结束的尝试时长。非流式接口的TTFT、TPOT及视觉tokens未采集，保持null。metrics_complete仅表示有限client E2E记录有效。

这四个请求来自新服务、没有显式预热；OS/JIT等缓存未清空，不能称所有缓存冷态。没有100请求×3重复或平衡运行顺序，不推正式吞吐、加速比或显著收益；HTTP inflight4也不证明GPU计算重叠。

## 保留的入口失败与机制边界

两组之间的c4f在CPU端口bind检查报Errno98、outer exit1，尚未导入模型或进入请求；没有identity/terminal，不伪造其模型或清理结论。此前ss无LISTEN不是端口预约，不据后续无占用猜定TIME_WAIT原因。原失败保留，使用已审PORT参数改为19262后独立运行c4f2，不修改或覆盖失败目录。

c4f2实际原日志为：libsmctrl is unavailable; skipping encoder SM partitioning。只能称“跳过encoder mask的解耦路径”；不是有效mask组，也未证明decoder互斥分区、完整stream配置或实际计算重叠。[此前mask数值失败及版本限制](20261104-native-vs-official-disagg.md)独立保留。

## 角色设备放置补证

随后离线核对原日志与原NVML记录：EngineCore PID2645128和EncoderProcess PID2646390分别有14和4个采样点，均对应物理UUID GPU-6186aa04-e2e2-84c4-0c50-a8d1bb260e32。同一采样时刻两者分别驻留74824MiB与2538MiB。它们的设备放置已有直接证据；有限采样不证明连续峰值，更不证明同时执行计算。

[角色日志与NVML匹配选样](../validation/official-c4-20261104/c4f2/role-placement-samples.json)是事后派生证据，原manifest作为采集当时快照保持不变；新文件发布SHA单列。[独立补审](../validation/official-c4-20261104/placement-and-delivery-review.md)认可此有限范围。

## 数据与复跑

- [逐图输入指纹及完整输出配对](../validation/official-c4-20261104/paired-comparison.json)
- [原生逐请求记录](../validation/official-c4-20261104/c4n/batch-result.json)、[解耦逐请求记录](../validation/official-c4-20261104/c4f2/batch-result.json)；对应目录包含逐请求intent/response/record原件、实际终态、模块来源和清理输出。
- [原生完整原件清单](../validation/official-c4-20261104/c4n/server-manifest.json)、[解耦清单](../validation/official-c4-20261104/c4f2/server-manifest.json)、[失败入口](../validation/official-c4-20261104/c4f/outer.stderr)。带base64图片的完整请求及完整日志保留于清单所列服务器路径；公开输入SHA与客户端可重建请求，未将完整请求重复下载到本地。selected-log-lines是派生选样，发布清单另标其SHA，不冒充完整日志。
- [启动脚本](../tools/official_space_c4.sh)、[客户端](../tools/official_space_c4_client.py)、[独立超时收口](../tools/official_space_c4_finalize.py)、[CPU回归](../tools/test_official_space_c4_cpu.py)、[独立G2](../validation/official-c4-20261104/independent-g2.md)、[G3/G4](../validation/official-c4-20261104/independent-g3-g4.md)。工具版本a64ab10ee7e5383ab848aa3411bf88983fead811。

复跑前核本人有效窗口、空闲设备UUID、源码/工具SHA及端口；每单元预留900秒，设置脚本要求的BOOK_START_EPOCH/BOOK_END_EPOCH/UNIT_START_EPOCH、GPU_IDS、PORT、RUN、HELPER与SOURCE_ROLE后执行bash。RUN是新的独立小运行目录；只在前组已停止释放、工作区clean时切换既有基线/适配分支。无需新checkout、环境、权重或MPS。完整大日志本轮未上传Release，不把原件清单当作下载链接。

正式原生/解耦/有效encoder mask三组对照仍未完成。下一步需直接采集计算时间线、解决或明确mask支持边界，并在有效长窗口完成冻结正式协议。
