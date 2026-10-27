# G2 partial逐次原始散点实现
沿用AGENTS3.2.1只读接替Claude，不网络/GPU/凭据/改文件。
G1方案已APPROVE0，见g1-partial-raw-plot-subagent.md；不改GPU/model/load/order/budget/统计门槛。本批正式raw尚未抓回/看性能数值，只有进度marker计数。
变更analysis/render_report.py、test_render_report.py、partial-display-plan.md：仅partial+no global_errors+valid>0画raw-observations PNG/SVG，六负载2x3，x block0/1/2轻微role偏移（明确非真实时距），每点单次成功req/s，无连线/均值/拟合/CI，y0起；每panelvalid/9和每block的missing/invalid N,D,M列全，图外文字非补零。主标题PARTIAL+no aggregate inference，合成大字SYNTHETIC，不称完整位置平衡已达成。full54原图/CI逻辑不变，global error连raw图也不画。
19整体CPU PASS，最新renderer3单测复跑PASS。partial缺一项无总体图/CI但raw图，full三比较/0.8退化保留，global冲突无任何图。work/space-partial-plot-SYNTHETIC-v2-20261027额外52/54 fixture含1invalid+1missing，实际view确认标题/状态标注可读；初版图例遮住SYNTHETIC已修（原失败预览保留在无v2目录），新图用颜色+形状及独立标题行说明，未用真实数据。
patches/README只是更新CPU展示文字并新增link，configs/patch-delivery-manifest仅对应README bytes/SHA更新，其余4项字节SHA不变。请核展示代码/筛选无偏/全部缺失/无虚假推断/截图排版，给APPROVE或修正，非实际G4。
