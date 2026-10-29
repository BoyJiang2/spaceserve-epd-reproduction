# EPD relocation inspect-only — independent G2/G5 source review

Reviewer /root/epd_pd_followup；reviewed_at_utc 2026-10-29T01:05:42Z（clock tool）。Actual tools/relocate_epd_assets_cpu.py SHA256 694679cbd66f67ea1b485ae1d833a03c82de523812f05d780a541d07e6fe4dd2. Scope: inspect-only source candidate, not apply or execution. Only local source/hash/time reading; no tests/compile/tool run/SSH/network/GPU or source changes.

G2 REQUEST_CHANGES / BLOCKING1. G5 candidate-source publication pending closure of the same one-line completeness issue.

B1 — bin inventory chooses shebang branch before activate branch. An activate* file beginning with#! is recorded by read(path,False), omitting its full text; the approved plan and task explicitly require activate full text to derive the later exact relocation allowlist. Unknown startup must not be assumed to lack a shebang. Minimal correction: prioritize path.name.startswith('activate') and read(path,True) before the elif shebang console branch. Keep all current owner/type/64KiB checks; no new framework/test suite is required by this review. This is an inventory completeness issue, not an observed GPU or remote failure.

Other narrow checks accepted:
- Only phase=inspect exists; no apply, file writes, subprocesses, .so loading, Torch/Ray/relocated-environment imports, ldd/dlopen or GPU access. System stdlib only; caller must use native/usr/bin/python3-I-S-B.
- Exact new CPU ticketbk-20261029T0057-e2efd603/09–10, cpu lane/owner/resource, no-future <=300s observation, UID2147/boot65f/affinity{50}/nice10, complete60+30 with120s end reserve before09:58 checked. GPU ticket does not confer scope here.
- Managed ancestors and regular-file leaves are real/owner-checked; startup files<=64KiB; pyvenv/.pth/sitecustomize/usercustomize captured statically, text never exec/import. Console first lines and whole-fileSHA, intended python-link metadata only. Unknown/nonUTF8/oversize/type/owner fails without modification or retry; no HOME/credential configuration reads.
- Work check60s and09:58; stdout only. The +30 cleanup/exact interpreter flags are launcher properties, so source G5 will cover code publication only and execution still requires the exact bounded launcher/fresh gate. No remote directory/backup/apply write permission is implied.

Only after the real inspect output can a precise path/beforeSHA allowlist be frozen; later flatIPC/RUNPATH/consoleactivate apply remains separate G2/G5 and approved actual CPU unit. Existing raw/nested/old source and Space final publication remain out of scope. Main executor's compile PASS is not independently rerun or treated as target execution by this review.

GATE_RESULT: {"gate":"G2","decision":"REQUEST_CHANGES","blocking":1,"scope":"inspect_only_activate_full_text"}
GATE_RESULT: {"gate":"G5","decision":"REQUEST_CHANGES","blocking":1,"scope":"candidate_source_publication_only"}

## B1闭合窄复审 — 2026-10-29T01:20:58Z（clock tool）

已直接读取最新bin分支，activate*全文处理优先于普通shebang console分支。实际源码SHA256 8ca5723e26e0083c703d46587a57416ad7e26a7d1386f34c34fd357aa1fcf28c，与主线程指定值相同。原唯一B1关闭；初审历史保留。

G2 APPROVE/BLOCKING0；G5仅此精确inspect-only源码候选发布范围APPROVE/BLOCKING0。未独立重跑compile或测试，不代表实际部署/执行/结果通过。当前用户强优先Space正式，EPD只本地准备，**不部署、不执行本工具**；qjh003本人新长窗未核且10–17冲突，不以旧CPU票、本G1/G2/G5或其他用户GPU票继续运行。后续真实获批资源/fresh预约、适用新时窗scope及Git-first部署/字节核验另行满足，原固定09–10边界不自动外推。未授apply/重定位写操作/native36/模型/GPU或新增预算。

本轮仅本地源行/SHA/时间读取并追加审查，无源码改动、测试、远程或网络。

GATE_RESULT: {"gate":"G2","decision":"APPROVE","blocking":0,"closed":["B1"],"source_sha256":"8ca5723e26e0083c703d46587a57416ad7e26a7d1386f34c34fd357aa1fcf28c"}
GATE_RESULT: {"gate":"G5","decision":"APPROVE","blocking":0,"scope":"exact_inspect_only_source_candidate_publication","deploy_or_execute_now":false}

## Inspect controller G5 — 2026-10-29T01:43:59Z（clock tool）

Reviewer /root/epd_pd_followup。实际读取outputs/migration-qjh003/epd-relocation-controller.py，SHA256 a070a952a017e68af50c8415f616476853936acbcc716f79bded9e4192bab112，与指定值一致。G5 APPROVE/BLOCKING0，仅当前精确inspect源码+plan/审查/controller候选发布范围。

代码核对：phase仅inspect；HEAD须等于ls-remote main，git show实际source固定SHA8ca5723e26e0083c703d46587a57416ad7e26a7d1386f34c34fd357aa1fcf28c；本地epd-relocation-remote-source-verified.json必须存在，且commit/sourceSHA/bytes精确匹配、observed_ms无未来且<=300s。该读取和断言都在booking调用、创建执行D和SSH之前，缺失/失败抛出且无捕获继续分支，故不会像先前独立PowerShell gh失败后继续那样由此controller自行绕过。此处只验证前置文件消费契约，实际API核验与原始bytes证据仍由primary在发布后本轮真实产生，不以此审查代替。

fresh booking snapshot一次、check_returncode成功后才能构造wire；资源字段白名单，票只id/node/resource_id/kind/user/start_ms/end_ms七项，固定新CPU票bk-20261029T0057-e2efd603。远端受审source再次核同SHA，native/usr/bin/python3-I-S-B、taskset50/nice10、60s TERM+30s KILL，SSH连接15s/本机父115s有界，严格hostkey/BatchMode；独占本地epd-relocation-inspect目录exist_ok=False，input/实际argv/源码commit与payloadSHA在SSH前留存，stdout/stderr/exit本地保全，无重试/备用执行路径。无apply实现、远端写入或GPU动作。实际工具仍核UID/boot/fresh新CPU票及09:58截止，不能借此G5外推新时窗。

用户最新“先做不需要GPU事情”的范围由主线程明确恢复当前09–10 CPU inspect；前条“暂不执行”的停等状态以本次明确续接为准，仅在发布/同源真实API字节核验和实际freshCPU准入完成后由primary一次执行。GPU长窗或10–17冲突不由本批准解决；不授GPU/apply/native36/模型/新预算。API核验文件须真实且在本轮准入仍新鲜，不重用旧结果或手填认证PASS。

本轮仅本地读controller/SHA/clock并追加原文；未运行controller、git网络、booking API、SSH、工具、测试或compile。发布后实际commit/remote字节核验与执行原件仍需保留并独立实际审查，不把候选G5当已发布或已执行。

GATE_RESULT: {"gate":"G5","decision":"APPROVE","blocking":0,"scope":"exact_inspect_tool_plan_reviews_controller_publication_only","controller_sha256":"a070a952a017e68af50c8415f616476853936acbcc716f79bded9e4192bab112","source_sha256":"8ca5723e26e0083c703d46587a57416ad7e26a7d1386f34c34fd357aa1fcf28c","apply_or_GPU_authorized":false}
