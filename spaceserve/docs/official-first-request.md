# SpaceServe 官方路径：下一GPU窗口的最短验证方案

状态：CPU源码与baseline metadata准备完成；GPU运行命令的现场绑定/独立审查尚未完成，本文不授权执行。EPD优先真实请求，两系统同机正式测量串行。

1. 刷新本项目预约与CPU权限、实际boot/GPU UUID/NUMA/占用/端口、已有自有任务、源码HEAD/dirty。模型保持Qwen2-VL-7B-Instruct FP16 TP1、单H20；复用官方目录assets/models下软链接，不增加GPU预算。
2. 先验证指定解释器/local/boyjiang/spaceserve/assets/envs/space/bin/python在选定可用单卡下实际加载路径、版本及_C；导入/--help/ctypes可能触发CUDA，不能在CPU-only阶段执行。此前源码目录未见_C而site-packages已有扩展，仅是静态风险，不提前声称ABI不兼容。若真实加载失败保存首错，再做必要最小适配，不重装整套环境或复制217MB二进制。
3. native使用同一个官方checkout内baseline/vllm-v0.7.2内容树988728…；fork使用adapt/qjh003-v1的66de。只有本项目服务彻底收口且源码clean时才切分支，运行中冻结。明确PYTHONPATH/实际__file__，不能在fork cwd中unset PYTHONPATH后误称已切回site原生，也不能把已查出两处修改的site包直接称pure native。
4. 官方README要求VLLM_USE_V1=1，入口vllm.entrypoints.openai.api_server、enforce-eager；本轮需显式dtype half、TP1及本地模型路径，避免auto精度改变FP16协议。采用本单元独立准备/请求/清理预算；不机械要求先有完整正式矩阵窗口。完整启动监督、身份收尾及单次请求文件须按现场范围冻结审查后执行，不能裸后台启动。
5. 验证单图再多图和并发路由，记录实际视觉/输出tokens，核设备放置和实际重叠。代码中EncoderCore有实际stream_lzc_mask调用；gpu_encoder_worker.py中的stub不代表整个编码路径未实现。
6. 不能靠VLLM_LIBSMCTRL_PATH设成不存在来保证mask关闭：loader还会搜索其它候选路径；EncoderCore目前按libsmctrl_path是否可用决定调用固定四word mask。解耦无mask/有效mask两组必须有可核的真正开关或等价控制，先核实际行为再做最小必要改动。原数组不直接解释为H20已生效的SM集合；按当前设备/配置定义允许集合，再采样验证，有限采样不必覆盖全部允许SM。
7. 已查EngineCore的decoder stream相关mask语句为注释，不能称完整encoder/decoder互斥分区；这也不是decoder实际执行范围的证明。MPS等并发条件需要现场说明与独立资源身份，不能接管或停止未知MPS服务。CPU准备不代替此验证。
8. 只有模型/机制正确、采集可靠、独立G3与正式范围闭合后，才按已冻结完整协议比较native/解耦/有效encoder mask。GPU预约3小时不承诺覆盖两系统全部正式矩阵，失败或时间不足保留原件和断点，不缩减协议冒充完整实验。

[已安装源码审计与baseline来源](../comparison/20261103-native-baseline-source-audit.md) · [官方源码快照](../code/README-official.md)。原生内容身份已通过整树证据核验，目标机仅建立metadata分支，无共享环境修复或GPU运行。
