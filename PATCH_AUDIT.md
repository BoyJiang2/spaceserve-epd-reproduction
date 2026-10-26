# 实际补丁与依赖审计

这是代码路径审计，不是“没有性能影响”的保证。正确性、缓存和进程生命周期修复可以改变执行路径；未改CUDA IPC或调度算法不能推出对所有组无偏。固定上游与许可见[来源说明](THIRD_PARTY_NOTICES.md)。

| 入口与适用批次 | 改动及性能相关性 | 应用关系与核查范围 |
|---|---|---|
| [历史space-complete](outputs/reproduction/patches/space-complete.patch)，4090/L20、2B | UUID、cache字典、完成状态/释放、spawn队列持有及profiler控制；可能改变正确性、内存、进程行为 | 历史快照；不能作为最新7B唯一审计对象 |
| [最新Space累计diff](outputs/qjh000-migration/results/patches/SpaceServe-complete.patch)，H20/7B | 同类兼容/正确性修复，加REPRO_SM_PROBE条件探针、模型驻留记录、with_stack=False；SM探针只用于机制验证 | 相对固定fork的累计补丁，不与分项重复叠加；不能仅凭探针环境变量声明正式无扰动，需对照保存runtime |
| [分项目录](outputs/qjh000-migration/results/patches)及[scripts](outputs/qjh000-migration/scripts) | 分项cache/Queue与累计对应；device-record、service-stream-probe记录实际GPU/stream；安装/启动脚本控制PYTHONPATH、模型与MPS | apply_space_compat、install_device_record、install_service_probe及实际used-scripts共同组成运行路径，不只检查patch文件 |
| [历史epd-complete](outputs/reproduction/patches/epd-complete.patch) | 修复多图反复读首图；传递IRP开关；输出token/input IDs；可能改变计算输入与接口工作量 | 不含后续RGB缓存公平修复，不能当H20最终版本 |
| [H20 cache-fixed](outputs/reproduction/patches/epd-h20-cache-fixed.patch) | 合并历史改动，预载20图RGB、增加只读缓存证据路由；改变首次请求缓存状态 | 替代epd-complete，依赖rgb_cache.py、manifest/PYTHONPATH；只预载RGB，不预计算embedding/KV。基线有对应预载，最终选用补测与旧替代记录见报告 |
| [vLLM UUID](outputs/reproduction/patches/vllm-0.7.2-cuda-uuid.patch)与[图像processor trust](outputs/reproduction/patches/vllm-0.6.1-image-processor-trust.patch) | 设备解析与模型处理器加载；运行前提变化，不推定对性能绝对无影响 | 分别用于原生0.7.2与EPD基线0.6.1系列；不把已在fork累计中的UUID再叠加 |
| [方案A instrumentation](outputs/epd-profile-a/instrumentation.patch)及[instrument.py](outputs/epd-profile-a/scripts/instrument.py) | worker/engine/API的NVTX、request/batch关联、采集控制、disconnect范围；刻意增加可观测性和开销 | 专用源码副本，配套observe/control与baseline_server；off/on来自同副本的条件分支，off不等于未经修改的上游二进制 |
| [API/启动/压测](outputs/epd-profile-a/scripts)与[最新Space实际脚本](outputs/qjh000-migration/results/formal/used-scripts) | 图像处理、采样、请求路由、时间戳和RGB缓存同样影响比较 | 按batch实际版本核对；start_server/benchmark不同于原论文服务协议，不视为透明适配 |

这些修复未新增论文完整SIS/TWSRFT、未重写EPD CUDA IPC/KV传输算法；不代表已隔离每个修复的性能贡献。原回归、输入ID、输出差异、RGB补测及on/off数据分别验证其有限范围，不能互相代替。EPD旧on/off仅验证观测流程差异，不是所有正确性修复的消融。

清单列出的32项补丁/入口文件的大小/SHA由[审计清单](docs/revision/patch-sources.json)绑定；表中目录链接用于导航，不表示已独立逐项审计目录中的每份文件。原patch、源码快照、测量数据不因本次审计改写。
