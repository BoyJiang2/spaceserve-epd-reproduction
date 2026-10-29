# 临时路径CPU辅助/部署候选G2

初审：REQUEST_CHANGES，BLOCKING2。reviewed_at：2026-10-29T05:24:54Z。只读本地源码、既有fixture日志、SHA；未执行测试/项目代码、网络、SSH、GPU、signal或affinity操作。仅按请求保存本报告。不授完整controller、部署或目标启动许可。

## 冻结证据

当前三源逐SHA与temporary-use-local/cpu-auxiliary-fixed-result.json相同：prepare_space_temporary.py `55408dcf6222a13504dbe76ed7769aab4f328d91189740989a7c8b13f2f16909`；test_prepare_space_temporary.py `feb5d54afe1c245131832d9b7020cdd0e50d076e10baeb0d16bd3d809004ac53`；project.temporary-idle.candidate.json `d0286c0126439edd653477f803fc2080df178524835df5eacf6dc04203bd0fe8`。已给出的3PASS/0skip为Windowsfixture+mocks，main中的module exec/OS/GPUmetadata/assetinventory/childentry均由明确fake代替；不是实际Git部署或目标LinuxCPU验证。原Windows/Posix路径错误日志保留，不重标第一次成功。

## 必须回补

B1：prepare/cpu分支在import ROOT/repo/spaceserve/runtime/scripts/stage_cpu.py之前，缺少当前repo HEAD==runtime_commit及Gitclean检查。匹配前驱terminal/logSHA只证明前一单元成功时刻，不能证明当前checkout仍是指定已审源码。旧prepare_space_gpu对每phase有actualHEAD检查，此处丢失。最小修正：在任何repo模块import/entry执行前，以受控Git环境和原9cf command_output核实际指定HEAD及clean；错误必须在导入或执行该repo文件前拒绝。给fixture加入HEAD/dirty拒绝、loader/child未调用的负例，不能仅mock假entry后声称source绑定已验。

B2：循环mkdir tmp/cpu、tmp/cpu-hf、tmp/cpu-torch前，只在前面对tmp/cpu做过real_ancestry。HF/Torch两目录可已存在为symlink或foreign-owned目录，mkdir(exist_ok=True)会接受，并由child_environment传为HF_HOME/TORCH_HOME。应对每个实际managed temp路径先核real_ancestry/owner/type再mkdir，保持旧helper的同一保障；加这两类目录的负例，在任何child/foreign写入前拒绝。

## 已成立与测试范围

三phase枚举、严格config字段/本项目根/run/GPU2UUID/CPU90、booking=None/用户原文SHA、≤60min与END120、fresh只读resource origin/active/hostUIDboot/CPU50nice10均明确。Metadata GPU2idle及SITE/manifest先于stage写入；不伪造ticket。前驱terminal/commit/config/logSHA匹配、排他evidence/config/run及失败保留有接线；prepare/cpu全资产inventory前后比较。Deploy只固定公共GitHub仓库、精确payloadcommit fetch/FETCH_HEAD/checkHEAD/clean/fsck，不复制资产。实际允许的commit必须在后续controller/G5绑定，不能因任意40hex被validator接受就视为已审批。

当前3个测试不覆盖实际deploy分支的Git/timeout/fsck或真实sourceimport闭包，仅覆盖配置/错误helper早拒和fake prepare→cpu流程。该范围可以作为本地软件证据，但B1/B2修正后应补针对性mock并重新绑定源SHA，不能据其推导目标部署安全。命令控制环境最好在第一次Git调用之前设置，不能把后面的clearenv描述为覆盖前面的Gitstatus/HEAD读取。新工具尚无外部Windowscontroller；原G2runtime7源批准不自动批准本CPU辅助链或GPU执行。

修复后仍需：精确发布/G5/Git闭包、实际CPU辅助窗口授权与fresh选卡条件、受审controller、真实目标CPU/拓扑/affinity、新numeric及313G3。用户最新direct授权可走独立CPU辅助scope，但不能造BOOKING或继承GPU0PASS。全局MPS保守拒绝不改；formal不在temporary路径范围。

GATE_RESULT: {"gate":"G2-temporary-idle-CPU-auxiliary-source","decision":"REQUEST_CHANGES","blocking":2,"reviewed_at":"2026-10-29T05:24:54Z","target_or_full_controller_execution_authorized":false}

## B1/B2关闭与最终G2

复审reviewed_at：2026-10-29T05:27:00Z。最终：APPROVE_WITH_NITS，BLOCKING0，仅本地CPU辅助候选源码及已有fixture证据。原REQUEST_CHANGES及旧证据保持不变。

B1关闭：非deploy现在先用受控child_environment和限时Git rev-parse/status核实际HEAD==commit且clean，随后才进入stage_cpu的spec/import；不匹配在repo模块import/child入口前拒绝，并再次check资源/总截止。fixture新增wrong liveHEAD，断言loader未被第三次调用，正常prepare→cpu仍走完整mock main并留claim/log/terminal。

B2关闭：cpu/cpu-hf/cpu-torch每个实际managed目录在mkdir之前调用trusted real_ancestry；fixture分别对HF/Torch祖先注入拒绝，证明对应目录未创建、prepare claim未写，正常分支记录三个guard调用。

当前三源逐SHA与cpu-auxiliary-final-result.json一致，receipt SHA2560b8929eda066c4cc8ade3f107b137576e022d850308bc059b112c7bf7d8bb33c。最终prepare_space_temporary.py SHA256c80aee88fc9f140dea7e5c844f197db47fc4008536465abd263488b3c21c1c99；test_prepare_space_temporary.py SHA256c9a29792da7dbff17b219d4cfaba3f7212349dbcc73e36576692aa938fcfd384；candidate配置仍d0286c0126439edd653477f803fc2080df178524835df5eacf6dc04203bd0fe8。日志实际3PASS/0skip/0.059s、exit0，仍为Windowsfixture+mocks。没有由审查者运行测试，不能升级成真实Git部署/LinuxCPU或GPU通过。

非阻塞限制：真实deploy/fetch/fsck、目标全量suite/动态NUMA和监控/MPS归属仍未验证；外部controller未完成。发布时须单独绑定实际已审commit及全部执行模块/配置原字节，不能将validator接受任意40hex视为该commit已审批。G2只是源码结论，不包含G5或目标执行许可；后续真实授权/资源scope、controller精确G2/G5及Git-first、目标CPU与新numeric/313实际Gates仍必须成立。formal继续拒绝临时路径。

GATE_RESULT: {"gate":"G2-temporary-idle-CPU-auxiliary-source-final","decision":"APPROVE_WITH_NITS","blocking":0,"reviewed_at":"2026-10-29T05:27:00Z","local_candidate_only":true,"target_or_full_controller_execution_authorized":false}
