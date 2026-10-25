# EPD 后续执行需要的主机条件

当前未满足完整目标。SpaceServe 的同卡实验不受这个跨卡问题影响；EPD 暂停进一步性能结论，等待可验证的数据传输环境。

已确认的证据：

- sapphire3 是裸机，八张 L20 的 IOMMU domain 均为 `DMA-FQ`。
- 不依赖 PyTorch、Ray、EPD 的 CUDA Runtime 测试中，`cudaDeviceCanAccessPeer` 返回 true，源数据校验通过，但 1 MiB `cudaMemcpyPeer` 后的目标数据与源数据不一致，目标前缀为 `ff`。
- 使用原仓库 KV 操作拷贝约 16 MiB，CPU 提交约 2 ms，GPU 实际完成约 59 秒，且数据校验失败。缓存池缩到 2048 blocks 后仍失败。
- 早期 64 KiB 探针只验证了导入指针后 D2H 读取，不能证明跨 GPU D2D DMA 正确。

因此已将故障缩小到 CUDA PCIe P2P 层；IOMMU 是已确认的不支持配置，但最终因果仍需在关闭 DMA 翻译后重测确认。NVIDIA 明确说明，Linux 裸机下 CUDA PCIe P2P 不支持启用 IOMMU，可能静默破坏设备内存。[CUDA 12.4 文档](https://docs.nvidia.com/cuda/archive/12.4.1/pdf/CUDA_C_Programming_Guide.pdf)、[NCCL 故障排查](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/troubleshooting/gpu_troubleshooting.html)。

建议由用户选择以下一种路径：

1. **管理员维护 sapphire3**：在协调好共享主机用户后，先以临时内核启动参数 `intel_iommu=off` 测试；确认后再由管理员决定是否永久写入 GRUB/BIOS。目前主机 `GRUB_CMDLINE_LINUX_DEFAULT` 和 `GRUB_CMDLINE_LINUX` 均为空。持久化修改应保留原参数，并由管理员执行 `update-grub` 和重启。
2. **换到已验证的 GPU 主机**：提供至少三张 GPU，并先通过 CUDA Runtime P2P 与原始 KV 传输的数据校验，再迁移固定环境和模型。

我尚未修改 GRUB、BIOS、驱动、ACS 或 IOMMU，也未重启主机。用户原计划要求“不终止他人任务”；重启共享主机会中断其他用户，因此必须由用户与管理员安排维护，不能作为当前实验的普通安装步骤执行。

维护或换机后的验收顺序：

1. 记录新 boot ID、GPU UUID 与 IOMMU 域；GPU 不应仍处于 DMA 翻译域。
2. 三张选定卡的相关方向均执行纯 CUDA P2P 校验，必须源、目标完整哈希相同；不能以 API 返回成功或拓扑支持代替。
3. 原始 KV 操作在 2048 和 24728 blocks 两种缓存形状上测 GPU 完成时间，连续重复并校验每个复制块。
4. EPD 冷启动与重启后的单请求、8 并发路由检查均通过。
5. 在同一次主机启动状态下，重跑 EPD 与三副本基线的完整矩阵，替换当前不能作为可靠性能结论的数据；旧记录保留为失败诊断。
