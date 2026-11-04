# Space C4交付、角色放置及Nsight方案独立审查

审查者subagent /root/official_epd_runtime_review_1104，2026-11-04。只读转送材料审查。输入为69raw/SHA/git-main真实核验、角色日志与原NVML匹配、独立Nsight fork C4诊断方案（单卡/原模型协议不变，900秒单元+300秒CPU保存；目标进程树CUDA/NVTX，不采全系统/MPS/权限变更），并明确源码/工具精确G2尚未完成。返回原文：

1. **C4交付 G5：APPROVE / BLOCKING 0**，限 `61f3fe66a2193e9884f3e1f493040c84f21aa477` 的69文件。转送记录支持raw大小/SHA全部核同，API限流失败保留后以 `git ls-remote` 核main；不把403称为发布失败，也不称本轮完成Release指纹核验。

2. **新增角色放置证据 G3/G4：APPROVE / BLOCKING 0**。角色日志PID与原NVML样本对应，支持EncoderProcess和EngineCore在同一GPU驻留，以及该时刻的显存观测。14／4个样本不证明连续峰值或计算重叠。派生样本另存SHA、旧manifest保持历史快照正确。

3. **Nsight诊断 G1：条件式 APPROVE / BLOCKING 0**。范围和预算合理，但G2须明确：
   - 请求窗口与Nsight时间轴的对齐方法，以及角色PID→CUDA context/stream/kernel归属；不能用初始化或enqueue重叠代替请求期活动。
   - 独立context若不能排除抢占／时间片影响，先限定为“trace报告的kernel区间重叠”，不直接升级为SM同时执行证明。
   - collector／导出与现有清理的顺序、失败留证及共同截止；不为采样新增权限、MPS或系统级追踪。产物不可用即记录失败。
   - 大产物只留服务器并按Release规则交付；fresh满足1200秒余量后才派发。

以上均仅依据主执行者转送材料，未独立读取、联网核验或操作GPU。精确profile runner仍待G2；不代表正式性能、mask或总goal完成。
