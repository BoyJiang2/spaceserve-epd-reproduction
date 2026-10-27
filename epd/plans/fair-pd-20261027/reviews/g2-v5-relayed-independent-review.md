# v5 独立G2：主线程完整转交

来源：主线程/root向实现者/root/epd_pd_followup转交；本条未提供独立G2审查者agent标识。以下保存收到的完整原文，不是实现者自审或未取得的原始审查全文。

> 独立G2 v5 REQUEST_CHANGES/BLOCKING2（本地候选，未部署GPU）。请保留v5，在v6仅编辑修复/新增测试（按新偏好不本地跑suite，targetCPU待合法qjh00118后条件窗口+已审commit）。B1 selected_g3.py115–136/215–230：只验3proc/role，无request endpoint→实际API/worker PID/UUID绑定，cold和restart各未要求三baseline端点覆盖；现成功fixture没endpoint，所有请求打一副本也过。修实际服务endpoint manifest与身份绑定、每request实际endpoint核对、每session三副本覆盖，补missing/all-one-endpoint拒绝。baseline客户端均衡分发约束也请在与现有raw/command接口一致处明确，别只把三worker存在当三副本参与；生产controller未接线继续blocked。B2 selected_g3.py137–141/171–175/205–213/232：session UTC/release未验finite，NaN绕大小比较；1600s从声称cold-start计而非实际claim起点；snapshotUTC-monotonic与session边界未核，系统间未要求上一个release后再start。修严格类型finite、持久claim实际start/deadline、同boot实际clock anchor对齐、cross-system互斥顺序，补NaN/超claim/错clock/overlap反例。其它candidate failclosed/ledgerNVMLlazy和无signal路径方向认可。请保存完整来源，v6可静态形成新manifest/patch/审查说明，报告测试未执行，勿把v5 13旧PASS标v6。另需准备最小远程CPU runner单元（可分后续小目录）：仅已审指定commit在qjh001独立CPU50/1GiB/300s+30cleanup，空CUDA、禁止GPU包/服务，记录实际test IDs/rawlog/exit/source前后SHA回传，不自行远程。CPU落点G1已条件APPROVE，旧四系统控制域18实际释放+无新接管/CPU50无冲突+freshCPU票15–21+19他人GPU窗前safe必须先验证，当前未handoff不执行。不要改v1-v5/Space/AGENTS/其他项目控制域/预约，不push。

执行范围：v6仅本地编辑/静态材料和未执行测试；v1–v5冻结，不自行远程/预约/push/真实GPU。条件CPU落点批准不等于实际handoff或执行许可。
