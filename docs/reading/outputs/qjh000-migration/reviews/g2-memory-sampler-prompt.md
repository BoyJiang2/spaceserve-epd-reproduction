> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-memory-sampler-prompt.md) SHA256 32c9340ddf6f368591ccc70a0e364deb15fdd04d2167df4c0f6ffdd864af0018。原数字及解释不变。

# G2：正式运行显存采样归属查询最小修复

你是独立只读审查者，先读 D:/Documents/codex/AGENTS.md。不得修改文件、访问 GPU、启动实验或读取凭据；可用 CPU 读取/复算现有原始数据。主执行者 Codex 已实现，不能由你接管实现。

当前目标：qjh000 单H20/Qwen2-VL-7B FP16 TP1 eager，native/Space/Space-mask三组，先1/C1和4/C8六配置1800formal+120warm，经G4后余四点，总5400formal+360warm。原003 EPD A已封存，不改。

Claude本批真实额度耗尽证据：outputs/epd-profile-a/reviews/g4-cuda-report-claude.json（usage_limit_reached，reset22:50）；按AGENTS3.2.1由独立subagent接替，不是跳过审查。

实际失败：正式监督器18837于20:25启动，首baseline1/C1完成300formal+20warm后audit_formal_case拒绝，自动cleanup退出1。gpu-memory1746条，周期median0.396067s/max0.523900s；第二重复起始gap0.310766s大于0.3s，foreign=[]。不放宽阈值、不采用该次性能数据、不把它说成成功。所有原始数据/原used-scripts/旧SHA/日志/设备记录已封存：
- outputs/qjh000-migration/results/formal-memory-failed-20261023T2038.tar.gz，SHA042347e42b5c331cc784e9ac5fff01eb7923a314a057e5f4d0e5f4d51e445d96
- evidence/formal-memory-failure-diagnosis.json，formal-memory-failed-archive.json

唯一实质修改：scripts/monitor_gpu.py，由每100ms扫描整机所有进程/全部后代，改为每次NVML实际返回的各GPU PID查同UID、root的Process身份(含create_time)/祖先关系或同私有pipe的MPS进程。不缓存PID，运行中新增GPU PID每次都会分类。其余schema、100ms sleep、NVML字段与正式审计阈值不变；main guard只为CPU隔离测试。旧版在失败包used-scripts/monitor_gpu.py可对比。

CPU证据：tests/test_monitor_gpu.py全部5项（含真实Linux父子孙、外来进程、新出现NVML PID、MPS错pipe/错UID、root复用/权限消失）；evidence/monitor-ownership-cpu-tests.txt。最初tests目录未部署的实际失败保留在*-before-dir.txt，不是测试通过。实际主机CPU归属路径profile（不初始化NVML）：旧median0.284316s，新median0.0000381s，evidence/monitor-ownership-cpu-profile.json。这些不是GPU/系统吞吐结果。

请核查：
1. 是否确实保留全部GPU进程归属/外来干扰检测，没有把MPS仅按名字当自有或错用PID复用？进程消失应fail closed。
2. 是否足够解释原采样周期和修复；未放宽审计、改模型/负载或调用额外GPU。
3. CPU用例是否覆盖实质风险；main/sample改造是否正确。
4. 若APPROVE，下一步只重新冻结真实源SHA，保留/移走已失败formal目录和旧runtime记录，恢复相同全矩阵从第一配置重跑；不复用失败case，不需重做未改变的模型/SM G3。继续原points G4硬门槛。

输出：APPROVE / APPROVE_WITH_NITS / REQUEST_CHANGES；BLOCKING(文件:行号/理由/建议)；NON-BLOCKING；QUESTIONS。不要修改文件，也不要把CPU mock的时序称真实GPU采样保证。审查正文直接回主执行者保存。
