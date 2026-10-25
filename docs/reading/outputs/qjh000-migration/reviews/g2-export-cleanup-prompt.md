> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-export-cleanup-prompt.md) SHA256 0590c319b4f67f6689e38e303fd259da4caed58fe4ec0cfa8e0f96ef25c9a0ca。原数字及解释不变。

# G2：预检等待真实trace完整导出 + qjh000 pidfd兼容清理

只读，AGENTS3.2.1 Claude额度接替仍有效。不跑GPU，不改文件。
实际cold PID3841088已退出1、MPS stopped、GPU0空；baseline及space标准/C8正确性完成，space同PID/同stream实际first执行已有。三组G3未过，因为stop_profile只发异步控制消息，旧preflight随即stop服务，traces为空，analyze_trace拒绝。原日志/结果保持，未自动跳过。

最小变更：
1 scripts/wait_for_traces.py：从本role实际worker-*.json读取PID并校验native1/fork2，在stop_profile之后停止服务之前，最多300s等待每PID唯一gziptrace。尺寸跨两轮稳定，完整解压校验gzip CRC/EOF后保存SHA/bytes证据；文件缺/多份/不完整失败。不是用HTTP200作为采集完成。analyze_trace后续仍验证真实kernels、时钟和overlap。tests/test_trace_export.py CPU模拟API早ack、gzipfooter延迟，必须等footer；缺worker/重复export拒绝，两项本地/LinuxPASS evidence/trace-export-cpu.log。
2 stop_server.py：现场psutil.wait_procs因pidfd_open EINVAL失败，原cleanup_owned实际精确runID兜底无残留。现仅改bounded polling同Process对象is_running/status非zombie，8s TERM等待、原身份逐项复验后KILL、5s等待仍存则报错；没有放宽UID/root/runID/先全体校验/信号前复验。未改psutil版本。Linux原3项实际CPU身份用例PASS evidence/stop-polling-cpu.log：本run清理、他run/外来子保留。
3 preflight_model.sh仅在profile/stop之后调用等待helper，其他请求/机制协议不变，Linuxbash-n通过。该export等待仅诊断，formal关闭profiler不调用。

请review实际delta并给结论/具体BLOCKING/NON-BLOCKING/QUESTIONS。只批准cold/restart重试及清理兼容，formal仍须独立服务G3/SM有效再重冻结源SHA。当前新driverG2已有条件化APPROVE_WITH_NITS，清理依赖此delta需你复审。
