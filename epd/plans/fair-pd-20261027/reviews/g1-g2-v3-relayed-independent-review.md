# v3 独立G1/G2：主线程完整转交

实际来源：主线程/root向实现者/root/epd_pd_followup转交。独立审查者agent标识未在该条消息中提供；以下是收到的完整原文，不冒称实现者自审或未取得的原始审查全文。

> 独立G2 v3 REQUEST_CHANGES仅Blocking1，原3项修复方向均落实、40sourceSHA匹配、core融合KV未变。B1 admission84只核20请求覆盖，experiment_plan176仍直接用summary requests_per_s；保持raw+receipt不变只改该rate巨大finite能改winner。请v4冻结明确measurement start/end外层窗口+16测量rows、按统一真实client同clock口径重算16/duration评分，并核/拒summary rate不符；不要未说明用min-submit代替原benchmark外层窗口。补只改summaryrate必须拒绝，非恒定fixture同时生成原始计时，定清calibration client要实际记录的raw header字段。保留v3原字节，原预算1440/340不变，不GPU/push。另v3G1已独立APPROVE0，两个nit关闭；计划层无新阻塞，仍需最终代码/collector/guard/Gitfirst及用户确认三卡候选预算后才GPU。请保存真实review原文，v4CPU/manifest/patch完成交主线程重审。

处理：仅在v4新版本加入实际client外层窗口raw header、计数/时钟/边界绑定与16/duration重算，拒绝只改summary rate。v3及之前原件保留，核心融合/KV代码不变；预算不增，不GPU/push，不由实现者批准自身G2。
