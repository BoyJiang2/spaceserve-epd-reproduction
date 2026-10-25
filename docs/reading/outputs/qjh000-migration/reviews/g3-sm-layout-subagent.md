> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g3-sm-layout-subagent.md) SHA256 f86d9ff56d8d04bd48b3d27090ddcdec27302a1df53e9f26e6da26bc9901c3ef。原数字及解释不变。

# G3：原生低12位SM布局与恢复

实际审查者：独立subagent `/root/profile_plan_review`；明确Claude额度耗尽后接替。只读原始数据/源码与实际hash，不运行GPU/实验，不改文件。

结论原文：APPROVE_WITH_NITS。G3原生逐位布局子范围BLOCKING：0。

独立重算六份JSONL，未使用末行summary布尔值作依据：两模式各3次exit0、stderr空；默认78，12次逐位恢复及组合后恢复均为原78集合。bit0/1/2/3/9/10/11各少2，bit4–8无变化；组合0xfff均64、少14。模式内三次完整集合稳定。无MPS有效单bit移除集合两两不交，并集精确为组合移除集合 `{0,1,2,3,14,15,16,17,28,29,30,31,42,43}`；未跨模式比较物理位置。

身份：qjh000、API12020、535.161.08、GPU0 UUID及boot一致。MPS daemon3671028/server3671035日志含实际probe PID3671034/3671104/3671116、active-thread100，最终daemon/server exit0；owner stopped、结束GPU表为空、supervisor finished child_exit0。3个二进制hash匹配，8份当前脚本与实际运行SHA逐字节相同；probe和服务库同SHA529e2502f633b0d7ef07db2848c64e42154cea73992a794c27a31d0361e5e7c5。helper无cudart导入/导出；固定revision符合约定。

NON-BLOCKING：固定源码error_at_line隐式声明编译警告保留，6次实际未遇该错误路径。仅当前低12位相关布局，不推断全TPC拓扑/64:14性能比例/完整SIS。

不批准7B服务、SM_EFFECTIVE、第三组或formal；实际服务stream及首次encoder执行仍另G3。另范围stop-helper B1不因本G3关闭。
