# EPD CPU资产重定位恢复准备（未执行）

旧apply在实际其他用户CPU10–16预约冲突处被guard拒绝，未到资产变更。原失败与原12点scope保留，后者已过期；不是迁移通过。

本候选仅将同一维护工具/配置的直接CPU授权窗口改为北京时间2026-10-29 16:00–17:00，增加开始前拒绝，保留61文件/3链接SHA、56必要文本替换、原nestedIPC与flatcopy/RUNPATH/NEEDED检查、CPU50/nice10/1GiB、apply120秒/verify60秒与120秒收口。用户授权未预约CPU使用；仍须执行前fresh确认无其他CPU/整机冲突，不能拿GPU票代替该检查。

入口：[控制器](../../../tools/run_epd_relocation_cpu.py)、[静态重定位工具](../../../tools/relocate_epd_assets_cpu.py)、[固定配置](../../migration/qjh003-asset-relocation.json)。控制器核实际main/Git源码、配置及自身字节，要求事先真实API字节验收文件；新本地raw以resume16命名，远端固定stage不换名，不删除原claim来重试。维护入口不是GPU实验启动器。

[本地10项CPU测试](claim-fixed-result.json) PASS/0skip：真实本地文件fixture走到apply的stage/claim写入，OS身份/资源/信号均mock；先确实复现独立G2发现的NameError，再恢复permission绑定一行，证明实际claim包含原始授权，随后按预期缺依赖拒绝且未生成flat库。修复前[原始失败](claim-regression-before-stderr.log)完整保留。其余覆盖窗口前/结束/收口余量、旧scope拒绝、CPU冲突、启动代码、claim持久化和终态不覆盖。均无真实SSH/API/GPU或目标资产修改。

[G1](epd-relocation-resume-g1.md)、[G2及阻塞关闭](epd-relocation-resume-g2.md)批准本地候选；尚未实际apply/verify，需精确G5/Git-first/实际CPU准入才能执行。成功也仅是静态资产修复，不能称Torch加载、native36、selected360或公平PD已通过。
