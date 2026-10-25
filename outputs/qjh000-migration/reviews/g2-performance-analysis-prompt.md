# G2：SpaceServe正式数据CPU核验与统计

只读，先读D:/Documents/codex/AGENTS.md；Claude明确usage_limit接替依据本批，实际g2-model-runner-claude.json与epd-profile-a/reviews/g4-cuda-report-claude.json。不要改文件/跑GPU/实验。
新增outputs/qjh000-migration/analysis/space_results.py、tests/test_space_results.py。正式实验尚未启动；三组cold已G3预审通过，restart刚完整退出0，最终G3仍待审。
脚本只读取正式raw，points阶段6case/1800formal（如3组有效）先G4，之后all扩18case/5400。允许2组fallback但由真实roles.txt决定，不自建marker。

请核：同GPU0 UUID/privateMPS100、三组版本/实际FP16参数/encoder+LM co-residency、加载SM库SHA和worker-MPS-NVML边界；实际engine args与固定协议及各组一致，decoder仍含visual如实记录。逐case复用既有audit_formal_case（300+20/128/视觉token/时钟/显存foreignPID/采样覆盖），新补RGB前后/同API及跨组、真实repetition计时首尾包含/吞吐meanSD/latency合并300inclusiveP50P95/所有本项目GPU进程采样峰值、代码SHA。
同图片/processed IDs按warmup+repetition+index比较，输入不同拒绝；输出不同只准确列key，不假称所有输出等同。相同负载下config除输出目录外逐字一致，所有role的实际engine args一致。正式mps-start是daemon启动记录state running，与结束时stopped不冲突。
3项新CPU测试PASS evidence/space-results-cpu-tests-fixed.txt：stdlibquantiles对照、真实cold identity拷贝后错UUID/错lib拒绝、旧sealed2B原数据格式fixture统计通过和RGB改动拒绝。fixture仅模型名/设备元数据改为7B/0，不冒充7B实测；首轮device7被新守卫拒绝的日志space-results-cpu-tests.txt保留。先前5项formal守卫测试仍有效，不为节省时间跳验收。

原实验/源代码不改，新统计尚未运行全数据（formal不存在）。批准后仅points完成时在qjh000 CPU运行，G4审actual再允许其余点，不能拿G2作为结果通过。请给结论/具体BLOCKING和行号/NON-BLOCKING/QUESTIONS。
