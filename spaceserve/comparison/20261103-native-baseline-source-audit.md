# 原生 vLLM 基线源码核查：CPU阶段

[复跑与下一步](../docs/official-first-request.md) · [完整Python文件清单与比较](../validation/native-baseline-source-20261103/)

当前环境版本号为vLLM 0.7.2，但不能直接称为未经修改的原生baseline。对固定原生源码树的585份Python文件逐项比较，已安装包588份：583份匹配、2份不同、0缺失/拒读，另有3份extra。没有导入目标模块、加载二进制或运行GPU。

| 文件 | 已观察的差异 | 结论边界 |
|---|---|---|
| platforms/cuda.py | 增加GPU UUID到NVML物理索引的兼容处理 | 未量化性能影响 |
| v1/worker/gpu_worker.py | 模型加载后额外调用record_device.record(self) | 不能凭hook位置断言无影响 |
| extra | 生成版_version.py和两份vendored flash-attention Python包装 | 不冒充已验证其二进制或ABI |

[CUDA审计diff](../validation/native-baseline-source-20261103/installed-cuda-audit.patch)和[worker审计diff](../validation/native-baseline-source-20261103/installed-gpu-worker-audit.patch)是已安装包相对原生源码的差异，**不是本次已应用补丁**。此发现不证明历史结果全部无效，也不能量化历史性能影响；旧批次及负收益原样保留。

为准备本轮可信native对照，已在同一个`/local/boyjiang/SpaceServe-official`中建立`baseline/vllm-v0.7.2`分支：

| 身份 | 值 |
|---|---|
| 原生vLLM v0.7.2 commit | 0408efc6d0c17fba17b2be38d0d0f02e96d2bf9d |
| 本仓库内容基点/新baseline分支commit | d7ec548300d7950c1305231b2aaf970bab7569c1 |
| 两者相同的完整tree | 9887287659a56df6f9744e631667f67893512b8c |
| 当前仍在的适配分支/HEAD | adapt/qjh003-v1 / 66de079af4234b27f7f82ff91d238ef1351324ba |

commit身份和历史不同，内容树相同。目标机实际浅fetch/创建分支exit0，readback匹配，未切换工作树；当前适配HEAD和clean不变。新增Git对象约508KiB，没有新checkout、环境或模型副本。原有临时pack未动。

独立G4及metadata子范围验收均APPROVE/BLOCKING0。新分支只证明来源准备完成，**不证明native或Space路径可加载、模型正确或SM mask生效**。仍须在合法窗口实测compiled模块加载、原生/解耦/有效encoder mask三组，以及设备放置与实际计算重叠。不同模型/卡数不作绝对性能排名。
