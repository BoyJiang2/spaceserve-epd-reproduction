> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/epd-profile-a/reviews/g3-subagent.md) SHA256 e858a272df9976a6716bfa26002fed613073765f53a016a6ed5428da23b8d554。原数字及解释不变。

# G3 观测预检实际验收

实际审查者 /root/profile_instrument_review，Claude明确额度耗尽后依AGENTS §3.2.1独立只读接替。直接检查源码、原始JSON和8份SQLite，通过mode=ro查询复核，未运行模型/实验/GPU。

结论：G3 APPROVE_WITH_NITS，BLOCKING为0。正式2400请求与扰动判定尚未完成。

- 两批完整结束，第二批EPD与三个baseline的GPU worker PID全部更换，boot ID相同；仅证明服务新进程启动和一次服务重启，不代表主机重启。
- 通过同进程correlationId关联CUDA runtime/GPU活动，API在同线程同步worker NVTX范围内；关联无范围歧义、runtime关联键无重复。两次EPD E/P/D kernel分别8690/4725/56636与8690/4725/56990；embedding/KV迁移分别关联21/7336次CUDA memcpy。六份baseline trace各有关联prefill4877、decode52742个kernel。
- 全部120请求的EPD E/P/D或baseline prefill/decode均有实际launch关联；原始响应rid/token/API时间戳与NVTX逐项一致。
- 八trace均唯一完整capture范围，所读NVTX和GPU活动均在范围内，GPU尾部未越界；nsys-rep和SQLite均存在且非空。
- 独立逐条比较120个target/reference，输出token IDs、处理后输入IDs和颜色路由一致；RGB前后一致，跨系统和两采集的20张RGB指纹相同。
- trace GPU PID与runtime相符，runtime含相同三张UUID/boot/cuBLAS路径；物理UUID来自实际nvidia-smi PID映射。used-scripts中的observe/instrument/runner与当前版本字节一致。

证据：results/pilot-metadata/、results/pilot-metadata-restart/，evidence/g3-pilot-acceptance.json。更早缺metadata/stop超时pilot不用于批准，另保留诊断。

非阻塞建议及处理：

1. 当前自动验收仅做主要存在性/布尔/部分样例；本次独立审查已直接核对全部原始请求、API与capture边界。后续验收纳入同等完整检查，不能只相信passed。
2. Nsight deviceId为进程局部编号，不以TARGET_INFO_GPU.id直接连接为物理UUID；使用runtime的实际GPU PID→UUID。
3. memcpy关联仅证明原生路径提交并执行GPU拷贝，不单凭此宣称带宽/逐字节内容一致/性能因果；正确性限定已测固定案例。
