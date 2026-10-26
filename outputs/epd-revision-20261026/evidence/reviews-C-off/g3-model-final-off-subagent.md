# 最终实际G3分项审查
审查者 /root/numeric_g3_review，Claude quota fallback，只读；2026-10-26。
## 结论
数值、模型正确性及off路径 APPROVE_WITH_NITS / BLOCKING 0。完整lite观察 REQUEST_CHANGES / BLOCKING 1。不是全局G3通过，不批准B。
## 核验
16 suite各17：272 target+17 reference=289；每suite17 submitted/17成功completed、distinct RID，所有case/input IDs/output token IDs同reference，32/128输出、64/256/512视觉tokens；四单色、C8、四色多图顺序通过。8组RGB before/after同frozen protocol SHA08a641f1bb0c98dca6ba6c6a829caddfe3d642d54643a09fc987eb54adcf4554。boot/三UUID/FP16/4096一致。自然图仅本案例token一致，不保证全语义。
原controller exit1和restart-off-epd缺marker保持，续68同attempt，不重生成221。checkpoint90项重新核验全部SHA一致，缺件/本地差异从远端原冻结字节恢复；差异副本另存，未重跑模型。
## 失败观察
EPD cold/restart全部worker gpu_stream_windows为空，export均0；baseline有320/321窗口。不能把带stream字段的host事件当CUDA事件证明。迁移只源blocks/RID/op，无完整目标索引，不能算纯复制或完整stream覆盖。host dispatch394/393和worker op一一对应，各640 api.output覆盖17RID，无overflow，仅host诊断。
## C-off条件
G1批准失败fallback/G4审失败/G2 consumer delta后，仅既定C-off6000+1200，禁止B/lite/新增GPU预检，不调剂B预算。门禁须model_correctness_passed=true/lite_observation_passed=false/allowed_actions=[performance]，runner强制off。producer49清单适用后续consumer仅经delta批准。fresh预约、boot、UUID、部署SHA、空闲重查。
最终bound_files含producer演进/consumer、numeric及raw、checkpoint90原件、全部16suite+审计/reference+审计/8组RGB/runtime/model-runtime/lite失败raw、旧及续controller/result/RESUME_STARTED/失败归档/后清理/G2及目标CPU/frozen-request-protocol/G4及C_SCOPE/fresh资源快照。
主执行者采纳：完整观察仍失败；不修复或重跑本轮观察，准备C-off批准链。
