# qjh003 EPD环境重定位：2026-10-30 CPU窗口源码

状态：代码与10项本地Windows CPU fixtures完成，真实apply/verify尚未运行，不是Ray/CUDA IPC/模型就绪证明。当前Space正式优先；此分支不改变Space main/部署版本。

代码入口：[维护工具](../../../tools/relocate_epd_assets_cpu.py)；[新配置](../../migration/qjh003-asset-relocation-20261030.json)。旧20261029配置和封存材料不改。旧run_epd_relocation_cpu.py只适用于其原冻结版本，不能当本批启动命令。

新配置仅更新独立stage与本人04–11 CPU预约范围；61项startup/3条link/56项rewrite、原nested IPC库及RUNPATH规则保持。工具写前必须fresh核实际本人完整CPU票及冲突、原件SHA/所有权/预算；成功claim记录真实预约，不从旧人类direct scope推断。apply120秒加30秒收口，verify60秒加30秒，CPU票结束前120秒不开始新工作。

复核代码：在epd repo对应根的tools目录执行python -B -m unittest test_relocate_epd_assets_cpu -v。before日志记录旧direct-scope模式不能满足新增owned-ticket要求的4个反例；after是中间换行整理前记录，final及tests.json才绑定最终源码。所有结果仅本地fixtures。

本次真实维护命令须另获精确执行G2，使用已发布tool/config原件与新的实际snapshot/唯一output；不得直接重发旧失败命令。实际执行后会追加原始证据、SHA及结果审计。尚无可称已成功的目标端复跑结果。
