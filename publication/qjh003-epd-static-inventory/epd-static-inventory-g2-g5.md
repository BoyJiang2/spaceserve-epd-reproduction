# EPD static inventory — independent G2 / G5 source review

Reviewer: /root/epd_pd_followup. reviewed_at_utc: 2026-10-29T00:08:39Z (clock tool). Source: work/repository-upload/checkout/tools/inspect_epd_assets_cpu.py; SHA256 0416aa1fe9ea9ba722078239718ef09d91b1d3cbcbe12ba30f72aea88db0b93a. Basis: revised static-inventory plan368ce96cc548e28770c392016a6f82a3b38f6c784ec3b01e689c15ef64fc15bc/G1 B1closed. Read-only local source/hash/status inspection only, no tool run, compile, tests, SSH, GPU or credentials. Main thread's compile PASS is not independently rerun here.

G2: REQUEST_CHANGES / BLOCKING1. G5 candidate publication: not approved until this source blocker is closed and exact revised source/launcher is pinned; no runtime approval.

## BLOCKING

B1 — main(), managed-file ancestry/ownership checks are incomplete at actual reads. `real(envroot)` does not validate its child `pyvenv.cfg`, yet `cfg.read_text()` follows a leaf symlink and reads its whole target. `mps-owner.json` is read without `real(owner_path)` at all. Dependency listing likewise calls `p.is_file()/p.stat()` on unchecked leaf entries and follows symlinks. This contradicts the approved real/owned managed-path and no-home/secret-read boundary: a linked pyvenv.cfg can cause an outside-project/home configuration read even though output later filters three keys; linked MPS evidence can also bypass the intended owned original-file check.

Minimal fix: before reading cfg/MPS JSON, call the existing real(path) on the exact leaf, require owned regular files (not symlink/special), and retain directory ancestry checks; for dependency entries only stat explicitly validated non-symlink regular owned leaves, or record/refuse unexpected entries rather than follow them. bin/python is the one intentional link-inspection exception: readlink and resolve metadata only, do not execute/read its target. No new general sandbox/mock framework is needed. Also move `real(ROOT)` until after the Space capture and MPS proof checks, so the approved “Space released before EPD inventory” order is literal. Only Space proof paths need be read before that boundary. Source change should be narrow and independently repinned before publication/execution.

## Confirmed nonblocking scope

- Exact qjh003/UID2147/boot65f/CPU affinity{50}/nice10 and raw fresh CPU booking identity/window checked; current booking test requires90s plus120s end reserve, equivalent finish before08:58. This is a conditional fixed-window check, not a ticket renewal/extra budget.
- Checks actual Space model-attempt1-terminal.json SHA, phase=model, released=true, correct boot, owned_processes=[], manifest0590bc...8f6; this hash matches local current-status.json:330. MPS state=stopped and exact private pipe are mandatory before any ELF/EPD environment inventory. No formal201min bypass.
- Only /usr/bin/git rev-parse HEAD with fsmonitor/hooks/global/system configuration disabled, /usr/bin/readelf -W -d/-S (each<=10sec, common60sec deadline), selected pyvenv fields, console first-line shebang, interpreter link metadata, two fixed IPC paths/SHA and dependency names/sizes. No Torch/ldd/dlopen/GPU query/kernel, patchelf execution, installs or source/env/manifest writes. patchelf is only which().
- Script prints facts, including nonzero readelf statuses, not loadable/GPU-ready claims; no credential fields requested by code. Data supplied on stdin must be only the already approved scrubbed booking fields and capture SHA. Do not stream tokens/cookies/Authorization or unrestricted booking-client state into it.

## Publication / execution conditions retained

After B1 closure, G5 may approve only the exact source artifact/commit publication; successful ordinary push and remote byte verification still need actual evidence. Exact command must use native /usr/bin/python3 -I -S -B (not the relocated env interpreter), CPU50/nice10, source SHA verification, outer total<=90sec/cleanup30 and stdout/stderr saved locally. These interpreter flags/outer cleanup are launcher properties, not enforced by this Python file, so review the concrete launcher with the revised source. No execution before Space full313 actual terminal and confirmed CUDA/private-MPS release, fresh CPU lane/host/boot/deadline checks and publication verification. Current tool not executed by reviewer; no permission for relocation/native36/selected360 or new budget.

GATE_RESULT: {"gate":"G2","decision":"REQUEST_CHANGES","blocking":1}
GATE_RESULT: {"gate":"G5","decision":"REQUEST_CHANGES","blocking":1,"scope":"candidate_source_publication_only"}

## 窄复审 2026-10-29T00:18:22Z（clock tool）

实际源码SHA256 f4ab56a3f3473042202dfe11c562e65c61ed21f5c39a37a7dc30557a179dd9ec。已核cfg及MPS原件在read前real+regular，依赖symlink仅readlink不跟随、普通依赖先real再stat，real(ROOT)已移动至Space capture/MPS gate之后；这些原B1具体项关闭。

同一受控叶子归属边界仍有一处遗漏：console shebang循环的普通文件仅检查not is_symlink和is_file，在open前尚未real(path)，因此bin目录归属不能证明该普通叶子owner2147。按已批准所有受管路径owner要求，请仅在with path.open前加real(path)；bin/python有意只读链接元数据的例外不变。无需新增mock框架。B1尚有该单行余项，G2/G5当前仍REQUEST_CHANGES/BLOCKING1，修后可立即窄关闭。主线程报告Space313已exit0/released，审查者本轮未读目标raw/未远端核验，故不把此报告当本轮执行证据。未执行工具/编译/SSH/GPU，未改源码。

GATE_RESULT: {"gate":"G2/G5","decision":"REQUEST_CHANGES","blocking":1,"remaining":"B1 console regular leaf owner check"}

## 最终窄复审：B1关闭

Reviewer /root/epd_pd_followup；reviewed_at_utc 2026-10-29T00:19:26Z（clock tool）。精确工具SHA256 665e1ca755f624b8b132e6a48292c5da082f3f4731bfd047c36f2b48405b0324。已直接核当前shebang普通文件在with path.open之前调用real(path)，补齐自身owner/真实祖先验证；原B1各项全部关闭。

G2 APPROVE / BLOCKING0。G5仅此精确候选源码发布范围APPROVE / BLOCKING0；不证明push/远端字节或运行已经完成。仍须实际发布/核SHA、具体native /usr/bin/python3 -I -S -B/CPU50/nice10/总90sec有界launcher、fresh票及Space完整313真实终态和CUDA/privateMPS释放准入。任何目标静态盘点或重定位结果须独立实际证据；不授GPU/native36/selected360/新增预算。主线程compile PASS未由此审查重复执行；本轮仅本地源行/SHA/时间核对并追加原文，没有跑工具/测试/SSH或改源码。

GATE_RESULT: {"gate":"G2","decision":"APPROVE","blocking":0,"closed":["B1"]}
GATE_RESULT: {"gate":"G5","decision":"APPROVE","blocking":0,"scope":"exact_candidate_source_publication_only","source_sha256":"665e1ca755f624b8b132e6a48292c5da082f3f4731bfd047c36f2b48405b0324"}

## Launcher publication G5 — 2026-10-29T00:21:39Z

只读实际outputs/migration-qjh003/epd-static-inventory-launcher.py，当前SHA256 04e90bc8751e96238f7eed19b4ab42748b83fef4f1a52401e532953aa6f54a87。原生目标命令固定taskset CPU50、nice10、timeout60s/TERM再30s KILL、/usr/bin/python3 -I -S -B，SSH本机父115s有界；Git原blob与已push main HEAD比较、665e源码SHA、实际local capture原件SHA入wire、一次fresh票、独占本地输出目录及无自动重试均明确。没有运行launcher、Git网络、booking API或SSH。

G5 launcher剩一处最小白名单项：resources已字段筛选，但bookings仍把选中的完整b对象写入wire/input.json。为使本launcher自身严格证明仅传“id/node/resource_id/kind/user/start_ms/end_ms”非秘密票字段，请把bookings改为这一显式字段字典；不是指称现有snapshot已含token。其余认证材料不读不传的计划不变。该单行关闭前launcher发布范围G5 REQUEST_CHANGES/BLOCKING1；tool源码G2 APPROVE0与其发布范围既有结论不撤销。执行仍须实际Space释放/fresh票、发布及远端核字节。

GATE_RESULT: {"gate":"G5","decision":"REQUEST_CHANGES","blocking":1,"scope":"launcher_booking_field_allowlist"}

## 最终Launcher G5闭合 — 2026-10-29T00:22:17Z（clock）

已直接核launcher的bookings构造，仅传id/node/resource_id/kind/user/start_ms/end_ms七个批准字段。当前launcher SHA256 a749afbe237cced1cbbb4c7800931aa82d38f1fccd6a9a6c6a037e19bfcb2642；原唯一launcher白名单余项关闭，G5 APPROVE/BLOCKING0。tool精确SHA仍665e1ca755f624b8b132e6a48292c5da082f3f4731bfd047c36f2b48405b0324。

发布范围仅：inspect_epd_assets_cpu.py工具、epd-static-inventory-plan.md、epd-static-inventory-g1.md、本文G2/G5原文及上述launcher。明确不包括Space待独立审查data，不修改或重标Space数据/旧claim。此结论只批准这些精确候选代码/计划/审查材料的正常发布，不证明push或实际盘点结果；实际发布commit/字节仍需核验。仍须遵守原Space终态+CUDA/MPS释放、freshCPU/boot/CPU50nice10、60+30及08:58等执行条件，才可按该受审launcher一次执行。未运行launcher/API/SSH/工具或重复compile。

GATE_RESULT: {"gate":"G5","decision":"APPROVE","blocking":0,"scope":"exact_tool_plan_reviews_launcher_publication_only_excludes_pending_Space_data","launcher_sha256":"a749afbe237cced1cbbb4c7800931aa82d38f1fccd6a9a6c6a037e19bfcb2642"}
