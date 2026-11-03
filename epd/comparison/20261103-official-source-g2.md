# EPDServe：实际vLLM API静态核查（2026-11-03）

本页是官方checkout的G2准备证据：未改源码、未导入目标包、未加载模型、未发请求。当前仍为官方9b111f710dfb4724072b603d626a1e4dad93ef1f、adapt/qjh003-v1、clean。此前旧repo的运行结果独立保留。

## 按实际依赖核调用

读取了官方worker/config/orchestrator及实际环境中vLLM0.6.1.post2的ModelRunner、分布式worker、MiniCPMV和Qwen2实现。没有机械比较EPD与Space两种不同架构。

- init_worker_distributed_environment、ModelRunner构造、load_model、prepare_model_input和两处execute_model的6个显式调用，其参数形状可绑定实际安装源码的函数签名。
- MiniCPM目标路径另核Qwen2Model.forward、compute_logits、sample、_get_image_bounds、_parse_and_validate_inputs、get_vision_hidden_states，6处形状可绑定。带**kwargs的实际内容未检查；embedding张量、配置对象默认值、CUDA执行与采样均未验证。
- 绑定使用标准库AST和inspect.Signature，未执行目标模块、decorator或函数体。这不是API运行兼容或模型正确性结论，调用数量不是完成标准。
- 实际依赖get_image_processor的trust_remote_code默认True，与官方README要求一致。本轮没有再次修改环境，也不声称安装文件等于未改动的官方wheel。

## 资产与当前风险

现有IPC库/local/boyjiang/epd/assets/build/libcuda_ipc_utils.so为398920B ELF；已安装vLLM _C为260143568B ELF。只读取文件元数据，没有复制、dlopen或执行。模型config存在且SHA已记录，config JSON没有scale_emb不意味着加载后的配置对象没有默认属性。

官方checkout本身带示例图片，不自动继承旧repo“缺sample”修复。身份、地址、通信或调度旧补丁亦未迁入。当前没有真实入口失败，不能为了凑适配commit而预改源码。

[调用、路径、签名和配置指纹证据](../data/official-g2-static-20261103.json)。原始source快照、命令stdout/stderr/exit保留在本地；公开记录省略源文件base64正文和预约详情。

下一步在合法三卡窗口使用现有环境/权重/IPC库，沿官方在线入口E:P:D=1:1:1执行单个真实图片请求。保持MiniCPM-V-2_6 FP16 TP1；可能触发CUDA的import/--help也放在该窗口。遇第一处实际错误即保留原始输出，按当前官方源码做最小适配。无需先通过native36/selected或整批长预算。

真实请求、重启并发、embedding/KV传输和三卡公平性能仍未完成。本页没有新增吞吐、TTFT或GPU结论。
