# G2 Space补丁交付回放（CPU/文档范围）
按AGENTS3.2.1只读subagent接替，不网络/凭据/GPU/改文件。新增outputs/spaceserve-revision-20261027/patches/及configs/patch-delivery-manifest.json；不是新推理补丁，不部署任何GPU文件。
- 原样复制封存累计SpaceServe-complete.patch与baseline-cuda-uuid.patch（未改旧源）；本地官方66de checkout实际git apply check/apply通过，6改动文件LF SHA逐个匹配本批configs/relocated-inputs.json中实际src/SpaceServe对应源。回执evidence/fork-patch-replay-CPU.json；本地work/spaceserve-upstream-66de保留CPU应用结果。
- 官方vLLM v0.7.2 worker通过GitHub API取得并核Git blob SHA（raw域连接reset，重试失败未伪造下载）；native-device-record.patch实际仅新增record_device两行，apply后LF字节匹配实际native worker source snapshot。UUID补丁另对官方cuda.py apply并匹配本批native原始pin。回执evidence/native-{upstream-source,patch-replay,UUID-patch-replay}-CPU.json，work/native-space-patch-check-20261027保留应用结果。源码未执行/CUDA未导入。
- patches/README.md记录累计不可与分项重复叠加、native/fork分开、启动/缓存/Queue/SM条件探针会影响路径、不声称全无偏；恢复专属环境/模型SHA/8内部链接/数值模型G2G3后正式，禁照抄旧marker/日期守卫，离线入口；上游LICENSE保留。当前README顶部新增最新状态/旧启动段历史标识。
请核回执与实际base/result/manifest/source AST/归一化SHA、三补丁的最小准确性、路径/许可/复跑说明是否完整，有无夸大“可运行”/fresh环境已验证。仅CPU交付代码文档G2，不是新GPU批准或实际数据G4。
附：已批准render_report.py仅文字澄清“位置平衡是冻结完整计划，partial不声称实际已达成”，算法/图不变，无需视为实验设置变更。
给APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING/NONBLOCKING，只回复主agent落盘。
