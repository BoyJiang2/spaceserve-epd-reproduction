# SpaceServe 7B / EPD 最终批次

本批主测为 qjh000、Qwen/Qwen2-VL-7B-Instruct、FP16、TP=1、eager、同一张H20 GPU0。18配置、5400正式＋360预热已全部完成并技术复算通过，原始数据已完整收回；全量数据和报告G4均APPROVE_WITH_NITS、BLOCKING0；G5同样APPROVE_WITH_NITS、BLOCKING0。最终封包完成证据见[外置完整性记录](../spaceserve-7b-h20-integrity.json)，包见[SpaceServe ZIP](../spaceserve-7b-h20.zip)。结果见[本轮结论](report/final-summary.md)、[完整报告](report/space-all-report.md)及[验收索引](report/acceptance-checklist.md)，验收状态以`status.json`和实际review为准。

EPD方案A是qjh003已有2400条正式＋160条预热，已做完CPU分析并以受限范围独立通过G4/G5，见[EPD报告](../epd-profile-a/report/report.md)和[完整性记录](../epd-profile-a-integrity.json)。不重跑，不与本批单卡7B结果做跨模型绝对排名。旧4090/L20的2B与更早H20 EPD分别保留在`../reproduction/`。

## 固定输入和版本

- SpaceServe `66de079af4234b27f7f82ff91d238ef1351324ba`；mysmctrl `6ff57356968a3f04158b9273aa881ee6bdf04229`。
- Python3.10、Torch2.5.1/cu124、vLLM0.7.2、transformers4.49.0；154个固定包见`configs/space-freeze.txt`，实际pip检查/已安装清单在`evidence/`。
- 权重未随包分发；`configs/qwen7b-model-original-pin.json`保存每个文件的revision/bytes/SHA256，`qwen7b-model-manifest.json`保存实际获取记录。逐文件pin不能称为单一共同revision。
- 固定20张COCO图及manifest在`data/dataset.tar.gz`，与首轮封存包字节相同；RGB448×448策略、图片序列及实际256视觉tokens/图由原始请求和RGB记录校验。
- 运行根目录固定`/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023`；GPU UUID `GPU-d1b595ce-0b57-cdee-c1c0-9b1051aaa07e`，驱动535.161.08。脚本包含主机、boot、版本和批准marker校验，不是可直接迁移到任意主机的通用安装器。

## 实际执行入口

以下是本批已使用的命令。正式运行使用专属GPU锁和私有100% MPS，正式计时关闭profiler/SM诊断，禁止同时准备模型、下载、分析或导出本项目数据。已有`results/formal/`时入口主动拒绝覆盖；另起复测须先保全已有结果、确认资源和当前批准条件。

```bash
ROOT=/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023
bash "$ROOT/scripts/preflight_runtime.sh"
bash "$ROOT/scripts/preflight_sm_h20.sh"
bash "$ROOT/scripts/preflight_sm_layout.sh"
bash "$ROOT/scripts/preflight_model.sh" cold
bash "$ROOT/scripts/preflight_model.sh" restart
bash "$ROOT/scripts/run_formal.sh"
```

各入口需对应G2/G3事前批准，不能把这些命令连跑替代审查。模型预检的实际参数以保存的`used-scripts/preflight_model.sh`为准；冷启动、重启均通过后才写`G3_MODEL_APPROVED`与`SM_EFFECTIVE`。正式driver按native、解耦、encoder-mask顺序，先各1图/C1与4图/C8，全部完成后保持同一MPS/锁暂停。独立两点G4通过后，主执行者将`points-manifest.sha256`原bytes复制为`G4_POINTS_APPROVED`才扩其余四点。

直接启动单组和压测的参数由`run_formal.sh`完整记录：服务端口19770；每配置20预热、100正式×3、128输出；C为1/4/8，图数1/4。必须通过driver建立所有权和MPS，不绕开`start_server.sh`的锁/身份检查。

## 本地复算

真实两点及全量数据分别放在`results/formal/points/`和`rest/`。所有正式请求、逐token时间、图片/输入/输出IDs、配置和重复摘要均保留；显存、RGB、实际参数设备与MPS边界另存同目录。只有已收齐对应阶段数据时执行：

```bash
python3 analysis/space_results.py --root /path/to/qjh000-migration --phase points --output /path/to/qjh000-migration/report/space-points.json
python3 analysis/write_space_report.py --root /path/to/qjh000-migration --phase points
python3 analysis/space_results.py --root /path/to/qjh000-migration --phase all --output /path/to/qjh000-migration/report/space-all.json
python3 analysis/write_space_report.py --root /path/to/qjh000-migration --phase all
```

统计为Python标准库；绘图固定Matplotlib3.9.2、NumPy1.26.4。windows使用Python UTF-8模式。分析脚本验证冻结points双层SHA、all阶段的G4批准原bytes、实际参数/身份/显存和请求协议，技术通过还须独立G4。各配置吞吐是三重复均值±样本SD，延迟为300正式请求合并inclusive线性插值P50/P95；显存是全GPU进程归属的采样和，不是精确瞬时峰值。

## 补丁和失败证据

`results/patches/SpaceServe-complete.patch`是相对固定fork提交的累计diff，其他patch保留原生UUID兼容/实际设备记录等修改。`prepare_space.py`复用同版本wheel扩展，`apply_space_compat.py`修复已复现的多图cache覆盖/释放和进程队列问题，`install_device_record.py`及`install_service_probe.py`记录实际设备/stream机制。不要将累计patch与其分项重复应用。

机制证据在`results/sm-feasibility/`、`sm-layout/`、`preflight-cold/`和`preflight-restart/`，含10份原始gzip。实际encoder stream掩码78→64、零mask恢复78、重新施加及首次真实编码64，冷启/重启正确性共90固定案例。该mask仅作用encoder，不是decoder互斥分配或完整论文SIS；LM仍保留visual权重，解耦另有encoder驻留。

此前模型预检失败保存在`results/model-attempts-before-export-fix.tar.gz`。首轮正式native1/C1虽然完成300正式＋20预热，但显存起始覆盖0.310766秒超过0.3秒而被拒绝，原始77文件封存在`results/formal-memory-failed-20261023T2038.tar.gz`，不选入对照。G2复审后只优化采样归属查询、保留全部守卫，从首配置重新执行；新代码清单SHA及唯一源码变动见`evidence/memory-sampler-fix-adoption.json`。该失败不能被当作正式结果或被隐藏。

审查提示/真实结论/处理保存在`reviews/`，Claude额度耗尽时由独立只读subagent依AGENTS3.2.1接替，审查者身份明确标注。后续机制解释、性能结论和是否扩大实验均以实际数据及G4/G5为准。
