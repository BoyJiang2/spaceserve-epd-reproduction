# actor引用修正页：独立文档G4

reviewed_at_utc: 2026-10-30T03:42:22Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，仅文档/证据展示，不授发布G5、部署、cleanup或新CPU/GPU执行。**

README `epd/validation/qjh003-cpu-lifecycle-ip2-20261030/actor-reference/README.md` SHA `bb4927a859552561d512482f321eb3179bd9f60f378e93a7bd9ef78ca7b6b87e`；目录7文件/48122B，完整文件SHA在本审JSON。本人只本地读文件、JSON/tar/已有日志、链接和SHA，不运行项目/测试、网络、SSH、Ray、信号或GPU，不改源或证据。

页面将实际producer固定2d2f、11–16 CPU/CPU50nice10/CVD空/actor num_gpus0，与本地handle修正、未发布/部署/真实复测明确分开。实际连接IP2成功且actor_ready后约60.156ms观察GCS DEAD、原protobufall references removed，与根目录真实失败readback相符；这不是修正版已经通过。原terminal exit1/0-of-4、父ACK5秒超时均保留；完整封包的实际0/stderr.log确有对应TimeoutError，不是仅从源码预测超时。

修正描述精确为scenario返回expected＋actor、main持有至ACK，不改lifetime/GPUbackend、不延长超时。源码G2已另审精确54fd9f driver/7d2709 test通过，本G4不把其当运行证据。176为真实final summary执行数，mock/单元测试不能代替实际Ray四场景。before的weakref失败与API契约ERROR、漏EPD_CPU_TEST_TMP的36环境ERROR原日志保留，不抹去失败；补环境后的176/OK也不冒称一次首跑成功。

页面driver-events、terminal、inventory与实际renewal失败capture原件逐字节/JSON语义核同；before/tests/env-error三日志与根目录原件字节相同。完整384875B包实际SHA `5d9b2130bd6ab02c4a2706428d1cd6880b8c218619cdaf3531979a229f46906e` 与README相符，12 tar成员＝11物理原件＋1生成inventory；本人逐inventory大小/SHA核同。页面没有把此新11raw封包混成旧8raw连接失败包。所有相对链接实际存在。

封包当前仅本地保留/尚未上传Release的措辞明确，无虚构下载链接、性能或GPU/IPC/native36 PASS。后续完整结果交付应保留这个未上传状态或提供真实资产链接，不能在源码发布后自动改成已上传。源修正版需要新版本/部署/执行/实际G3；现失败仍需另审创建WAL后的真实收口，不可由文档批准清理进程。

GATE_RESULT: {"gate":"G4-ip2-actor-reference-documents","passed":true,"decision":"APPROVE_WITH_NITS","blocking":0,"readme_sha256":"bb4927a859552561d512482f321eb3179bd9f60f378e93a7bd9ef78ca7b6b87e","old_failure_retained":true,"new_Ray_success_claim":false,"publication_approved":false,"cleanup_approved":false,"remote_CPU_execution_approved":false,"GPU_approved":false}
