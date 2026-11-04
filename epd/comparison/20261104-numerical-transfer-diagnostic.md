# EPD embedding / KV 数值传输诊断（2026-11-04）

现有 CUDA IPC 二进制的两条复制路径，在本次**显式同步、禁 CUDA 缓存的小张量诊断**中逐元素正确；不是模型异步通信或性能的完整证明。

| 路径 | FP16 布局 | 非恒等块映射 | 全张量不一致元素数 | 退出 |
|---|---|---|---:|---|
| E → P embedding | [5,3,8] | src [4,1,3] → dst [0,4,2] | 0 | E/P 均0 |
| P → D KV | [layers=2,K/V=2,blocks=5,block_size=3,heads=2,head_dim=4] | 同上 | 0 | P/D 均0 |

CPU期望张量从独立整数序列构造，FP16可精确表示；未写块保留-2048 sentinel，比较覆盖完整目标张量，包含未写区域。生产者保留源存储直至消费者退出。D先关闭KV IPC并退出，随后P、最后E退出。目标初始化、生产完成与接收完成均显式同步。

## 来源与实际运行

- 官方源码基线 `9b111f710dfb4724072b603d626a1e4dad93ef1f`，适配 `06fbcb6f3f3b931950077077c9a040e9c238deee`；本次未改官方C++源码。
- [诊断脚本](../tools/official_transfer_numeric.py)发布于 `a93f4def7979a73f92c2ab7942fe01e1ae18e199`，8282B，SHA256 `f82911cbed5b0b01dbba8ef36fc4b265debd1b855293f60ec1bca940fc6c9e6c`。
- 解释器为既有EPD环境，torch 2.4.0+cu121。实际库 `/local/boyjiang/epd/assets/build/libcuda_ipc_utils.so`，SHA256 `fdb86ae5a5658d17c98cc8cc17e3b0d911433bf270fb8bcfbb381a99f66a970e`。**该二进制的完整构建来源仍未闭合**，不能把源码接口核对当作二进制来源验证。
- 三个spawn进程分别选择CUDA ordinal 0/1/2；NVML采样捕获E/P的PID→物理UUID，D生命周期较短未被采中，不宣称D的NVML UUID直接证据齐全。记录的设备属性均为H20。父进程退出0，三个child退出0，末次NVML八卡显存0、compute apps空。
- 未记录指针及storage offset，不声称这些已实测；未用有限NVML采样推连续峰值或计算重叠。

## 原件与复跑

- [embedding 结果](../validation/official-transfer-numeric-20261104/n1/embedding.json)、[KV 结果](../validation/official-transfer-numeric-20261104/n1/kv.json)、[三子进程终态](../validation/official-transfer-numeric-20261104/n1/terminal.json)、[父退出和NVML原始观察](../validation/official-transfer-numeric-20261104/n1/numeric-n1-outer.json)。各目录保留独立stdout/stderr、环境身份和SHA。
- [服务器完整原件清单](../validation/official-transfer-numeric-20261104/n1/server-manifest.json)、[独立G1/G2及原失败](../validation/official-transfer-numeric-20261104/independent-g1-g2.md)、[数值诊断G3/G4](../validation/official-transfer-numeric-20261104/n1/independent-g3-g4.md)。公开原件逐字保留；spawn/预约身份原件留服务器，清单列完整SHA，不把清单当作上传证明。

在已核本人资源的窗口，先核源码、脚本、二进制、设备UUID及占用，确认360秒单元余量，再在既有服务器目录运行：

```bash
CUDA_VISIBLE_DEVICES=0,1,2 PYTORCH_NO_CUDA_MEMORY_CACHING=1 OMP_NUM_THREADS=4 \
  taskset -c 0-89 nice -n 10 /local/boyjiang/epd/assets/envs/epd/bin/python \
  /local/boyjiang/epd/assets/build/official_transfer_numeric.py \
  /local/boyjiang/epd/runs/NEW_UNIQUE_RUN
```

run必须不存在，避免覆盖历史；保存父stdout/stderr、实际退出码及GPU前后状态，不能只凭terminal marker验收。无需模型、Ray或MPS。

本次不证明原模型缓存分配、异步调度与多请求KV语义，不说明此前错误已穷尽，也不测量吞吐、TTFT或通信性能。正式公平性能对照仍未完成。[不同图片C4模型诊断](20261104-distinct-image-c4-diagnostic.md)与本批独立，不互相替代。
