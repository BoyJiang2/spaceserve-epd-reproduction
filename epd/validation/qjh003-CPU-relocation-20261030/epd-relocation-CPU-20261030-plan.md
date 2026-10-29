# EPD现有环境重定位：当前本人CPU预约内的最小续接

Space当前没有模型或正式测量，GPU2被第三方占用；Space源码24b保持冻结。此前EPD apply因旧CPU窗口冲突在资产写入前exit1，未发生成功迁移。原封存/失败材料与旧配置不改。

目标是完成已有重定位，不新增GPU工作：56项console/activation路径替换、从原nested IPC库复制出单独flat库并设置已审RUNPATH，原nested库/旧root/权重不变。沿用61项startup allowlist、3条Python links、依赖存在/原文件SHA/未知startup拒绝/唯一stage/atomic rewrite与逐项journal、apply120+30和verify60+30。此结果仅静态启动资产就绪，不代表Ray、dlopen、CUDA IPC或模型通过。

实际API1793311978453确认本人CPU票bk-20261029T1809-58743aa0，h20/qjh003/cpu/boyjiang，1793304000000至1793329200000（04–11）。旧direct_user_instruction 16–17 scope不可复用。只申请以下本地修改与测试，具体远端另G2：

1. 新增独立配置epd/migration/qjh003-asset-relocation-20261030.json，原61项/3links/库pins/RUNPATH不变，唯一stage改asset-relocation-cpu-20261030，cpu_permission明确绑定上述实际本人CPU票。原20261029配置保留。
2. tools/relocate_epd_assets_cpu.py仅改CPU scope校验/CONFIG_SHA适配新配置：window_end拒旧许可、正确类型及精确票字段；cpu_permission在fresh实际API中必须找到完全相符本人票，并保留他人CPU/整机冲突检查、完整budget+120收口。真实own票通过后claim的reservation_claimed才可为true，不能沿用旧direct scope的false/虚构授权。
3. 先本地反例/回归，独立源码G2。只在独立EPD分支形成精确commit/push/API字节核，不改变Space main/HEAD24b或其服务器checkout。实际维护用该发布commit的tool/config原字节，经新命令执行审查与fresh票/现场/一次新output，再单次apply；success及原件下载SHA/独立实际审计后，另fresh才verify。旧失败命令不重发。
4. 实际CPU helper可以按已发布Git对象传入执行，必须记录维护tool commit与EPD runtime repo实际commit分别是什么，不把辅助源码传入冒充整个EPD repo已部署新版本。此时不导入EPD Worker/Ray/Torch、不执行flat IPC库、无CUDA/NVML操作。
5. CPU50/nice10，不更改其他环境/系统驱动/他人进程。只在Space无活跃模型/正式GPU单元时开始维护；一旦Space恢复优先，在这次有界CPU单元完成/受控收口后再GPU，不能让远端EPD维护干扰正式测量。各操作都须留足CPU票11点前120秒，不自动扩大GPU预算。

本步骤直接清除真实CPU Ray lifecycle和后续native36运行所需的环境障碍，不将它当完整backend或性能验收。后续仍需G1/G2/Git-first部署CPU Ray生命周期/实际native36/G3及模型与公平PD对比。若任何实际原件与旧allowlist不同，写前拒绝并保留证据，不自行修权/覆写或循环重试。

当前未修改重定位源码/配置、未执行新远端维护。请先独立G1裁决本地续接范围，避免套用旧16–17许可。
