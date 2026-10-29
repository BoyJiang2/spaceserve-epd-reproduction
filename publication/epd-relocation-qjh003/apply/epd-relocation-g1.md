# EPD minimal asset relocation — independent design G1

Reviewer /root/epd_pd_followup；reviewed_at_utc 2026-10-29T01:03:20Z（clock tool）。Plan: outputs/migration-qjh003/epd-relocation-plan.md；SHA256 d258129d6bd1a19908c87dbbbda90bc1b00634f10c21784eded2de77378adc33。仅本地阅读计划、时间/SHA核对并写本审查；未实现、测试、SSH、网络或远端CPU/GPU操作。

结论：APPROVE / BLOCKING0，仅限计划所述qjh003续约CPU最小迁移设计；不授权未审代码或未知文件修改，不是实际执行/结果或GPU批准。

## 范围成立

- 新CPU票bk-20261029T0057-e2efd603/2026-10-29 09–10，固定UID2147/boot65f/CPU50/nice10、系统Python-I-S-B。并列GPU票不是本步骤GPU授权；不查询/初始化GPU，不导入Torch、不dlopen/ldd、不模型/native36，不以1小时绕过Space201min正式门槛。
- 先一次只读startup真实清单（.pth/sitecustomize/console/activate及相关meta/readelf），60+30；不执行/导入这些startup文件。既有原件没有覆盖startup，明确不从旧shebang样本推断其行为。未知行为/路径依赖立即保全阻塞，不绕过。
- 真实清单后才冻结精确路径/原字节SHA的最小写allowlist；仅新稳定资产的flat副本RUNPATH与所需console/activate旧root引用。原nested库359096B/SHA12e414...ca20和旧源不动，不重装/改版本/模型/调度/cache/无关metadata。patchelf只改新副本，用readelf静态复核；完整原件备份及before/after差异独立保留，不覆盖原raw manifest/旧失败/ZIP/claim。
- 单一tools/relocate_epd_assets_cpu.py，不复制窗口工程；代码及实际allowlist先G2/G5、commit/push/远端原字节核、指定source后才一次apply120+30；排他claim、freshAPI/boot/root/无本项目活动、owner/link守卫在执行时重新核，不复用旧票/marker。失败保留partial、零自动重试。
- 最后一次独立静态重读60+30，只承认路径/RUNPATH/shebang/startup引用和原件SHA事实；不是Python运行可用、IPC/通信/模型或GPU通过。09:58硬截止不延长，不混Space已发布批次或当前final-publication staging。

## 实现/G2必须具体落实（不是额外资源批准）

1. 本G1批准先inventory、后基于事实冻结allowlist的设计，不批准现在预填未知startup改写项。实际apply必须消费受审清单和每叶子before SHA；缺文件/错SHA/符号链接或归属未知应拒绝，不能递归替换所有旧root或跟随链接到其他项目。对unknown .pth/sitecustomize先停，不能靠改写其路径把未知可执行startup合理化。
2. 备份与差异清单的写入位置也需纳入新项目受控输出白名单；原nested/旧源/原manifest/Space目录应在代码中明确写保护。副本和env文本写入/失败partial的真实终态须保全，不能把部分apply报告completed。原始bytes与重定位后的派生bytes分版本记录。
3. 每次本窗fresh CPU票/UID/boot及全部90s/150s单元必须能在09:58前结束；开始apply时还应预留计划内独立verify90s的时间，不以“apply已开始”追加窗口。三个远端单位上限合计330s（90+150+90），代码编写/审查/发布耗时不是允许越过10点或补跑的依据；时间不够则未执行/部分静态事实收口。
4. 明确native系统解释器/无site初始化与patchelf/readelf固定argv，保护argv和日志不含凭据；票回执只批准非认证字段。leaf owner/real ancestry检查沿用上次修复，bin/python只检查链接文本/resolve，不执行目标。具体launcher/G2需确认总deadline/cleanup/身份边界，计划本身不等于这些实现已验证。

上述均是计划已有边界的代码化检查点。盘点后如果出现需执行未知startup、安装/更改依赖版本、触碰旧源、扩大allowlist语义/CPU时间或GPU动作，必须先提出新设计/适用G1，不能作为本批准的默认例外。没有此类事实前，无需重复请求用户迁移许可。

NON-BLOCKING：无。历史事前API核验缺失仍按原页保留，本次发布必须真正前验失败即停，不以事后核验代替；此审查不重判Space已发布Release，也不授权混入最终publication。

GATE_RESULT: {"gate":"G1","decision":"APPROVE","blocking":0,"scope":"qjh003_09_to10_CPU_only_inventory_then_exact_allowlist_relocation","GPU_authorized":false,"execution_before_G2_G5_publication_allowed":false}

## 新直接CPU许可补充G1 — 2026-10-29T02:06:38Z（clock）

已读计划新增“用户最新CPU授权覆盖”。当前plan SHA256 18487f0228f79434c6f1e3c771517d152ab92dc83f541abfc3af2f2dd00b5971。主线程转述用户直接原文：“虽然后面的cpu没有预约 但是你可以随便用”。G1 APPROVE/BLOCKING0，仅将同一最小apply/verify CPU设计的09–10本人票限制改为本日12:00自限、11:58收口的人类直接许可；不批准其他主机/GPU/模型/native36或API scope升级。

实际读cpu-extension-book.stderr.log为API400 missing scope:bookings:create:self。补订未成功，不能签BOOKING_VERIFIED或伪造10–12票，不能改凭据/换scope绕过API。未预约CPU使用由明确人类许可承担授权，和API预约权限是不同事项；原inspect仍按真实09–10票记录，不追溯套新许可，不重跑。

后续每个单元须fresh只读API resourceactive、全部相关他人CPU/整机占用及精确半开时间区间重叠检查，保存非认证原件与观察时间；未知lane/归属/不可判定占用立即拒绝。仅“没有本人票”或“有本人17–20GPU票”不构成无冲突证明。发现他人CPU或整机窗口与该单元工作+清理重叠，不启动/继续借用；实际UID/boot/CPU50nice10/项目root和无本项目活动也须重新核实。不可因API400改为不检查API，只是不再要求虚构本人票。

人类原文和当前计划范围/SHA须绑定进新准入证据，状态明确“direct_user_authorized_unbooked_CPU”，不能复用旧ticket marker。原代码尚只支持旧09–10 exact ticket；新apply/verify及相应准入必须先按该新模式G2/G5/Git-first/真实API字节前验，现有inspect实现不会自动得到延时执行许可。apply120+30、verify60+30，开始apply应预留verify90s；全部在11:58前结束，时间不足不追加。具体allowlist/原件SHA/flat副本/备份/partial和旧源保护边界不变，未知startup仍先停。

本G1只审新直接CPU许可的设计边界，不是实际fresh无冲突/执行结果证明。没有新的预约被此审查创建；用户GPU17–20仍另按真实GPU票和独立GPU Gate处理，当前不GPU、不混Space最终publication。

GATE_RESULT: {"gate":"G1","decision":"APPROVE","blocking":0,"scope":"same_EPD_minimal_apply_verify_direct_user_unbooked_CPU_qjh003_until12","BOOKING_VERIFIED":false,"API_scope_escalation":false,"GPU_authorized":false,"execution_before_new_G2_G5":false}
