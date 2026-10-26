# EPD修正批次：执行状态与入口

**发布准备状态：终态部分数据，完整C未完成；尚未获得本次发布G5批准。** 53/60单元、5300正式＋1060预热；七项缺失，不再续接。实际部分G4与窄受阻收口G5已通过，其范围不等于完整C验收或发布许可。[终态与审查索引](report/publication-status.md)优先于下文历史记录。已签名报告原文保留“候选待审”历史标题，实际后续审查见索引。

本目录是2026-10-26新批次，与原封存四批和原Release分开。已完成实际数值通信与289请求模型正确性预检；完整lite观察失败，B阶段未运行，经审查转C-off。首区组10个cell已独立G4通过；唯一续接已退出1，最终保留53/60个cell（5300正式＋1060预热），七项未执行。三卡已确认释放；实际部分G4及窄受阻收口G5均APPROVE_WITH_NITS/BLOCKING0；不含发布许可，不再续接C。CPU_STAGED、服务启动及单纯exit0不表示实验验收。

## 冻结范围

qjh000，MiniCPM-V-2_6，FP16/TP1/eager。EPD E:P:D=1:1:1，对照同三张H20上的三个完整模型副本；统一cap8/context4096/batched_tokens4096/seq8，IRP和动态角色切换关闭。详细设计及终态审查原字节副本在[设计](reviews/publication/epd-bc-design-v1.md)与[审查索引](report/publication-status.md)。

GPU工作窗口：系统实际确认的北京时间2026-10-26 21:00至27日09:00，运行时必须重新向预约系统核验boyjiang/GPU lane/h20/qjh000。结束前120秒清理；本地锁或历史空闲快照不代表预约权。

## 当前状态

| 项目 | 已有实际证据 | 尚缺 |
|---|---|---|
| B0环境 | 80706成员/30086083014 bytes迁移；实际74088文件逐SHA重验；旧源未变 | 环境与模型不得上传Git |
| GPU代码G2 | 新53成员SHA `01cab0ae49091effbd6bed8220fee96382d711f761ef7bcfa8652ad287da5ed0`；独立G2通过、目标27CPU+ALARM1与部署53SHA均实际通过 | 仅授权一次performance-resume，禁止B/lite/重跑前缀 |
| 数值G3 | 实际BLAS、embedding IPC、KV全值一致性通过；独立G3通过 | 原numeric producer710与后续consumer分记 |
| 模型正确性G3 | 17reference+272目标冷启/重启/路由通过；独立G3认可模型/off | 自然图不保证全量语义正确；首68失败分支另存 |
| lite观察G3 | EPD冷启/重启worker实际CUDA窗口全缺，host诊断保留 | 完整观察未通过，不解释off关键路径 |
| B观测开销 | 未运行；独立G1/G4批准失败fallback | 不存在等效结论，不调剂4800预算 |
| C性能 | 实际53/60：5300正式＋1060预热；唯一续接exit1 IdentityUnconfirmed；794原始文件本地逐SHA匹配；GPU已释放 | 七项未执行，不再续接；没有六区组CI；部分G4及受阻收口G5均通过，发布仍待独立G5 |
| CPU分析 | 本地21项通过；部分报告列全60单元和30计划配对，逐次比值仅描述 | 新增partial全局检查/配对表G2已APPROVE_WITH_NITS0，21CPU通过；不出合并CI/性能图 |


## 代码与分析

- [启动/压测/预检](scripts)、[独立EPD源码副本](src)、[冻结顺序及代码清单](configs)。不要删除守卫或复制历史批准marker。
- [六区组分析器](analysis/analyze_cells.py)从逐请求重算并核对summary，绑定G3/实际boot、GPU worker、RGB及窗口顺序；部分/失败/缺证据保留，不自动签Gate。监测质量事前固定：目标0.1秒，最大gap2秒、首尾容差1秒，未知显存不填零。
- [CPU测试](analysis)：`python -B -m unittest discover -s outputs/epd-revision-20261026/analysis -v`（仓库源目录运行，不启动GPU）。完整48/60cell合成fixture只测试分析器，不能当实验数据。

实际数据抓回后，在独立副本中复算；数据不齐只输出partial，不把候选分析当Gate：

```bash
python analysis/analyze_cells.py --root /path/to/copied-batch --phase performance --output /path/to/new-performance-analysis.json
```

`--root`需要保留dataset/manifest.json、configs、evidence/G3_MODELS_APPROVED.json及其bound_files、results/preflight-models/reference.json、完整阶段目录。分析器只读原始数据，输出拒绝覆盖；不删除不利结果，不把requests当六次独立运行，不宣称已解释off因果瓶颈。

EPD本批完成验收或明确受阻并收口后，SpaceServe补充方案另行G1冻结；正式测量不并行。两项目均交付并分别核验GitHub后，总目标才完成。

## 候选报告与baseline图表生成

完整实际数据抓回后，在本批目录使用Matplotlib3.9.2运行；直接重审raw并生成analysis.json、Markdown、PNG和SVG，输出目录拒绝覆盖：

```bash
python analysis/render_report.py --root /path/to/copied-batch --phase overhead --output /path/to/new-B-report
python analysis/render_report.py --root /path/to/copied-batch --phase performance --output /path/to/new-C-report
```

生成器G2已APPROVE_WITH_NITS/BLOCKING0，两个nit已落实。B的lite/off90%区间与C的EPD/三副本95%区间分别展示；所有退化保留。不完整批次列全部计划/实际记录及错误，以及全部计划配对的逐次描述；无合并CI、总体加速结论或性能图。报告始终标候选，实际G4/G5前不称已验收。work下带SYNTHETIC标记的绘图fixture只是CPU测试，不是本批实测，不上传为结果。

## 正式前请求冻结

对应设计第2/6节，预约生效后、模型/正式测量前，在新root source env.sh后用新环境CPU生成实际请求清单（不执行模型前向或CUDA）：

```bash
/var/tmp/boyjiang-epd-revision-20261026/envs/epd/bin/python -B analysis/freeze_requests.py --root /var/tmp/boyjiang-epd-revision-20261026 --output /var/tmp/boyjiang-epd-revision-20261026/evidence/frozen-request-protocol.json
```

需同步已审analysis/freeze_requests.py、analyze_cells.py和block_statistics.py并核对各自SHA；它们是CPU辅助代码，不改变GPU50清单。新协议保存20文件/RGB SHA、五点各120请求顺序、实际template prompt及SHA、同host boot/UTC/perf_counter。G3模型门禁的bound_files必须纳入该文件；分析器检查实际prompt/图序/RGB符合且冻结时间早于运行。输出拒绝覆盖，失败不默默改清单。

本delta G2 APPROVE_WITH_NITS/BLOCKING0；17 CPU测试实际记录evidence/analysis-request-freeze-cpu-tests.json，旧14记录保留。实际冻结协议已执行并绑定G3，见evidence/frozen-request-protocol.json；本节命令保留为复跑说明。

## 历史落实记录（2026-10-26 夜间，现状以上表及current-status为准）

EPD模型正确性第二attempt已完成289请求（17 reference+272 target），原首次启动失败68请求单独保存。独立G3分项认可数值/模型/off路径；完整lite机制失败：EPD冷启/重启worker CUDA窗口为空，不能称阶段观测通过。B正式未运行，不存在开销等效结论。

经独立G1/G2/G3及失败fallback G4批准，C-off原定60个cell/6000正式+1200预热已启动；controller50725，首个000-b0-E-epd-off已完成，随后001 baseline。当前不报告未完成区组CI。计时窗外全机GPU/load/mem/swap快照和所选三卡外来PID监测保留，共享主机结论不能提升为内部阶段因果。

实际consumer清单9bb1a92b9864bb9ccd837a9258d7079f0dc98d559ab305c906d4bed6d27d4bbd，numeric producer710/model producer49分别保留。门禁 evidence/G3_MODELS_APPROVED.json 和 C_SCOPE_APPROVED.json 明确C-off-only/lite=false。checkpoint版本演进采用89项原路径+1项历史49清单归档映射，不改旧批准和原失败记录。

预约fresh核实本人qjh000 GPU lane截至2026-10-27 09:00北京，08:58前受控清理；08:30/08:58原生任务保留，21一次性任务已删除。SpaceServe仍为下一阶段；两项目交付具体要求见工作区PROJECT_GOAL.md，各自comparison目录必需。旧封存/七ZIP/Release不变。


## 唯一断点续接的历史启动记录与取证入口

原C控制器完成block0后在010服务启动阶段中断，退出码及原因均未知（null/unknown）；152件原始文件已逐SHA冻结，首10原路径不动，010两件移入失败档案并留映射。新控制器PID3542208、ctime1793033278.17、controller-ID8eccc158550d4ff7a2e27ed28fbc71b0已实际核活及marker一致，远端持久日志`evidence/C-resume-controller.log`。只补原顺序index10–59，不二次续接；再同类失败保存partial收口。

- [实际中断清单](evidence/C-interruption-20261027-0018.json)、[首区组CPU审计](evidence/C-prefix-analysis.json)、[历史映射](evidence/C-resume-history-mapping.json)。旧C producer9bb、model producer49、numeric710、新consumer01分别保留，旧JSON不改写。
- [实际启动身份](evidence/C-resume-launch.json)、[模型/off门禁](evidence/G3_MODELS_APPROVED.json)、[C范围](evidence/C_SCOPE_APPROVED.json)、[前缀批准](evidence/C_PREFIX_APPROVED.json)、[本次审查](evidence/reviews-C-resume)。
- 最终`C-resume-exit.json`只能由marker owner UUID+PID写入；上述为启动时历史记录。现已实际exit1，完整终态见下节与发布状态索引，不能声称exit0。

历史项目展示结构已独立窄G5通过并发布：commit `3acdc797353256e22e4b123e6cf7087131100c73`，[SpaceServe独立项目](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/main/spaceserve)、[EPD独立项目](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/main/epd)。当前新C未验收结果不混入历史提交；原Release与7资产不变。

## 2026-10-27 终态部分结果

[候选逐单元及baseline配对报告](report/C-terminal-reviewed-candidate/report.md) · [实际退出](evidence/C-resume-exit.json) · [资源释放](evidence/C-terminal-resource-status.json) · [原始文件SHA](evidence/C-terminal-files.json)。最后052单元请求已产生，退出清理读取已注册worker 4052597身份失败；为何身份读取失败尚未定位。不能据此判为模型数值失败，也不能把退出1改写成成功。缺53–59全部保留为未执行，按一次续接停止规则收口；完整C性能复现未完成。
