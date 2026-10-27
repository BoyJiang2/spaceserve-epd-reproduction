# 本批实际补丁及CPU复跑核验

这些补丁恢复本批已运行的源码路径，不代表已隔离每个修复的性能贡献，也不是新的GPU实验。

| 对象 | 基础版本 | 应用文件 | 核验 |
|---|---|---|---|
| SpaceServe fork | `66de079af4234b27f7f82ff91d238ef1351324ba` | [SpaceServe-complete.patch](SpaceServe-complete.patch) | 官方提交实际`git apply --check`及apply通过，六个改动文件LF SHA均与实际部署清单一致 |
| 原生vLLM CUDA设备解析 | `v0.7.2` | [baseline-cuda-uuid.patch](baseline-cuda-uuid.patch) | 官方tag文件实际apply，LF SHA匹配本批原生环境清单 |
| 原生vLLM启动设备记录 | `v0.7.2` | [native-device-record.patch](native-device-record.patch) | 官方tag文件实际apply，LF字节匹配本批原生worker快照 |

fork累计补丁是旧批累计补丁的原字节副本，本批复核它仍完整匹配实际源码；**不要再叠加旧分项补丁**。累计修改包括UUID、多图特征缓存、编码状态释放、Queue生命周期、设备记录和条件SM探针，能够影响实际执行路径，不能称全部无偏或只改日志。native的两份补丁应用到原生wheel源码，不应用到fork；fork已含对应UUID及设备记录。

核验回执：[fork六文件](../evidence/fork-patch-replay-CPU.json)、[原生worker](../evidence/native-patch-replay-CPU.json)、[原生UUID](../evidence/native-UUID-patch-replay-CPU.json)。完整文件版本及SHA见[实际复制清单](../configs/relocated-inputs.json)，实际服务所用两个fork文件和native worker快照见[源码证据](../evidence/integration-source)。比较时明确按LF规范化；未把Windows CRLF误报为语义差异。

## 恢复顺序与运行入口

在新的专属副本恢复以下内容；不覆盖已有实验root、共享环境或旧封存目录。权重、环境和缓存不在发布包内。

1. 从官方仓库取得上述固定fork提交，先`git apply --check /absolute/path/SpaceServe-complete.patch`，再`git apply /absolute/path/SpaceServe-complete.patch`。本批已在CPU独立checkout实测此路径；无需在这一步导入CUDA或启动服务。
2. 根据版本清单恢复独立Python3.10环境及原生vLLM0.7.2、torch2.5.1、transformers4.49.0、实际cuBLAS12.4.5.8。原声明依赖与实际cuBLAS版本差异保留，不声称未经GPU验证的新环境等价。仅对该专属环境的`site-packages`根应用两份native补丁，先check再apply；不得改用户全局环境。
3. 按[输入摘要](../configs/input-pins-summary.json)恢复模型文件SHA、COCO20图、实际448×448 RGB与原请求序列。CUDA扩展的八个内部链接须指向同一专属原生wheel的对应文件，路径转换和逐SHA验证按[scripts/stage_cpu.py](../scripts/stage_cpu.py)，不能共享可写hardlink或照抄旧绝对路径。
4. `mysmctrl`固定`6ff57356968a3f04158b9273aa881ee6bdf04229`；构建命令与数值/模型stream探针源码分别在[scripts/run_numeric.py](../scripts/run_numeric.py)、[probe_sm_mask.cu](../scripts/probe_sm_mask.cu)、[service_sm_probe.cu](../scripts/service_sm_probe.cu)。本批实际自建库SHA由原始G3绑定。只加载库不能证明应用mask；正式组禁用SM诊断与profiler。
5. 下一有效窗口须重新核预约、boot、GPU UUID、占用、专属root和UID，审查冻结新窗口及守卫配置，完成实际CPU/数值/模型预检G2/G3后才运行正式入口。**不能照抄旧批准marker或绕过脚本中固定日期、身份与时限守卫。** 当前被冻结的入口分别为`run_numeric.py`、`model_launcher.py`及`formal_launcher.py`；实际版本以各自manifest为准。

## 本地离线复算

真实采集结束并抓回全部原始证据后，在本批根目录执行：

```bash
python -B -m unittest discover -s analysis -v
python -B analysis/render_report.py --root /absolute/path/copied-batch --output /absolute/path/new-report
```

输出拒绝覆盖。须保留dataset、configs、全部G3绑定、controller原始回执和results目录；不是只有requests.jsonl就可计算受审结论。部分矩阵保留全部54计划单元及三种配对，不生成总体区间或完整矩阵汇总图；按另行G1批准的[CPU展示补充](../analysis/partial-display-plan.md)，仅无全局冲突时展示有效单次原始点及全部缺失/失败状态。分析/renderer的G2不是实际数据G4，完整复现仍须G4/G5与发布核验。

上游许可证保留为[SpaceServe原LICENSE](SpaceServe-LICENSE.txt)；vLLM继承其官方包内许可及来源。补丁不改变上游授权，不将第三方源码统一重新许可。
