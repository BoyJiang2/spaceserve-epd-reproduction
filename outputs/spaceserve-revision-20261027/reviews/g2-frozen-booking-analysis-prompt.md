# G2 分析输入改用终态冻结预约快照
沿用AGENTS3.2.1只读审查，不网络/GPU/凭据/改文件。
小delta outputs/spaceserve-revision-20261027/analysis/analyze_formal.py/test_analyze_formal.py：booking读取由动态evidence/BOOKING_VERIFIED.json改为已G2终态helper在实际结束后xb创建的formal-final-booking-state.json（原运行控制器持有的预约状态原字节快照，不冒称新的API查询）。owner/resource/start/end/cleanup边界检查逻辑不变；input_sources替换动态BOOKING并新增四份终态冻结回执SHA。
原因：08:30/08:58后续只读预约跟进可能更新当前BOOKING，不能让已计算报告的源SHA因正常状态刷新而漂移。动态API快照仍用于实时资源核查，离线分析应绑定当次执行记录；没有修改GPU守卫或预约时间。
20CPU PASS，新增动态current booking变化不改变结果，但冻结执行快照owner不符即全局拒/无CI；其余partial raw/no-global/full CI门槛不变。仍无实际formal raw抓回/分析，新增文件尚待真实helper创建，不伪造metadata。
请G2核新来源及input_sources范围符合已审capture/transfer元数据，无统计降级。只回复结论，主agent落盘。
