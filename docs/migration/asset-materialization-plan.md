# qjh003 原始资产物化

两个固定代码目录已实际部署 a3f03b9dd5956db92add454f9b3afd5663f84609，并通过独立代码部署审查。该结论不代表环境、CPU套件或GPU机制通过。

本阶段只将旧项目资产复制到长期项目资产目录，不改旧源、不删除、不安装、不加载模型或CUDA库。代码仍冻结于a3f；辅助工具单独记录其实际push commit和原始SHA，三端执行字节一致。没有新增GPU预算或实验配置变化。

源根为 `/local/boyjiang/spaceserve-epd-qjh003-20261023`。每个单元独立启动、重新核验实际本人CPU票、主机/UID/boot/CPU50/nice10、a3f代码与实际占用。不得将旧票或本地锁作为预约权。预约21:00至次日09:00，结束前120秒停止；不用qjh000旧预约。

| 单元 | 旧源相对位置 | 新目标 |
|---|---|---|
| data | dataset | spaceserve/assets/dataset 和 epd/assets/dataset |
| data | build/epd-cuda/libcuda_ipc_utils.so | epd/assets/build/epd-cuda/libcuda_ipc_utils.so |
| env | envs/epd | epd/assets/envs/epd |
| model | models/MiniCPM-V-2_6 | epd/assets/models/MiniCPM-V-2_6 |

每个单元上限900秒，另留120秒收口；API证明超过300秒即停止，不据900秒上限扩大证明有效期。每单元资产预算30GiB，实际可用空间至少源大小加2GiB。源前、源后、目标完整清单包含目录、隐藏文件、缓存、类型、权限、bytes、SHA256和链接文本；每次哈希与复制受时限约束。目标排他创建，失败保留partial及原始终态，不自动重试或覆盖。

环境只允许原盘点的四个精确链接：lib64→lib、bin/python→/usr/bin/python3、bin/python3→python、bin/python3.10→python。只保留系统Python链接，不复制系统Python，不接受其他外部链接、foreign owner或特殊文件。目录祖先和证据路径均检查真实归属。进程cwd筛查遇同UID不可确认则停止；该筛查不冒称完整FD/maps引用审计。此阶段不删除或改动源，因此完整引用审计留给后续清理验收。

成功状态严格为 **ASSET_BYTES_COPIED_RELOCATION_PENDING**。不改shebang、.pth或IPC RUNPATH；原库仍含旧绝对路径，须后续单独审查最小重定位及实际依赖验证。仍未准备Space专用Torch2.5.1/vLLM0.7.2环境及Qwen7B完整权重，不用EPD环境替代。native36/selected360未接齐的拒绝路径保持。

先独立G2，再本机Windows工作目录临时文件CPU-MOCK测试；它只验证复制、哈希、拒绝覆盖、变更检测、预算/时限和路径/权限负例，不是实际POSIX信号、目标套件、资产运行或GPU机制证据。G3-tool/G5后commit/push，远端wrapper逐字节核Git对象与工具SHA，再按每个实际单元准入执行。原始claim、完整清单、失败及终态下载后核SHA并独立审查，才能称字节迁移完成。
