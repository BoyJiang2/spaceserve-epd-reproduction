# SpaceServe GPU2临时空闲预检准备

**975版本CPU部署已实际失败并收口；numeric/model均未执行，新正式矩阵仍0/54。** 这是响应用户直接授权“如果gpu暂时没人用 你可以先暂时用一下”的独立条件准入，不是本人预约记录或正式性能结果。此前的完整GPU0预检、旧48/54及所有失败原件独立保留，不转授GPU2 PASS。

用户已确认三组共享NUMA0逻辑CPU0–89、OMP4，监督器仍CPU50。选同NUMA0单H20 GPU2/UUID `GPU-c005197e-747d-2dc8-b77b-b123b41efd75`，不碰其他卡任务；当前快照仅选择背景，实际启动还要fresh空闲核验。一个临时batch固定不超过60分钟，120秒收口，numeric/model只作机制验证，formal/EPD及混合booking scope均拒绝。其他GPU的背景负载不作为可比较的正式吞吐/延迟数据。

## 代码与复核入口

- [runtime条件授权/监督](../../runtime/scripts/temporary_gpu_use.py)：绑定原始用户文稿、实际G1/G2原文SHA、frozen配置/源码及boot/UUID；独立monotonic锚不自动续时。原booking路径保留，不造BOOKING_VERIFIED。
- [CPU部署/prepare/suite](../../../tools/prepare_space_temporary.py)及[Windows每phase控制器](../../../tools/control_space_temporary_cpu.py)：先Git/API原始字节及Gitblob核验再SSH；固定CPU50/nice10、240+120、managed路径和资产startup pins、fresh资源原件、指定commit、前驱真实终态。准备不复制环境/权重，不启动GPU。
- [候选配置](../../runtime/configs/project.temporary-idle.candidate.json)仍是candidate/nullrun/null窗口，不能直接运行。最终实际window/config需独立核；控制器读取本项目工作区outputs下的实际配置和用户原文。Windows维护控制器使用固定本地证据布局与已安装gputime helper；不是通用云部署工具。
- 每0.5秒循环监测选卡，query自身timeout0.5秒；foreign/unknown PID、权限/查询失败、授权改变或到期只向当前自有监督器TERM，让原finally停止本项目。MPS GPU server须闭合实际daemon PID/ctime/UID/UUID/private pipe/control inode和真实父链。原全主机任何MPS即拒绝start的保守检查保持，不为借卡quit他人daemon。

## 本地验证与审查

[38项runtime/旧booking/布局/CPU放置回归](fixed-result.json)、[3项CPU辅助fixture](cpu-auxiliary-final-result.json)、[5项controller mocks](controller-fixed-result.json)均PASS/0skip。全部Windows CPU；不调用真实Ray/Torch/GPU/SSH/API、signal或setaffinity，不能代替目标Linux全suite及实际机制G3。CPU辅助正向fixture走实际main的prepare→cpu控制流，子入口/OS/Git是明确fake；错误live HEAD在repo模块import前拒，两个管理临时目录guard拒绝在mkdir/claim前生效。controller测试131KB文件FD输入、payload SHA/regular身份、限时等待及UNKNOWN不kill/重启。

[原始MPS缺身份失败](mps-regression-before-stderr.log)、[混合scope失败](mixed-scope-before-stderr.log)先复现再修；CPU辅助初次Windows/POSIX路径错误也保留。独立审查发现并关闭的源码绑定、目录归属和同步stdin写阻塞均保留前后原文：[G1](space-temporary-idle-g1.md)、[runtime G2](space-temporary-idle-runtime-g2.md)、[CPU辅助G2](space-temporary-idle-cpu-g2.md)、[controller G2](space-temporary-idle-controller-g2.md)。

## 尚未完成

精确发布G5、GitHub/服务器指定版本与全部SHA、实际config/window、目标CPU suite、GPU2 native/MPS numeric实际G3、完整313冷启/重启模型与并发/encoder mask实际G3，均须据真实回执分别验收。MASK_OFF56及旧GPU0端口诊断只是GPU2待测候选；未验证decoder互斥，不称完整SM分区。任何失败保留，不缩预算/自动重试；临时预检通过也不等于正式54或两项目目标完成。

## 实际部署失败与一次恢复准备

9754419完成Git/API前验后，真实CPU部署的GitHub HTTPS fetch在60秒Timeout，实际exit1；[目标terminal原文](deploy-failure/deploy.terminal.json)、[Git命令日志](deploy-failure/deploy.log)、[原配置](deploy-failure/original-config.json)和[三个原PID实际消失回执](deploy-failure/process-release.json)保留。目标仍beadff9/Gitclean，run/candidate不存在，GPU2空闲；不是观察超时，也没有启动GPU。原三文件下载后SHA与目标逐项相同，见[原始readback](deploy-failure/readback-original.json)。

[恢复G1](space-temporary-bundle-recovery-g1.md)/[G2](space-temporary-bundle-recovery-g2.md)批准仅一次CPU bundle恢复准备：新增transfer-recovery/deploy-recovery，固定staging接收≤16MiB精确C1 HEAD bundle，先原始失败terminal/log SHA、旧配置与未变化窗口、实际资源/UID/boot/CPU50/目标空闲、owner/file/hash与Git bundle验，再本地fetch/checkout/fsck；保留旧deploy文件，新recovery独立claim/log/terminal。prepare只接受匹配的新成功前驱。新代码不改变Space84源与共享GPU代码，只更新维护入口；由于run尚不存在，首次prepare将冻结全C1，旧实际失败永远记975。

[10项本地回归](bundle-recovery-result.json)PASS/0skip，明确CPU fixture/mock；原临时窗口13:40:34.579–14:40:34.579及END120不延长，完整模型仍需1800秒入场。精确G5/Git-first/实际C1配置与bundle前验未完成前，不执行恢复。恢复成功也不等于目标CPU suite、numeric或模型G3通过。
