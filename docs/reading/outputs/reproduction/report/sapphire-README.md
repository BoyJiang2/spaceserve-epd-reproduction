> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/reproduction/report/sapphire-README.md) SHA256 3b5742b0043e835fcffeb201cbcb72a7780ac1b7b4352acf76033e01d2e97c49。原数字及解释不变。

# SpaceServe / EPD 小规模复现

本目录包含部署、兼容性补丁、正确性检查、压测、CUDA 能力探针和时间线分析脚本。已采集 30 个配置、9,000 条请求和 600 条矩阵内预热，但后续独立测试确认 sapphire3 的 CUDA PCIe P2P 会破坏数据，其八张卡均处于裸机 DMA-FQ IOMMU 域。1,800 条 EPD 记录已降级为诊断数据，不能作为可靠性能结论；其余同卡/独立副本测量保留。完整目标未完成，需管理员维护或更换有效环境，详见 report.md 及 report/host-maintenance-proposal.md。

## 固定版本与机器

| 项目 | 版本 / 配置 |
|---|---|
| SpaceServe | `66de079af4234b27f7f82ff91d238ef1351324ba` |
| SpaceServe 原生基线及 native extensions | vLLM `0.7.2`、PyTorch `2.5.1+cu124`、Transformers `4.49.0` |
| libsmctrl | 作者的 `gofreelee/mysmctrl`，`6ff57356968a3f04158b9273aa881ee6bdf04229` |
| EPDServe | `9b111f710dfb4724072b603d626a1e4dad93ef1f` |
| EPD 原生基线 | vLLM `0.6.1.post2`、PyTorch `2.4.0+cu121`、Transformers `4.44.2` |
| SpaceServe 模型 | Qwen2-VL-2B-Instruct，FP16，TP=1 |
| EPD 模型 | MiniCPM-V-2_6，FP16，E:P:D=1:1:1，TP=1，关闭 IRP 和动态角色切换 |
| sapphire1 | 8×RTX 4090 24GB；实验根目录 `/mnt/data/boyjiang-spaceserve-epd` |
| sapphire3 | 8×L20 48GB；实验根目录 `/mnt/data3/boyjiang-spaceserve-epd` |

论文附录 G 明确使用 vLLM 0.7.2 和 CUDA MPS；已通过官方 GitHub 文件 blob SHA 核对固定分支。初期 0.7.3 的结果归档为诊断数据，不参与正式比较。证据见 `configs/upstream-version-evidence.json`。

完整依赖和模型文件哈希在 `configs/`；模型下载脚本可按保存的逐文件 revision 与 SHA256 重放下载。native extensions 取自相同版本的官方 vLLM wheel，通过符号链接供 fork 使用，不重编译无关 CUDA 内核。

## 运行方法

前提：Linux、Python 3.10、CUDA Toolkit 12.4、NVIDIA 驱动、`uv`、`git`、`make`、C++ 编译器、Python 开发头文件。使用已确认空闲的 GPU；本次没有终止其他用户的任务，也没有清理他人文件。

首次准备环境，例如在 sapphire1：

```bash
export EXP_ROOT=/mnt/data/boyjiang-spaceserve-epd
bash scripts/bootstrap.sh space "$EXP_ROOT"
```

在 sapphire3 准备 EPD：

```bash
export EXP_ROOT=/mnt/data3/boyjiang-spaceserve-epd
bash scripts/bootstrap.sh epd "$EXP_ROOT"
```

`bootstrap.sh` 会检查数据盘空间、检出固定代码、安装锁定依赖、应用补丁、准备模型和解包固定 COCO 子集。全部缓存及临时文件放实验目录；Ray 使用指向实验目录的短路径软链接，避免 Unix socket 路径过长。

SpaceServe 的基线和实验组都启用同一套 MPS 设置，并在同一张物理 GPU 上顺序测试。例如确认 GPU 3 可用后：

```bash
EXP_ROOT="$EXP_ROOT" bash scripts/mps_control.sh start 3
nohup env EXP_ROOT="$EXP_ROOT" REPRO_USE_MPS=1 \
  bash scripts/start_server.sh baseline-space 3 17778 \
  >"$EXP_ROOT/logs/baseline.log" 2>&1 &
SERVER_PID=$!
# 等待 curl -f http://127.0.0.1:17778/health 成功，再启动矩阵。
nohup env EXP_ROOT="$EXP_ROOT" REPRO_USE_MPS=1 \
  bash scripts/run_matrix.sh baseline-space-4090-mps 3 "$SERVER_PID" \
  http://127.0.0.1:17778 >"$EXP_ROOT/logs/matrix-baseline.log" 2>&1 &
MATRIX_PID=$!
nohup env EXP_ROOT="$EXP_ROOT" REPRO_USE_MPS=1 \
  bash scripts/run_sequence.sh space-followup "$MATRIX_PID" "$SERVER_PID" \
  >"$EXP_ROOT/logs/sequence-space.log" 2>&1 &
```

`run_sequence.sh` 仅在前一个矩阵有 `COMPLETED` 标记时继续；随后停止本实验服务，并在同一 GPU 启动 SpaceServe、执行完整矩阵。`stop_server.py` 检查进程 UID 和命令是否属于本实验目录，再停止对应进程树。

全部 SpaceServe 服务结束并确认该私有 MPS 已无客户端后，执行 `EXP_ROOT="$EXP_ROOT" bash scripts/mps_control.sh stop`。本次使用独立 pipe/log 目录，结束时关闭本实验 MPS，不操作其他服务。

EPD 启动方式：

**当前 sapphire3 不满足启动条件。** 先完成以下检查；任一数据校验失败都应停止 EPD，不得以 API 返回成功或拓扑显示支持代替：

```bash
python scripts/check_iommu.py --devices 0,1,2 --require-compatible --output "$EXP_ROOT/results/iommu-platform.json"
CUDA_VISIBLE_DEVICES=0,1 python scripts/probe_cuda_peer_runtime.py --output "$EXP_ROOT/results/peer-0-to-1.json"
CUDA_VISIBLE_DEVICES=1,2 python scripts/probe_cuda_peer_runtime.py --output "$EXP_ROOT/results/peer-1-to-2.json"
SITE="$EXP_ROOT/envs/epd/lib/python3.10/site-packages"
export LD_LIBRARY_PATH="$SITE/torch/lib:$SITE/nvidia/nccl/lib:${LD_LIBRARY_PATH:-}"
"$EXP_ROOT/envs/epd/bin/python" scripts/probe_epd_kv_ipc.py --source 1 --destination 2 \
  --library "$EXP_ROOT/build/epd-cuda/libcuda_ipc_utils.so" --output "$EXP_ROOT/results/native-kv-check.json"
```

实际三卡角色可能由 Ray 分配，因此最终验收应覆盖选定卡的相关方向及重启。早期 `probe_cuda_ipc.py` 只验证 IPC 指针导入后的 D2H 读取，不能替代上述 D2D 数据校验。

通过后才启动服务：

```bash
EXP_ROOT="$EXP_ROOT" bash scripts/start_server.sh epd 0,1,2 18400
```

确认链路可推理后，另一个终端运行：

```bash
EXP_ROOT="$EXP_ROOT" bash scripts/run_matrix.sh epd-l20 0,1,2 <EPD服务PID> \
  http://127.0.0.1:18400
```

`run_sequence.sh epd-followup <矩阵PID> <EPD服务PID>` 等待 EPD 矩阵完成，在原三张 GPU 分别启动完整模型副本，用同样客户端按请求序号轮询三个端口，再跑完整矩阵。单卡完整模型的预检数据不作为三卡吞吐基线。

L20 趋势验证使用 `VALIDATION_ONLY=1`，选择“1 图/并发 1”和“4 图/并发 8”两个点。先跑 `baseline-space-l20-mps`，再通过 `l20-followup` 在同一 GPU 顺序运行 `space`、`space-mask`。

## 数据与指标

- 固定 20 张 COCO val2014 图片，转换 RGB、缩放 448×448、JPEG quality 95。文件、原图哈希和变换后哈希见数据包中的 manifest；参考 captions 同时保存。
- 每请求 1/4 张图；并发 1/4/8；目标 128 output tokens，temperature=0，ignore_eos=true；每配置预热 20 请求，然后测量 100 请求，重复 3 次。
- 每条记录保存图片路径、端点、真实 output token IDs、token 时间戳、处理后输入 IDs、视觉 token 数、失败信息和客户端端到端延迟。
- 固定图像尺寸下，Qwen2-VL 每图 256 个视觉 tokens，MiniCPM 每图 64 个，按实际处理后输入计数。
- TTFT 为服务端首 token 的 `time.perf_counter()` 减客户端发出请求的同机时间，包含请求入口和推理，但不含首 token 的网络返回开销。EPD 原接口最终统一返回 JSON，因此不能把此值称为流式客户端可见 TTFT。
- TPOT 为 `(最后 token 时间 - 首 token 时间)/(实际 output tokens - 1)`；端到端延迟使用客户端完整 HTTP 往返。
- NVML 采样循环每次等待 0.1 秒，另有进程查询开销；实际采样间隔记录在 summary.csv。记录分配 GPU 的物理显存和本实验进程归属，MPS 共享服务进程同样纳入；显存值是采样峰值。
- 采用固定并发闭环测试，不作真实到达率或 SLO attainment 结论。两个系统各自与自己的基线比较。

## 必要修复与机制证据

EPD 修复了 HTTP 多图请求重复第一张图、IRP 参数未传递的问题；按原 README 设置 MiniCPM image processor 的 `trust_remote_code`。返回值增加真实 output token IDs 和处理后输入 IDs，便于检查。

SpaceServe 修复了多图特征缓存被覆盖、进程间 Queue 的上下文及生命周期、编码请求完成后不释放状态，以及释放缓存时修改正在迭代集合的问题。对原生基线与 fork 同时补充 GPU UUID 的 NVML 索引解析，使旧版 vLLM 能按 NVIDIA 建议连接限定 GPU 的 MPS 服务。Profiler 控制同时发给编码与解码进程；性能测量不启用 profiler。

`evidence/` 保存正确性与硬件验证记录。EPD 单图、四图及并发颜色请求的 token IDs 与完整模型一致。SpaceServe 的真实照片并发路由正确，输出与原生基线一致；Qwen2-VL-2B 对纯色图及部分四图描述本身存在错误，保留了基线和目标的原始结果，未据此宣称语义质量全部通过。

当前驱动与库组合下，4090 跨卡 CUDA IPC 返回错误 217，EPD 转 L20；4090 的 libsmctrl 拒绝 CUDA Driver API 13.0，因此该机 SM mask 标为未复现。L20 探针确认 mask 把实际运行 kernel 的 SM 数从 92 降至 68，MPS 下也已实测。固定公开分支仅给编码器应用静态 mask；解码器 mask 被注释，未补写论文完整 SIS/TWSRFT。

在分开的 CUDA trace 中，MPS 下已观测到编码与解码 kernel 的时间重叠。原始 trace、对齐方法和重叠统计均保存；这些短诊断的吞吐不混入正式性能结果。

## 离线重算与验收

在具备 matplotlib 的 Python 环境中，从本目录重算全部指标和图：

```bash
python scripts/summarize.py data/raw/sapphire1 data/raw/sapphire3 --output report --require-all
python scripts/compare_outputs.py data/raw/sapphire1 data/raw/sapphire3 --output report/output-comparison.json
python scripts/make_report.py report/summary.json --comparison report/output-comparison.json \
  --artifact-root "$(pwd)" --output report.md
python scripts/verify_delivery.py .
```

最后一步只用 Python 标准库，检查 7 个矩阵、30 个配置、9,000 条已采集请求、600 条矩阵内预热、44 个服务级对照样例及失败证据，生成 `report/delivery-audit.json`。它只审计材料完整性，**不表示 EPD 验收通过**；实际有效性另见 `validity.json`、CSV 的 `result_validity` 和 `report/experiment-status.json`。EPD 的冷、暖 8 并发检查均超时，独立纯 CUDA 与原始 KV 传输均校验失败。正式请求的输入/输出差异索引保留在 `output-comparison.json`，无需再次调用 GPU。

`patches/README.md` 列出最终源码及依赖补丁；evidence 中的调试阶段补丁仅用于追溯。模型权重和环境目录留在各主机专属数据盘，不放入交付包；固定图片子集、逐文件模型下载清单、依赖锁定和原始结果均随包保存。

## 来源

- [SpaceServe 论文](https://papers.nips.cc/paper_files/paper/2025/file/720e7ebc49c84252abc0754dddf80976-Paper-Conference.pdf)、[官方代码](https://github.com/gofreelee/SpaceServe)
- [EPD Disaggregation 论文](https://proceedings.mlr.press/v267/singh25d.html)、[官方代码](https://github.com/vbdi/epdserve)
- [NVIDIA MPS 环境变量及 GPU UUID 说明](https://docs.nvidia.com/deploy/mps/latest/appendix-environment-variables.html)
