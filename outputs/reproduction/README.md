# SpaceServe / EPD 小规模复现

目标与范围见 `goal.md`，结果与限制见 `report.md`，分项证据见 `report/completion-audit.md`。qjh003 跑 EPD 全矩阵，qjh005 独立复测低、高负载；两台各自比较同机、同三张 GPU 的三个完整模型副本。既有 SpaceServe 4090/L20 数据一并保留。

## 固定版本

| 项目 | 固定版本 |
|---|---|
| SpaceServe | `66de079af4234b27f7f82ff91d238ef1351324ba` |
| SpaceServe 原生基线 | vLLM 0.7.2、PyTorch 2.5.1+cu124、Transformers 4.49.0 |
| libsmctrl | `gofreelee/mysmctrl`，`6ff57356968a3f04158b9273aa881ee6bdf04229` |
| EPDServe | `9b111f710dfb4724072b603d626a1e4dad93ef1f` |
| EPD 原生基线 | vLLM 0.6.1.post2、PyTorch 2.4.0+cu121、Transformers 4.44.2 |
| H20 兼容覆盖 | cuBLAS 12.4.5.8；原 12.1.3.1 的 SIGFPE 有最小复现及 GDB 栈 |
| 模型 | SpaceServe：Qwen2-VL-2B-Instruct；EPD：MiniCPM-V-2_6，均 FP16、TP=1 |

完整依赖、模型逐文件 revision/大小/SHA256 在 `configs/` 及 `evidence/<host>/`。H20 的 cuBLAS 使用显式 `--no-deps` 局部覆盖；PyTorch 元数据声明的旧 cuBLAS 要求与实际覆盖版本不同，未因此升级 PyTorch/vLLM。双方实测使用相同运行库。CUDA Toolkit/驱动、编译命令和实际加载路径均留档。

## H20 重新运行

需要 Linux、Python 3.10 及开发头文件、CUDA Toolkit、NVIDIA 驱动、C++ 编译器、git 和 uv。两台本次均为 CUDA Toolkit 12.8、驱动 580.126.20、8×H20、NVLink；选择 GPU 0/1/2，同 NUMA 域。安装前检查数据盘剩余空间，所有文件放自有实验目录，不终止其他用户任务。

以下在解压后的交付目录执行，`DELIVERY` 指向该目录。使用新的专属父目录，以免覆盖已有数据或占用其他实验的 Ray 短路径；不要直接重跑到已含正式结果的目录。

```bash
export DELIVERY="$PWD"
export EXP_ROOT=/local/boyjiang/r1/epd
mkdir -p "$EXP_ROOT"/{envs,cache,tmp,logs}
python3 -m venv "$EXP_ROOT/envs/tools"
TMPDIR="$EXP_ROOT/tmp" PIP_CACHE_DIR="$EXP_ROOT/cache/pip" \
  "$EXP_ROOT/envs/tools/bin/pip" install uv==0.13.5 \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple
export PATH="$EXP_ROOT/envs/tools/bin:$PATH"
bash "$DELIVERY/scripts/bootstrap.sh" epd "$EXP_ROOT"

# 依次验证 IOMMU 配置、BLAS、原生 embedding、P2P 与 KV；失败即停止。
bash "$EXP_ROOT/scripts/preflight_epd_h20.sh" >"$EXP_ROOT/logs/preflight.log" 2>&1
PREFLIGHT=$(tail -n 1 "$EXP_ROOT/logs/preflight.log")
bash "$EXP_ROOT/scripts/run_epd_h20.sh" "$PREFLIGHT" >"$EXP_ROOT/logs/workflow.log" 2>&1
```

`bootstrap.sh` 在 qjh003/qjh005 自动应用 H20 cuBLAS 覆盖。`fix_h20_cublas.sh` 可单独复现安装和四组 BLAS 验证；只作用于隔离环境。模型按已保存的逐文件版本及哈希下载，不包含在 ZIP 中。固定 COCO 子集由 `data/dataset.tar.gz` 解包。

运行器按hostname选择qjh003的六个负载点或qjh005的两个负载点：先保存完整模型参考，检查EPD首次启动及一次服务重启后的8并发，再运行EPD矩阵、停止本实验服务、启动同三卡三个完整副本测基线，最后按实际缓存分配规模重测原生KV（每次实际传18 blocks，并非遍历全部缓存）。它检查GPU占用、保存PID与实际运行库，只清理本实验进程树。服务仅监听本机回环地址。

本次实际运行用的旧文件名为 `run_epd_qjh003.sh`，脚本快照保存在各主机 `evidence/used-scripts/`。当前 `run_epd_h20.sh` 汇总了同样的测量命令与已单独执行的验收步骤；这个整合版本本轮没有端到端执行过。没有改写 C++ 通信层，也没有跨机 E/P/D 部署。

现行EPD适配器启动时将同manifest的20张图片载入实际RGB缓存，不执行模型前向或新增推理预热。首次归档中单图/C1的三副本缓存初态不一致，后经独立G1/G2审查仅成对补测该点，原数据保留。复现这次定点补测可在已准备好的原专属root执行：

```bash
export EXP_ROOT=/local/boyjiang/spaceserve-epd-qjh003-20261023
# DELIVERY指向解压目录，qjh005使用它自己的专属root；确保本实验服务已停止。
find "$DELIVERY/scripts" -maxdepth 1 -type f -exec cp {} "$EXP_ROOT/scripts/" \;
"$EXP_ROOT/envs/epd/bin/python" "$EXP_ROOT/scripts/apply_epd_compat.py" "$EXP_ROOT"
bash "$EXP_ROOT/scripts/run_cache_fix_h20.sh" >"$EXP_ROOT/logs/cache-fix-workflow.log" 2>&1
```

以上是本次补测的实际命令；脚本拒绝覆盖已有 `results/cache-fix-single-c1-20261023`，重复实验应按前节准备新的专属root，不删除旧结果。它使用同三卡与原20/100×3协议，保存前后RGB像素SHA、API PID、GPU UUID、库路径、标准/C8固定检查及实际源码快照。基线固定正确性检查覆盖首端点；RGB检查及正式请求覆盖全部三个副本。新建的干净全流程root无需再人为制造旧缓存不公平状态。

## 协议与路径

固定 20 张 COCO 图片，RGB 448×448、相同提示词及顺序；每请求 1/4 张图，并发 1/4/8（qjh005 只取 1图/C1、4图/C8）。每配置预热 20 请求，正式 100 请求重复三次，temperature=0、ignore_eos=True、实际输出 128 token IDs。详细 TTFT/TPOT、显存采样和统计口径见报告。

本次机器目录：

| 主机 | 数据盘目录 | 用途 |
|---|---|---|
| qjh003 | `/local/boyjiang/spaceserve-epd-qjh003-20261023` | H20 EPD 全矩阵及三副本基线 |
| qjh005 | `/local/boyjiang/spaceserve-epd-qjh005-20261023` | H20 低/高负载及三副本基线 |
| sapphire1 | `/mnt/data/boyjiang-spaceserve-epd` | 4090 SpaceServe 同卡对照 |
| sapphire3 | `/mnt/data3/boyjiang-spaceserve-epd` | L20 SpaceServe 趋势及旧 EPD 失败诊断 |

归档的 qjh005 矩阵名添加 `-qjh005` 区分主机，原始请求、配置和时间戳不改写。每格 `requests.jsonl` 共 320 行，其中 20 条预热、300 条正式；`summary.json` 是三次重复。矩阵另含 `runtime-config.json`、GPU 采样、独立 `audit.json`、有效性标记 `validity.json` 和测量完成标记。

## 离线审计、汇总与打包

Claude额度耗尽后，用户授权独立subagent接替，实际审查原文及处理记录位于 `reviews/`，当前状态见 `report/experiment-status.json`，逐项核对见 `report/completion-audit.md`。技术脚本的 `passed` 不等于G5批准，最终完成状态必须以真实Gate结论为准。

在包含matplotlib和Pillow的Python环境中，从交付目录执行：

本次离线分析使用专属Python3.12.14环境、Matplotlib3.9.2、NumPy1.26.4、Pillow12.3.0；详细包版本见 `report/analysis-environment.json`，与远端模型推理环境分开。RGB审计会按归档图片重新计算像素SHA，若换Pillow版本导致解码差异，需先解释差异而非跳过断言。

```bash
python scripts/audit_h20.py "$PWD"
python scripts/audit_cache_fix.py "$PWD"
python scripts/audit_cache_continuity.py "$PWD"
python scripts/compare_outputs.py data/raw/sapphire1 data/raw/sapphire3 \
  data/raw/qjh003 data/raw/qjh005 --cache-fix data/cache-fix --output report/output-comparison.json
python scripts/summarize.py data/raw/sapphire1 data/raw/sapphire3 \
  data/raw/qjh003 data/raw/qjh005 --cache-fix data/cache-fix --require-all --output report
python scripts/make_report.py "$PWD"
python scripts/verify_delivery.py "$PWD"
python scripts/package_delivery.py "$PWD" ../reproduction-h20.zip
```

`make_report.py` 按当前解压位置重新生成报告中的绝对图片路径。重新计算审计会更新时间戳，须随后重新生成 SHA256SUMS 和 ZIP。未修改的原始交付可用 `sha256sum -c SHA256SUMS` 检查，ZIP 创建时另做完整 CRC 检查。

`audit_h20.py` 覆盖两台的原生数据校验、运行库/设备/boot ID、固定服务用例和完整负载协议；`verify_delivery.py` 同时检查既有 SpaceServe 机制、原始请求、配对输入和历史失败证据。这些检查不证明任意图片的语义质量或论文规模等价性。

`audit_cache_fix.py` 检查定点补测的实际RGB缓存、来源代码SHA、服务PID、设备与原协议。归档保留50配置/15,000正式请求，最终摘要选择46配置/13,800；其中12,000条为有效测量、1,800条历史L20 EPD仅诊断，另1,200条旧H20低负载被补测替代。`data/cache-fix/`保存四个新配置，原 `data/raw/`不改写逐请求数据；原角色validity的case_overrides仅标记被替代的1图/C1。summary的source_case/source_kind与superseded-summary明确来源，报告和输出配对必须使用相同的 `--cache-fix`。

## SpaceServe 与历史材料

SpaceServe 的准备使用 `bash scripts/bootstrap.sh space "$EXP_ROOT"`。同一张可用卡上，两组均启用专属 MPS：`mps_control.sh start <gpu>`，分别用 `start_server.sh baseline-space|space|space-mask <gpu> <port>` 启动、`run_matrix.sh <label> <gpu> <pid> <url>` 压测，结束后 `stop_server.py <root> <pid>` 和 `mps_control.sh stop` 清理。L20 趋势使用 `VALIDATION_ONLY=1`。本次完整命令、兼容补丁与 CUDA traces 保存在 sapphire 证据及 `report/sapphire-README.md`。

sapphire3 旧 EPD 的 1,800 条记录标为 `diagnostic_only`：独立 CUDA P2P 和原始 KV 操作均出现数据损坏。其原始数据和失败日志保留，不能作为 EPD 加速结论。启动器会拒绝已知不支持的裸机 DMA IOMMU 配置；维护方案仅为历史建议，当前目标使用已验证的 H20。旧 `COMPLETED` 只表示测量结束，不代表通信或性能有效性验收通过。

## 最终审查与归档来源

G1–G4由Claude额度耗尽时接替的独立subagent审查，G5在额度恢复后由Claude审查，均有真实原文与提示词；G5为APPROVE_WITH_NITS、BLOCKING为0。`reviews/g5-closeout-handling.md`逐项回答收尾意见。`reviews/prompts/g5-final-delivery.md`是候选包生成前保存、未执行的subagent草稿；本轮实际G5提示词为 `g5-claude-focused.md`。

`report/h20-final-script-provenance.json`只比较原矩阵17个脚本。补测实际七文件的SHA在 `report/cache-fix-code-manifest.json`，实际执行快照在 `data/cache-fix/<host>/used-scripts/`；`audit_cache_fix.py`读取该manifest逐个校验快照后才生成acceptance，acceptance本身不逐条重复存SHA。两台均通过，G4另独立复核运行时缓存证据。

最终报告的“四个问题”与重复波动限定属于独立审查后的文字补充，不改变统计数值。`make_report.py`可复算主体和刷新本机图片绝对路径；最终文字补充另存 `report/final-editorial-notes.md`，重生成正文时请一并参考。保留绝对路径供本应用预览，换目录后先运行该生成器。

最终ZIP旁保存候选到最终的逐文件差异 `reproduction-h20-differences.json`、完整性输出 `reproduction-h20-integrity.json` 和 `.zip.sha256`。交付内AGENTS快照是在封包前保存；外层ZIP的SHA在打包后追加到原AGENTS及外部最终快照，避免把ZIP自身哈希写进自身内容造成循环。
