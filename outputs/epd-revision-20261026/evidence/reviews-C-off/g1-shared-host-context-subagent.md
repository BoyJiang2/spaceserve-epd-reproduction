# 实际独立 G1 共享主机范围补充
审查者 /root/profile_plan_review；Claude额度耗尽既定fallback；只读。
结论 APPROVE_WITH_NITS，BLOCKING 0（有条件，非模型G3/正式批准）。
最终模型G3后可按共享主机条件继续原B/C预算，C仍须B结果G4分支门槛。
每cell计时窗前后记录全机GPU占用/利用率、host load、available memory与swap；共同采集流程，窗外执行。维持所选三卡外来PID即停，固定顺序和失败规则。无需增加连续全机监控。
实际affinity0–179/Mems0–1只证明设置一致，不证明竞争/实际内存放置；只能称共享主机条件相对观测，不能称主机隔离、纯observer开销或内部阶段因果。新增实现先G2。
主执行者处理：采纳，run_cells.py新增host_snapshot候选，尚未部署，因最终lite G3新缺口待分支决定。
