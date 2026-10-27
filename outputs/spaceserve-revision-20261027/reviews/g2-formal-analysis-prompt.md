# G2 Space整批离线分析候选
先读AGENTS；Claude额度耗尽接替，独立只读本地，不GPU/网络/凭据/改文件。
新增outputs/spaceserve-revision-20261027/analysis/analyze_formal.py、test_analyze_formal.py，依赖已分别G2 APPROVE0的audit_cell.py/block_statistics.py。冻结正式15/model57/numeric18任一字节不改，不部署远端。
功能：15/57/18固定producer+347实际G3consumer绑定SHA；实际formal-target-CPU/FORMAL_STARTED SHA固定（前者6218df252d938b50d3ac5621bda92424094e8e35013de18c19d4a19f975114d8，后者db3714e64c3c1371162b3edc73f420567966dd89db67ad40f6dec67ee9500772）。全54计划单元/36计划target-baseline配对，原始marker/逐请求/显存重审、实际导入/设备/FP16/组件/role/libSM/MPS边界/engineargs、fresh API身份、全局窗顺序和预约收尾边界。
完整54valid+同controller exit0+全矩阵marker+无全局错误才出三时间区组df2区间；partial逐次描述无CI。全局冲突全部比值禁用。记录raw文件SHA/输入SHA、invalid原因、原失败行数，不删失败。只数学/数据候选，不签G4或goal完成。
注意mask decoder在实际预检也加载lib但未证明应用mask，因此decoder可空或exact reviewed lib，encoder必须exactlib；不能称decoder互斥。实际kwargs忽略、保留visual+language decoder、共享主机、trace不反推off限制写入输出。
12CPU测试PASS（统计5、单cell1、整批6）；整批fixture全在workspace临时目录并标SYNTHETIC CPU ONLY，mock describe/verify_inputs仅隔离聚合，绝非正式数据/真实marker。另实际本地verify_inputs已核15/57/18+347原件一致，不分析未抓回formal。
请核验证范围/全局冲突/CI门槛/输入绑定/实际源码记录字段是否匹配，是否遗漏会让报告假阳性的条件；指出必须补的最小测试。此轮没有实际formal raw可评G4。给APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING/NONBLOCKING，主agent落盘。
