> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/reproduction/patches/README.md) SHA256 1a82ef041dbb4246afadb91c17baae6412361c86aa8aa58cf8c12ec9abe8dad9。原数字及解释不变。

# 补丁清单

推荐用 `scripts/bootstrap.sh` 和配套的幂等补丁脚本重放。下列文件是最终改动的可审阅快照；不要把 evidence 中不同调试阶段的增量补丁全部叠加应用。

| 补丁 | 应用位置 | 目的 |
|---|---|---|
| space-complete.patch | SpaceServe 固定提交 | 多图特征缓存、编码状态释放、Queue 生命周期、GPU UUID 解析和双进程 profiler 控制 |
| epd-complete.patch | EPDServe 固定提交；历史首轮版本 | 分别加载各张图、传递 IRP 开关、返回实际 token IDs；不含后续RGB修正 |
| epd-h20-cache-fixed.patch | EPDServe 固定提交；H20最终合并版本 | 包含历史兼容修改和实际RGB缓存预载/只读证据接口；替代上一行，不叠加应用 |
| vllm-0.7.2-cuda-uuid.patch | SpaceServe 环境安装的原生 vLLM 包 | 与 fork 相同的 GPU UUID 解析；双方以相同方式连接 MPS |
| vllm-0.6.1-image-processor-trust.patch | EPD 环境安装的原生 vLLM 包 | 按模型与官方 README 要求启用 MiniCPM 图像处理器 remote code |

SpaceServe 的完整源码补丁已经包含 UUID 修改。EPD 仓库跟踪了 Python bytecode，运行时会改变这些文件；这里仅保存实际 Python 源码改动，不把生成的 bytecode 当作实现补丁。

没有改写 CUDA IPC、KV 传输或调度算法。SpaceServe 的 native extensions 链接到官方 vLLM 0.7.2 wheel，实际链接文件和 SHA256 记录在两个主机的 `native-extensions-manifest.json`。

H20最终补丁来自qjh003实际补测归档的合并diff；适配器还依赖交付的 `scripts/rgb_cache.py` 及 `REPRO_RGB_MANIFEST`。推荐通过bootstrap和apply_epd_compat脚本安装，确保启动器同时设置PYTHONPATH与manifest；不要单独套用diff后省略这些运行依赖。所有20图预载仅解码RGB，不执行模型前向，不生成embedding或KV。
