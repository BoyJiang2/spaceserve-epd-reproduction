# 04–10 window admission 小组件 — 独立G2

reviewed_at_utc: 2026-10-29T18:27:24Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，限纯准入策略小组件；不是完整启动器、实际runtime Gate或GPU许可。**

独立SHA重算：tools/space_window_20261030.py `b2fa9d497861360c5480e868c71e03bf6116acee085c49880755a971af908ef1`；tools/test_space_window_20261030.py `7e7e4ccfac58951d6e49fc684c9f92cfc5f2fb390cc5ff1312fefe6501b8a07a`。只读核两源码、proposed配置、已审G1及space-20261030-window-cpu-tests.log/json；未测试、网络、SSH、GPU或改实现，仅保存本审查。

## 核验结果

固定newrun/qjh003/UID2147/GPU2 UUIDc005、04–10 exact GPU a2228913、CPU0–89/NUMA0/mask56和禁止temporary scope，符合已审参数子集。snapshot必须origin/read_only、整数observed、04后不未来且<=300秒；resource须唯一h20/qjh003/node/active/8卡。本人CPU58743aa0/04–11与GPUa2228913/04–10均exact owner/node/lane/start/end且唯一；缺失/重复/错误归属拒绝。所有他人CPU/GPU/整机预约在当前工作+120秒清理区间重叠均拒绝；边界半开区间处理正确。

phase budgets prepare240/cpu240/numeric900/model1800/formal12060秒，finish=now+(work+120)*1000不得越10:00，不能根据CPU11点或GPU后续票延期。formal最迟END-12180000=06:37:00，即201分钟工作预算到09:58，加120秒清理预算到10:00；09:58是最迟开始收尾/停止工作界，不承诺所有基础设施故障下此时或10点已实际释放。实际终态仍须进程身份/显存/MPS原件证明，异常如实报告。

返回source_or_runtime_Gates_granted=false。没有文件写入、进程启动、GPU导入、信号、cleanup或marker生成。与G1“04前不占他人、06:37赶不上不缩验证、主窗硬界、不自动延期”一致。

本地日志确实9项Windows CPU tests/0fail/0error，JSON记录exit0与上述两精确SHA一致。独立审查没有重跑，也不把此日志当真实Linux/POSIX/Ray/GPU。

## 非阻塞边界与建议

1. validate只检查配置的窗口/资源子集，不核完整配置SHA、state/allowed_actions/source_commit/源码闭包、mask兼容性proof、hostboot/实际idle/NUMA或阶段G2/G3；这与小组件范围相符。最终launcher必须另核完整指定配置和源码版本、真实API来源、旧工具的实际Gate，不可将validate成功升格为“完整配置/运行已批准”。
2. test_no_late_extension_even_if_owned_ticket_exists当前fixture并未实际附加extension ticket；测试验证的是now=END拒绝，没有证明名义上存在延长票的fixture分支。源实现硬END本身不依后续票，故无代码B。建议测试名称改为按实测含义，或在该fixture加入真实结构的owned10–11票后保留同断言。
3. test_wrong_resource_gpu_profile_and_auto_extension覆盖的是错误GPU/profile/temp/newrun，不实际变resource；resource唯一/active/node/count逻辑已只读核，未来若声称有对应反例测试应添加或收窄名称。当前日志只能称9 Windows测试，不能声称穷尽准入。
4. 后续完整launcher须Git-first、04后真实fresh双lane、逐SHA/实际CPU与numeric/model/正式Gate/预算和受控释放。不能仅以此组件存在或拟定自动任务当GPU执行授权。

GATE_RESULT: {"gate":"G2-space-20261030-window-policy","decision":"APPROVE_WITH_NITS","blocking":0,"source_sha256":"b2fa9d497861360c5480e868c71e03bf6116acee085c49880755a971af908ef1","test_sha256":"7e7e4ccfac58951d6e49fc684c9f92cfc5f2fb390cc5ff1312fefe6501b8a07a","scope":"pure_window_admission_component_only","GPU_approved":false,"runtime_Gates_approved":false,"formal_approved":false}
