# EPD CPU 重定位当前票据适配：源码 G2

reviewed_at_utc: 2026-10-29T22:24:20Z

reviewer: 独立 Codex subagent `/root/fallback_g3`，按 AGENTS.md 3.2.1 接替 Claude 额度耗尽后的审查；本人未实现此变更。

**APPROVE_WITH_NITS / BLOCKING 0，仅通过下面三文件的源码及已有本地测试证据范围。不批准发布、远端 apply/verify、GPU 或环境运行时验收。**

## 精确范围

|文件|实际SHA256|字节|
|---|---|---:|
|`tools/relocate_epd_assets_cpu.py`|`0e3031089b7e523309b4cc3fcaab2b91f4ba4382963778cf22ea78cba647acec`|17729|
|`tools/test_relocate_epd_assets_cpu.py`|`fff8d0e122f7a772999305ee952964a257c4075b4fcd97852e61b704d848eacb`|9321|
|`epd/migration/qjh003-asset-relocation-20261030.json`|`218bfc2d53f623d98aa64286c1d132c9c74a8f6db0c75aa8e48cfaa9f82f0e70`|13721|

本次按实际文件重新算SHA，核相对本地HEAD `24b441923119581ab1c5e3274eca7d654021675d` 的工具/测试diff，以及旧/新配置逐字段比较。旧配置SHA仍为 `5e2ad79aaca28dbc9588540ecd8e0e4c4f222176335b30e6063f33a73e5af1d7`，未改写。新实现符合 `epd-relocation-CPU-20261030-G1.md` 的本地最小范围。

## 审查依据

1. 工具实际diff为11增7删：仅新CONFIG_SHA、固定CPU_BOOKING、window_end从旧direct scope改为精确owned CPU scope、fresh proof内实际票校验，以及成功准入后claim的真实reservation_claimed。原重定位/库复制/链接/启动文件检查与失败处理逻辑没有扩大。

2. 第72–77行的permission必须与新owned_cpu_booking/固定票字段一致，now须严格int且处于04–11窗口，旧16–17 direct许可拒绝。第80–92行仍要求实际只读API proof、observed严格int/不未来/不超过300秒、active指定资源；新增本人票ID唯一且id/node/resource/kind/user/start/end完整匹配，缺失/重复/错票均拒绝，end也须是固定票结束值。其后对相关CPU/整机票的start/end严格int检查也覆盖本人票，避免浮点/bool等时间类型借Python相等比较通过完整准入。

3. 他人CPU或整机冲突检查保留，GPU票不作为本次CPU许可。实际relocate先取真实now并通过window_end，再在第111行完成cpu_permission，之后才读资产/进程前置与建立stage。apply沿用240秒保守可用区间、verify90秒，其后再有END前120秒余量；实际工作限额仍120/60秒，外层清理30秒待精确执行命令绑定。没有因new own-ticket缩小冲突过滤或放宽最后收尾。

4. 第180行reservation_claimed=True位于这些真实准入和写前前置之后，随精确permission和proof记入排他claim。这里表示已验证本人预约，不表示工具创建了预约，也不表示apply成功。新fixture确在依赖缺失导致失败时检查保留claim及其True；不能从这个mock推出目标host实际已有新claim。

5. 新旧配置只有 `cpu_permission` 和 `stage` 两项差异。新stage为 `staging/asset-relocation-cpu-20261030`；61项原始allowlist（51 console+5 activation+5 unchanged）、3条Python links、nested IPC原SHA/大小、flat目标与3项RUNPATH均一致。原stage/flat已存在即拒绝、源pin/未知startup/所有权或链接异常拒绝、备份原字节、atomic rewrite、NEEDED不变及nested原库不变的检查仍在。新stage不能绕过flat/部分结果排他。

6. 本次没有引入Ray/Torch导入、dlopen/IPC执行、CUDA/NVML/模型或系统修改。CPU50/nice10、boot/UID、1GiB限制及自有EPD/Space项目活动进程拒绝保留。旧inspect入口的历史票范围未更新，不作为本次维护入口；旧runner因新CONFIG_SHA不符而拒绝，具体apply/verify必须使用后续另审operator与实际发布的新工具/config，不隐式复用旧runner。

## 已有测试证据与限制

已读取before/after/final原始日志、tests.json/files.json并核实际三源码SHA。before记录新owned-ticket用例的4个subtest在旧source上未抛ValueError；这是**新合同反例**，旧direct scope原本允许合法无票CPU工作，不能称为旧授权漏洞或旧预约失败。after为10 tests/0failure/0skip，final再次为同一10 tests/0failure/0skip，分别0.113s/0.119s；不合并成20个不同测试。final实际SHA `38e840bfcd407fd8085db903b25a8b53e4fe650974513ea5abaea8b7b053c204` 与tests.json一致。

源码覆盖票缺失/错误/重复/篡改结束、窗口起点前/终点/now类型/旧scope、他人CPU/整机冲突、stale proof/预算余量、真实claim序列的Windows mock，以及原文本变换/CRLF/未知startup/终态不可覆写回归。本审不重新执行测试；这些是Windows fixtures，模拟了Linux身份/信号/进程/资源接口，不证明目标Linux signal清理、readelf/patchelf、实际61资产状态、动态加载、Ray或GPU可用。

## BLOCKING

无（上述精确源码与本地证据范围）。

## NON-BLOCKING

1. 下一精确候选G5应绑定本三文件、真实G1/G2及测试原件，在独立EPD分支发布；Space main/HEAD24b与其server checkout不变。本G2不是发布许可，也不是新工具已部署/运行的证明。
2. 实际维护operator/transport需另审：绑定发布commit与tool/config字节、fresh本人票/现场/无活跃项目进程、唯一新output、apply120+30/verify60+30和END-120；记录辅助tool commit与EPD runtime repo commit各自事实。实际partial/UNKNOWN保留不回滚/不重发，不能靠换stage或手改资产恢复。
3. 仅在真实apply成功、下载原件逐SHA及独立实际审计通过后，再fresh并另审首次verify。旧写前CPU冲突失败保持失败，现有本地10PASS不授目标重试或runtime-ready。静态维护与Space模型/正式GPU工作不可并发，完成/受控收口后才交接；不放宽自有进程guard来配合并发。

## QUESTIONS

无阻塞性问题。当前没有新远端成功结果或环境加载结论。

本审仅读本地源码/配置/diff、SHA与已有测试日志，未测试、网络、SSH、GPU或修改实现，仅新增本报告。

GATE_RESULT: {"gate":"G2-EPD-relocation-CPU-20261030-source","decision":"APPROVE_WITH_NITS","blocking":0,"source_review_passed":true,"tool_sha256":"0e3031089b7e523309b4cc3fcaab2b91f4ba4382963778cf22ea78cba647acec","test_sha256":"fff8d0e122f7a772999305ee952964a257c4075b4fcd97852e61b704d848eacb","config_sha256":"218bfc2d53f623d98aa64286c1d132c9c74a8f6db0c75aa8e48cfaa9f82f0e70","distinct_local_Windows_fixture_tests":10,"publication_approved":false,"remote_execution_approved":false,"GPU_approved":false,"runtime_ready_granted":false}
