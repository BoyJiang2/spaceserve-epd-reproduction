# qjh003 迁移后的 SpaceServe 预检（2026-10-29）

完整313请求已实际exit0，[独立实际G3](reviews/gpu-http-model-g3-actual.md)已通过（APPROVE_WITH_NITS/BLOCKING0），[报告G4](reviews/gpu-http-report-g4-g5.md)已审；精确发布仍待G5。**正式性能0/54**，没有本批吞吐加速比或正式延迟对照。历史性能对照仍在[SpaceServe独立项目页](../README.md)与[comparison](../comparison/README.md)，不拼接跨机器、批次结果。

| 对照路径 | 冷启动 target / diagnostic | 重启 target / diagnostic | 正式性能 |
|---|---:|---:|---|
| 原生vLLM | 15 / 36 | 15 / 36 | 未运行 |
| 编码器解耦 | 15 / 36 | 15 / 36 | 未运行 |
| 解耦＋有效encoder mask | 15 / 36 | 15 / 36 | 未运行 |

另有7条原生reference，总计313；90个target均HTTP200；共有5条输出与reference不完全相同：四个非baseline角色的coco-4，以及cold-space-mask的一条cat，验收采用既定输入/长度及语义契约，不能声称全部token逐项一致。实际生成32或128tokens，216条为带预热的诊断请求，不作为正式性能样本。单H20 GPU0、Qwen2-VL-7B-Instruct、FP16/TP1/eager。三组共用私有MPS100%，仅正确性客户端统一force_close、不重试POST，性能benchmark代码没有这项修改。

[六角色逐请求、设备及trace摘要](raw/results/preflight-models-attempt1/) · [版本/输入配置](raw/configs/) · [实际启动与exit0](raw/evidence/models-attempt1-exit.json) · [受控释放](raw/evidence/model-attempt1-terminal.json) · [源文件清单](source-files.json)。完整trace与二进制尚未上传Release，不使用候选下载链接。

实际服务记录独立encoder与language worker在同一GPU；四次解耦诊断均观察到CUDA kernel时间重叠。MASK_OFF=56是在本机driver580.126.20/DriverAPI13000上依官方port方法测得，[服务同stream撤销/重施/首执行证据](raw/results/preflight-models-attempt1/cold-space-mask/device-records/SM-validated.json)已通过实际G3；不外推其他驱动或机器。encoder mask不能说明decoder互斥或完整论文分区，诊断profiler overlap也不能说明关闭profiler后的性能收益或因果瓶颈。decoder仍驻留visual权重。

本轮producer为`beadff9c4cc4693cd2ea8675020f757e313659e8`，外部helper为`236e8896d91bdea9b36fd9bc551ff3dfea9f25a4`；模型94文件manifest为`0590bc625d2d3dff2d412bd240aeba29e6193016bcccb340fb38a24e654fb8f6`。完整原始tar.gz已安全下载355691974字节，SHA256 `799d1774f1e45a82dfdf9c516c7f757c5911d6e4cf8e769ccf5e172815edeb88`；260个model inventory原件与本地全部匹配。

前序失败不抹除：原DriverAPI拒绝、首模型共享资产路径错误（0请求）、路径修正后mask C8的一次ServerDisconnected（124尝试/123响应）均保留在[前序失败原件](previous-failures/)中。force_close后本轮通过，只支持此处缓解措施有效，不能单凭此证明旧错误的根因。另一本地SSH观察器在远端正常完成后timeout；实验真实exit0与观察传输错误分别记录。

环境和模型权重已迁至固定`/local/boyjiang/spaceserve/assets`，运行在`runs/space-http-20261029`；[维护代码入口](../runtime/)、[迁移流程](../migration/README.md)。复跑需在新有效预约中，用上述producer与本批配置固定输入，重新经过CPU、numeric、独立模型G3；不能复用本批marker批准新运行，也不能原样使用已到期预约。正式54单元仍需要完整201分钟准入，本窗不缩矩阵。

EPD另有固定目录与原始资产，但flat IPC/RUNPATH/shebang尚待重定位，不代表已运行可用；与本Space预检分开验收。整体项目目标未完成。
