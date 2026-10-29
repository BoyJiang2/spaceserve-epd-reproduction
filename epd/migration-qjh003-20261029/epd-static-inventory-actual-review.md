# EPD static inventory — independent actual-result narrow review

Reviewer /root/epd_pd_followup；reviewed_at_utc 2026-10-29T00:24:46Z（clock tool）。仅本地原件/源码字符串/SHA只读核对并写本文；未执行盘点/compile/SSH/网络/GPU，不重跑、不新增预算。

结论：APPROVE_WITH_NITS / BLOCKING0，仅认可本次只读CPU静态盘点事实及诚实保留的程序偏差；**不是“全部事前发布准入已满足”，不是EPD可加载/CPU_STAGED/GPU通过**。前API核验未完成仍作为历史不符合项存在，后验不能关闭其事前性质。此结果没有授权下一轮重定位或模型实验。

## 原始链与现场范围

- command.json source_commit=ae7ede016191e68a7b933ec7470f6061d7dc4021。独立对其中SSH命令的base64仅解码为字节、未exec，SHA确为已审665e1ca755f624b8b132e6a48292c5da082f3f4731bfd047c36f2b48405b0324。实际remote argv前缀为taskset -c50 / nice -n10 / timeout --foreground --signal=TERM --kill-after=30s 60s /usr/bin/python3 -I -S -B -c，符合受审只读工具边界。
- 输入SHA d1012d...ceea6a与command.payload_sha256一致。booking仅有批准的资源字段和七个票字段，kind=cpu、本人boyjiang/qjh003/bk-20261028T0925-0332cf80/21–09；工具观测时票据年龄7101ms，距结束2192148ms（约36.5min），完整90s及08:58收口可容纳。工具成功意味着源码内host/UID2147/boot65f/CPU50/nice10断言均未拒绝；没有独立在目标重测它们。
- input/stdout共同绑定Space capture SHA2556286dec99131b25931294a1438ecd353e814462ca3cf7eff96ff44b0ec42e。实际读取本地successful-model-originals/space-http-20261029/evidence/model-attempt1-terminal.json，原SHA相同、phase=model、released=true、owned_processes=[]、boot65f52a67-afe4-4919-8646-4694255b48ee、model94 manifest0590bc625d2d3dff2d412bd240aeba29e6193016bcccb340fb38a24e654fb8f6一致。执行工具在Space gate之后读EPD，且源码要求MPS原件state=stopped及精确pipe；本次盘点stdout没有另附MPS原件，故独立MPS释放依据仍应保留Space完整原件链，不能把本文当新GPU查询。
- 实际exit.json exit_code=0；stderr为空；stdout.elapsed_seconds=0.013231667981017381。该0.013s是工具自身读文件/命令段，不是包含Git/booking/SSH在内的整段launcher总耗时。两次readelf与git子命令各exit0，全部为静态解析，没有动态库加载或模型操作。

## 得到的实际事实

1. 目标epd/repo HEAD仍a3f03b9dd5956db92add454f9b3afd5663f84609；不能用发布的ae7工具commit把这个目标EPD源码重标。
2. assets/build/epd-cuda/libcuda_ipc_utils.so存在，359096B，SHA12e4145134ba1697bb745fd51c37a8f275293284d6152c17b42513dd6d07ca20；预期flat assets/build/libcuda_ipc_utils.so不存在。这证明是实际落点与预期路径落差，不是controller缺CUDA_IPC_LIB_PATH参数（该参数已在源码中存在）。
3. readelf -d显示RUNPATH仍指/local/boyjiang/spaceserve-epd-qjh003-20261023/envs/epd/.../torch/lib、.../nvidia/nccl/lib及/usr/local/cuda/lib64。NEEDED包含libc10.so/libtorch_cpu.so/libc10_cuda.so/libnccl.so.2及系统C/C++库；-S输出33个section。没有通过ldd/dlopen证明这些依赖能解析。
4. bin/python为/usr/bin/python3链接，resolve=/usr/bin/python3.10；pyvenv已读home=/usr/bin、include-system-site-packages=false，未输出version字段，不推断其版本已验证。51个普通console shebang仍指旧/local/boyjiang/spaceserve-epd-qjh003-20261023/envs/epd/bin/python。
5. /usr/bin/patchelf存在，仅which观察、未执行修改；已列torch/lib及cuda_runtime/lib文件名/size，不是完整依赖可用性验收，尤其该两目录列表不能证明NEEDED的所有库已闭合。尚需单独受审的最小静态重定位/flat库操作及后续合法CPU/真实GPU Gate。

## 程序偏差必须保留（NON-BLOCKING结果使用限制）

epd-static-publication-verified.json明确记录：本拟以gh做前GitHub API字节核，但gh不存在触发WinError2，PowerShell继续launcher，**事前API核验要求未满足**。launcher本身仍执行ls-remote main=本地commit及Git原blob665e校验，且本次实际命令嵌入字节已独立核；这解释实际运行版本约束，不等于补齐原“前API核”流程。

该文件记录后续GitHub connector在exact ae7 commit读取base64 raw665e，verification明示“after actual static run”。本审查不再访问GitHub，仅确认本地记录及其时间性质；不能把它改写成执行前核验、删除gh失败或声称完全合规发布。应将此偏差随本次raw/结论一同交付；以后命令链应在前置失败时停止，但不为修历史流程追加本次重跑。此次静态事实可用于制定最小重定位方案，不提升到模型/GPU或正式准入证明。

## 本地原件SHA256

|文件（epd-static-inventory/）|SHA256|
|---|---|
|command.json|12312143afcadd42e12c7650e4d6b4527cda190365e164daab2041dab70c02f5|
|input.json|d1012d507bb6f7afc41fcd914c5c3899dfc6f47498393355f542db6523ceea6a|
|stdout.json|e438ec9ab0e18b99286ad03314e0b82e93bbfd7ee7e5a2d4bacca5922f5d2aa2|
|stderr.log|e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855|
|exit.json|a2ebfbd8473baeb3aa1bcf58bd942e3c9a08c2e5e9f3bfee7f72cb7e1acda95e|

GATE_RESULT: {"gate":"actual_static_CPU_inventory","decision":"APPROVE_WITH_NITS","blocking":0,"pre_execution_API_requirement_met":false,"rerun_authorized":false,"runtime_GPU_ready":false}
