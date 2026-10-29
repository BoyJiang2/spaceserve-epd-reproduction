decision：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-29T06:00:33Z
审查者：独立 Codex subagent /root/handoff_cpu_review
scope：CPU bundle传输/单次deploy-recovery源码；不授GPU执行许可。

已只读审四份维护源码及diff/测试、bundle-recovery-result.json和原始stderr。未运行测试、Git远端/API/SSH/GPU或读凭据，未改实现，仅保存本审查。

四源当前SHA与原始result逐份重算一致：

- prepare_space_temporary.py：acf3c4f3213336ee8495868cac4dee33592588ce722287a53e8d4018cd3c40ff
- control_space_temporary_cpu.py：931cf156515b4c439a146cd8a8f17b4ccdf449070abf8e982e5278362d898aa0
- test_prepare_space_temporary.py：dad10c9ac0effa5415eb24e9a910b3be1added4ca201f657721a0a12bea02e06
- test_control_space_temporary_cpu.py：1a24408d8c60354624178c3e177df9e389c746853bd9aa243f03ea8a4f4021a1

恢复范围足够窄：仅新增transfer-recovery/deploy-recovery，原失败deploy文件不覆盖，恢复claim/log/terminal使用独立phase名。recovery_bundle核旧terminal精确b4dda733摘要、失败exit1/TimeoutExpired和原log摘要，原config精确ebe8ae33摘要；新config除source_commit外必须逐字段相同，不能延长14:40截止。固定bundle仅接受owned regular非link、实际size/SHA和≤16MiB；目标Git bundle verify/list-heads精确C1 HEAD后才本地fetch/checkout/fsck，恢复分支没有网络fetch回退。HEAD仍beadff clean、run/candidate无、恢复marker不存在等检查保持。prepare只有匹配C1/config/log摘要的成功recovery terminal才进入；原deploy成功链保持独立。

传输入口的inline源码来自已核Git/API维护源码，先SHA再compile，执行模块本身不调用main或GPU初始化。随后核config/user、host/UID/CPU50nice10/boot、原窗口完整360秒余量、fresh resource、managed root/staging、原失败terminal、run/candidate不存在、三个原PID不存在与GPU2只读idle，才exec固定/usr/bin/dd。stdin是本机已核bundle，使用受审launch_cpu的同一fileFD摘要校验及UNKNOWN不杀/不重启语义；dd固定目标、conv=excl/oflag=nofollow、umask077，无删除或覆盖。传输只负责排他字节落盘，原log/完整prior-config和目标bundle摘要闭合在随后的deploy-recovery检查，不能将transfer exit0本身称部署成功。

原240秒外层工作+120秒收口及END-120不变；恢复Git每调用接受共同剩余时限和原pidfd/session身份收口。没有自动retry/换卡/重建run或重复失败HTTP。CPU辅助查询仅metadata，不能据此推导CUDA/numeric/模型机制。当前批源码diff限维护工具/tests，真实GPU84源码和共享模块精确不变仍须最终G5/source清单闭合。

原stderr实际Ran10/0.095s/OK，无skip；result exit0。覆盖prepare→cpu的mock成功链、wrongHEAD/managedtmp、existingRUN拒恢复、旧failure/config/window/bundle变化拒绝、transfer错误executor在query/write前拒绝，以及原fileFD/观察超时保全。不是实际Git bundle clone/fsck/dd/SSH成功证明，也没有实际信号或GPU执行；我未复跑。

最终C1、原窗口config及实际bundle尚待后续精确G5/Git-first/API字节前验，尤其需核bundle实际SHA/≤16MiB/精确C1 HEAD和beadff prerequisite、本机与目标source闭包，不能在本review填入未产生的C1。此前三原PID独立/proc不存在证据已在G1补审认可，执行前还须fresh实际资源与项目活动核验。任何失败/UNKNOWN保留停止，原窗口不续，不缩完整1800模型门槛；prepare/CPU成功后numeric/model仍依原实际Gates，formal不批准。

GATE_RESULT: {"gate":"G2","decision":"APPROVE","blocking":0,"scope":"single_CPU_bundle_transfer_and_deploy_recovery_source_only","prepare_source_sha256":"acf3c4f3213336ee8495868cac4dee33592588ce722287a53e8d4018cd3c40ff","controller_sha256":"931cf156515b4c439a146cd8a8f17b4ccdf449070abf8e982e5278362d898aa0","execute_now":false,"GPU_approved":false}

未执行测试或远端操作；真实传输/部署、最终C1/config/bundle和后续机制结果尚未通过本审查证明。
