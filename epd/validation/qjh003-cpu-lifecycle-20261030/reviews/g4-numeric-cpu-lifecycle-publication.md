# EPD CPU生命周期准备页：文档与证据独立G4

reviewed_at_utc: 2026-10-30T00:19:08Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，仅当前文档和可读证据展示；不代替精确发布G5，不批准commit/push、部署、远端CPU/Ray或GPU执行。**

绑定新页 `epd/validation/qjh003-cpu-lifecycle-20261030/README.md` SHA `706f422f87881aced15f92499b181fdb18a2f366084c1de2f8b08e7c2d2d2018`，原重定位页 `epd/validation/qjh003-CPU-relocation-20261030/README.md` SHA `e3cd7caa713209ae02dbbff9773e0103ef872c6080696f5b675b582c3d0aaf99`。新目录实际38文件（README+37附属）、371402字节，完整SHA清单在本审JSON。仅本地只读/解析/SHA/链接路径核验，无项目/测试、网络、SSH、GPU或源码修改。

## 展示与证据相符

新页开头明确是CPU生命周期接线准备、不是新增性能/IPC结果；表格将实际静态apply/verify、安装源码静态核验、本地fixtures与尚未实际执行Ray四场景/native36/公平PD分别列出。原EPD性能比较页只作导航，没有复用旧方案A/53-of-60当本批成绩，也没有跨主机/模型绝对排名。没有新增req/s、延迟或加速比。

helper97a33d5287cfdca69956da0fdabe5bc68ea65d46、实际旧runtime a3f03b9dd5956db92add454f9b3afd5663f84609、Space冻结24b分开陈述，未把使用helper写成运行目录已更新。源码审查通过不开放真实Ray/GPU阶段的界限明确；未来Git-first/部署/独立执行G2/实际G3仍单独列出。

复制的审查/Gate/测试/配置来源材料与对应outputs原件逐字节核同；两份最终G2 JSON的review_sha256与所指真实原文一致、passed/B0有效，不靠文件名推断。旧初审和首次修订拒绝、初次Windows缺少/proc的4ERROR以及整合缺EPD_CPU_TEST_TMP的36ERROR日志均保留，最终166项不是删失败后假称首次成功。166唯一ID及其日志SHA与源码候选manifest全同；文案明确fixtures/回环socket/NTFS文件检查，不能代替实际Ray/POSIX/GPU。测试复跑PowerShell只运行本地unit discover，并配置其必须的EPD_CPU_TEST_TMP/PYTHONPATH，没有提供未获批远端启动命令。

实际installed-ray-source-inspection.json与服务器静态检查stdout原字节相同；17项path/SHA集合精确对应loader的16源码pins加runtime_context，全部matches true。该原件只读安装文件，optional dependency存在性不等于已import或minimal实际分支，README明确保留这个限制。本人未访问服务器或复核当前安装状态，不将历史时点证据称当前健康。

apply/verify实际审计、terminal与inventory均为真实复制；inventory虽本地格式化，JSON语义与verify tar生成原索引全同。原121物理文件不变、新增verify terminal的122物理+1生成inventory口径正确。61startup/56修正/3link、原nested不变与先前独立实际审计相符。

README给出的verify raw.tar真实1003520B/SHA `97dc246c9b1e5f3e9f219043be2731e4df7de1d234803016870f26869f256374` 与本地实际包一致，且说明含环境启动文件/库原字节，只本地保留、不提交环境包、不当Release资产。没有虚构Release URL或下载链接。原始完整维护包不入Git的理由明确，Git内仍有可读报告/运行回执/逐文件inventory/审查，非只丢ZIP。

原重定位页新增最新静态结果与新页导航；旧“尚未运行”放在“维护源码首次发布时的准备记录”标题下，是明确历史，不与最新结果混为当前状态。没有改旧配置/ZIP/Release或追溯原证据。

## 链接和发布边界

本人对新目录所有Markdown及两个README相对链接逐一按真实所在目录解析，全部指向checkout实际存在文件；项目比较、runtime代码、历史及最终审查、证据与官方pins导航可读。官方完整源码只本地保存，pins给出真实原GitHub源链接，README已说明，不以本地不存在的原件相对链接冒充可下载材料。未联网核外部URL，外链是来源而非声称新发布成果。

38文件常见token/私钥头及会话已知口令片段筛查无命中；没有环境原字节、权重、缓存或trace包。真实路径/booking ID/SHA属于必要身份记录，不是凭据。精确G5仍应对最终Git tree、父分支、实际字节和新变更集合再核，不能据本审将其它未审源码混入。

非阻塞边界：README的180+120是设计预算，不是已经测得的实际清理保证；所附源审明确合作式check/Node阻塞/pending保留head及外层监督尚待。后续结果页必须据真实执行保留超时/失败与释放证据，不能把本页准备状态升级为真实CPU生命周期通过。本审不要求为展示新增GPU实验或改冻结证据。

GATE_RESULT: {"gate":"G4-numeric-cpu-lifecycle-publication-documents","decision":"APPROVE_WITH_NITS","passed":true,"blocking":0,"new_directory_files":38,"source_and_runtime_separated":true,"new_performance_claim":false,"publication_approved":false,"remote_CPU_execution_approved":false,"GPU_approved":false}
