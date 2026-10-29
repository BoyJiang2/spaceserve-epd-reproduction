# EPD迁移：原始资产已到位，运行重定位待完成

本页是qjh003新固定目录的迁移状态，**不是EPD/PD新性能结果或GPU通过**。历史同三卡三副本baseline对照仍在[EPD项目](../README.md)与[comparison](../comparison/README.md)。

固定根为`/local/boyjiang/epd/{repo,assets,runs,staging,archives}`。代码部署实际HEAD为`a3f03b9dd5956db92add454f9b3afd5663f84609`；原始env、MiniCPM、数据及IPC共23,080,280,259字节已按原SHA迁移，旧源保留。SpaceServe先完成本窗机制预检，释放后才执行一次本页只读CPU静态盘点。

| 实际静态事实 | 结论边界 |
|---|---|
| nested IPC359096字节/SHA12e4145134ba1697bb745fd51c37a8f275293284d6152c17b42513dd6d07ca20 | 库字节已到位；没有dlopen/CUDA执行 |
| `assets/build/libcuda_ipc_utils.so`不存在 | 预期运行路径尚缺 |
| ELF RUNPATH仍含旧实验根 | 尚待最小重定位与真实加载验证 |
| 51个console shebang仍为旧前缀 | 不称环境完整可复跑 |
| Python链接到系统3.10；patchelf存在 | 只读元数据与which，未执行修复 |

[实际stdout及原始argv/输入/exit](raw/)与[独立实际结果审查](epd-static-inventory-actual-review.md)保留。工具段0.0132317秒不含SSH/预约查询；原生Python `-I -S -B`、CPU50/nice10、60秒工作＋30秒收口，未导入Torch、未查询/初始化GPU、未运行模型或通信。source工具位于commit `ae7ede016191e68a7b933ec7470f6061d7dc4021`，工具SHA665e1ca755f624b8b132e6a48292c5da082f3f4731bfd047c36f2b48405b0324；它不改变EPD runtime实际a3f来源。

程序偏差须保留：计划在执行前API核远端源码，gh缺失使该步失败，但PowerShell继续启动。launcher自身已核pushed main与精确Git blob；执行后GitHub connector核了相同原字节。**后验不能补作事前验收**，这项偏差不因静态exit0消失。独立审查APPROVE_WITH_NITS/BLOCKING0仅认可静态事实，未重跑。

下一步应先审查最小重定位，再逐项验证运行依赖；native36及selected360 producer尚未接齐，不是GPU就绪；公平PD完整预算/角色分配必须另在足够有效预约中执行。当前没有EPD新模型请求或新吞吐/TTFT/TPOT/E2E数据，不复用旧PASS充当新批次结果。
