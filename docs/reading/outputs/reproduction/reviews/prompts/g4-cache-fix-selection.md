> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/reproduction/reviews/prompts/g4-cache-fix-selection.md) SHA256 6946a96f95725651f83ddfbb1a8af0dabdabdf2901be2c37a7a79d3fcdaa9e3d。原数字及解释不变。

独立只读审查准备，Claude额度接替按AGENTS3.2.1授权。先读 D:\Documents\codex\AGENTS.md，项目根 D:\Documents\codex\2026-10-23\new-chat-2。不改文件、不运行实验/网络/SSH/GPU、不读凭据。

补测正在两台运行，此时尚未宣称数据通过。请先预审离线选择/验收代码与报告模板，指出阻塞性逻辑问题；数据到齐后再进行G4正式复审，不要提前批准实际结果。

文件：outputs/reproduction/scripts/audit_cache_fix.py、audit_matrix.py（low_load_only）、summarize.py（--cache-fix与source_kind/source_case）、compare_outputs.py（同选补测低负载路径）、verify_delivery.py、make_report.py。补测源脚本run_cache_fix_h20.sh、rgb_cache.py、check_rgb_cache.py已由G2 APPROVE，记录reviews/subagent-g2-rgb-followup-20261023.md。

选用政策：原始11矩阵46配置13800正式不改写；新补测4单配置矩阵1200正式，全归档合计15矩阵50配置15000正式1000矩阵内预热。正式报告仍选46配置13800，其中有效12000、历史L20诊断1800；旧H20低负载1200原始请求保留但被替代，不再参与性能结论。原矩阵validity.json将加case_overrides只标旧images1-c1，新的data/cache-fix/两host四role替换报告与输出配对的同负载行。summary记录source_kind/source_case，superseded-summary另存旧行。有效配对仍5400，另历史诊断1800，共7200，新的低负载配对600来自补测。

audit_cache_fix独立重算20COCO的RGB SHA，对照每服务前后实际cache proof，并将API pid对照runtime-config的实际server pid、GPU UUID/boot/version对旧机制验收，检查每单配置20+100x3/60新固定服务用例/结束GPU空闲/7份已审源码SHA。旧G3与SpaceServe证据不重跑。

当前只给“代码预审发现”，不能给G4数据批准。聚焦来源替换是否混批、计数/统计口径是否一致、全缓存预载与其它负载延续性的证据是否足够。指出文件行号、理由、最小处理。不要仅因模板写未来已完成而判为伪造：make_report读取补测通过证据才可生成，尚未运行。
