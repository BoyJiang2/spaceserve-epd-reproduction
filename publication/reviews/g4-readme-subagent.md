# G4 根README baseline对照

独立只读审查者 /root/profile_plan_review，依本次Claude weekly quota接替，无远端/GPU/改文件操作。

APPROVE_WITH_NITS，BLOCKING0。逐数核Space6行吞吐均值/样本SD/相对变化、6行TTFT/TPOT P50与space-all.json全部一致；EPD off2行吞吐/SD/比值/延迟及4个on/off扰动百分比一致，高EPD−5.0027158%及受限用途保留；展开5张历史表与原reproduction/report.md原文一致。

host/model/GPU预算、正式/诊断与缓存替代范围、负值、输出差异、encoder-only非SIS、固定顺序/时间漂移与因果限制均清楚，无重聚合或跨批排名。

NON-BLOCKING：延迟表旁补P50合并300正式请求，TTFT为服务端首token减客户端提交、不含首token回传。主执行者已原义采纳，不改数值。

链接落盘/Release真实访问/发布状态仍待G5和远端验收，不代表已上传。
