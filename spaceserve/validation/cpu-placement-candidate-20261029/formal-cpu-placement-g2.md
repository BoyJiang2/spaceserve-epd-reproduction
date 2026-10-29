# CPU放置候选源码G2

初审：REQUEST_CHANGES；BLOCKING2（均为新测试fixture的冻结部署兼容问题）。reviewed_at：2026-10-29T04:34:31Z。生产候选逻辑未发现其他必须修改的阻塞；不授部署/远端/实际affinity/GPU或正式运行许可。

本审查者没有参与实现，仅本地读取源码、git diff、记录及SHA，未运行项目代码、测试、系统放置操作、SSH、网络或GPU。按请求仅保存本审查原文。实际90logicalCPU profile仍须用户明确确认，原G1只是本地候选许可，formal仍0/54。

## 来源与现有测试证据

以cpu-placement-local/frozen-result.json为冻结证据：SHA256 dd9d1759c1315a44011a54d47db9bb3cbdebe168101166a6b3f40698bde6d4e5；frozen-stderr.log SHA25655d7eef929f0c2c6b0957e8f8a4a65b5bbb6e0637d9b9baf9b6538995307301d。日志为本机Windows9PASS/0skip/0.034s、exit0；当前9文件逐SHA与该receipt一致。先前final-result引用的是补after边界前的run_models/run_formal，不能称其绑定当前完整候选；该差异已由新的frozen记录如实单列。

当前源SHA256：

- entry.py：43d7b2bfb69e13161d3d555363e28b725a4202775704f6f50deca6977209794c
- configs/source-files.json：055c4fb6d536b759604f46113807c75f8095050a055d5c5ee8b2ad0b4ec3853f
- configs/project.cpu-placement.candidate.json：e846a94d76413275d4e5fe61b3c44647b7d4abda5e6edc581d39dc5c01a5f2a5
- scripts/cpu_placement.py：8a1a30d9e67ec08dd25c4c36838ea360e07a29ec58937859daa288afee5149dc
- scripts/test_cpu_placement.py：5f6b65e6abd188a526e86bf65fba5e5525aedab1a5fa4c799826362406ecdd66
- scripts/capture_runtime.py：b5230674d7332af36f8e5473cafb8fa1d6a222e51338d84443ca4f5fbe1f9411
- scripts/record_device.py：d73ab28acde926ef2d2be5691a720e722b81ea7efd0b118f4f336773cdc9d3e7
- scripts/run_models.py：dd663b3c598de842805a570473a7fb3ff86a27893e4e8f989e5928c3aa752d47
- scripts/run_formal.py：05d296d277823b77def3feaeea066d60ab89329482c2d62446b701b4f636137d

## 必须修正

B1：test_entry_frozen_helper_and_tamper_refusal只寻找父目录entry.py。本地runtime布局成立，冻结部署的入口是scripts/project_entry.py；目标CPU完整suite中该测试会找错文件。最小修正是明确兼容这两个真实布局，不能skip或删除该测试。当前本机9PASS不证明目标冻结布局通过。

B2：上述测试调用entry.main()会写os.environ['SPACESERVE_CONFIG']，但未用patch.dict恢复。测试结束删除临时配置后，后续同进程CPU测试的runtime_config.context可能读取已删除路径，污染suite。必须在fixture内隔离并恢复该环境变量，包括异常/篡改分支；不能通过改后续生产guard规避。两项均已由主代理自查并与本审查者复核确认。

## 生产逻辑与最小性

entry仅在明确profile且numeric/model/formal时执行apply；require_scope、冻结project/receipt绑定先行，helper及manifest拒绝直接symlink且逐SHA核后才import。旧profile缺失不偷偷扩CPU，CPU/prepare不set。小stdlib模块明确拒bool/重复/负数/乱序及非法NUMA，核完整node cpulist/online、唯一UUID/PCI/sysfs NUMA，再set/readback；非法/缺失资源数据均抛错。候选配置为candidate/nullrun/空GPU/空actions/无booking，不是可执行授权。代码不改OMP/模型/SM或benchmark。

worker记录实际main/thread集合及环境，模型/正式校验复用同一validate；capture边界重新取workerPID/start_ticks/UID，拒身份变更、缺worker、main不等或线程越集合。新增after采集在诊断请求完成/停服务前及formal measurement结束后，before采集保留，不将高频监测加入测量区间。source-files为82个唯一path，全部source存在，新helper/test闭包纳入；原目标CPU verifier按AST动态发现，不需硬编码测试数。

## 非阻塞限制与后续门槛

snapshot遇到/proc线程消失、权限或系统接口错误会直接失败，属于保守拒绝；无profile时record_device/capture仍新增观测字段/读取，所以只能说“不扩CPU且原校验放行”，不能宣称无profile的全部观测行为逐字节相同。没有真实Linux线程生命周期/实际set/readback测试；Windows mocks也未执行边界capture脚本的完整真实进程路径。这些须在实际采用经确认、G2/G5发布和有效CPU授权后的目标验证中成立，不构成本地候选额外重装/新框架理由。

修改后的fixture应重新提供本地日志及最终源SHA；本报告保留原B1/B2，再追加真实关闭记录。实际采用0–89仍按AGENTS第85行取得明确profile确认并fresh核授权/拓扑/OS可用集合；旧CPU50服务G3和本机mocks不转授新profile。后续新source/config/cohort与CPU/numeric/313/G3、足够长正式窗口均不跳过；不推断已实测CPU瓶颈或新性能收益。

GATE_RESULT: {"gate":"G2-local-CPU-placement-source","decision":"REQUEST_CHANGES","blocking":2,"reviewed_at":"2026-10-29T04:34:31Z","production_logic_additional_blocking":0,"actual_profile_or_GPU_execution_authorized":false}

## 两项关闭与最终结论

补审reviewed_at：2026-10-29T04:36:05Z。**最终G2：APPROVE_WITH_NITS，BLOCKING0，仅本地候选源码及现有软件证据。** 原B1/B2及旧测试记录保留，不追溯替换。

B1已通过明确的entry.py→同目录project_entry.py真实布局选择修复；不是skip。B2已用patch.dict(entry.os.environ)包围所有entry.main调用，异常/篡改分支同样恢复环境。最终test_cpu_placement.py SHA2565dc85252829a7ee7c1182dfefeb21760643844ea302bedbcbe56a2859bc48482，其他8文件保持上列冻结SHA。独立逐SHA核当前9源均匹配candidate-result.json；该证据SHA2569c99a51334be7bab633654cd50679b6e80602ef2376a574708c5d0a3f8b6177b，实际本机Windows9PASS/0skip/0.037s、exit0。

额外本机frozen-layout证据使用scripts/project_entry.py、同目录reproduction_paths.py及helper/test四个实际副本，四项SHA均与指定源相同，实际9PASS/0skip/0.036s、exit0。frozen-layout-result.json SHA256bd1ee1c283b5d30dcffdbffe6102d942d4f6d82b5ead06db4ca9d0a667a5fa6e。该证据关闭文件布局回归；仍是Windowsmock而非实际Linux目标CPU suite、真实sched_setaffinity或worker观测通过。

最终非阻塞说明维持上文：真实/proc权限、线程生命周期与测量边界采集须以后在有效授权的目标验证；无profile不扩核但新增观测不等于所有旧行为逐字节相同。源码/测试规模与本地G1相符，不需为此另建框架。实际90logicalCPU profile采用仍须明确用户确认、适用G5/Git-first与新cohort实际Gates，未授部署、远端、GPU或formal执行许可。审查者未运行上述测试、未参与实现，仅读源码和既有结果及核SHA。

GATE_RESULT: {"gate":"G2-local-CPU-placement-source-final","decision":"APPROVE_WITH_NITS","blocking":0,"reviewed_at":"2026-10-29T04:36:05Z","local_candidate_only":true,"actual_profile_requires_explicit_user_confirmation":true,"remote_or_GPU_execution_authorized":false}

## 本地候选资料G4/G5补审

reviewed_at：2026-10-29T04:36:50Z。G4 APPROVE、窄候选发布G5 APPROVE，BLOCKING0。范围为已绑定的9源、spaceserve/validation/cpu-placement-candidate-20261029/下README及9份计划/审查/结果/log原件，以及spaceserve/README.md末尾候选导航；不是尚未提供的精确staged tree审查或实际远端发布证明。

该目录9份副本分别与outputs下对应计划/G1/audit及candidate/frozen-layout六份结果/log逐SHA相同。README清楚区分本机Windowsmocks、无真实affinity变更、未部署/未采用、实际profile需用户确认、formal0/54及完整目标未完成；没有将旧预检作为新profileG3，也没有声称已证明CPU瓶颈或性能改善。源码/测试链接和G1链接指向实际候选文件，spaceserve末尾导航明确“尚未采用，不是正式性能结果”。无模型/env/旧raw/Release修改。

批准将上述真实候选作为代码/资料普通commit/push；执行前仍核实际staged成员/源SHA/Git-first，新增材料若超出本范围另核。不授目标部署、CPU0–89实际采用、GPU或formal许可。最终源SHA以上节candidate-result所绑定9项为准（test5dc852...；其余8项未变）；本G4/G5不把9mocks升级为Linux完整suite或实际资源授权。

GATE_RESULT: {"gate":"G4+G5-local-CPU-placement-candidate-publication","decision":"APPROVE","blocking":0,"reviewed_at":"2026-10-29T04:36:50Z","actual_profile_or_GPU_execution_authorized":false,"formal_cells_completed":0}
