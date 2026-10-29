# EPD minimal apply/verify — independent narrow G2

Reviewer /root/epd_pd_followup；reviewed_at_utc 2026-10-29T02:16:56Z（clock tool）。Source tools/relocate_epd_assets_cpu.py SHA256 22563200f74ec2ab64d83f4ecc965e6793c9415f94175e431d2a31c4f284fc3a；config epd/migration/qjh003-asset-relocation.json SHA256 afab6795c25600d7fdfa3de215e30ab97ae367d81deb3897cc2a7f29f3e09a66。Read only actual source/test/config and original inspect pins; no tests/compile/SSH/network/GPU, no code changes. Main executor's five local PASS are reported evidence, not rerun or expanded by this review.

结论：REQUEST_CHANGES / BLOCKING3，仅以下窄边界；修后复核，不批准目标执行。

## B1 — unknown startup guard incomplete

relocate() before apply/verify checks only `pth.glob('*.pth') == {'distutils-precedence.pth'}`. Inspect originally had no sitecustomize.py/usercustomize.py at this site path, but a newly present file is neither in61 pinned rows nor rejected now. This violates the approved unknown-startup-first-stop rule; fixed known file SHA alone cannot establish no added startup.

Minimal fix: real/check the exact sitecustomize.py/usercustomize.py leaves and reject if present (including linked/special nodes), in both apply and verify, matching actual inspect absence. Keep the exact.pth set and its pinned file hash. Do not execute startup or broaden into home/system scans. Add one small source-level/unit contract regression for added customization rejection, not a new testing framework.

## B2 — first mutation outside unified terminal finally

In apply, `stage.mkdir`, `save(stage/'claim.json',...)` and `(stage/'before').mkdir` occur before state creation, TERM/INT/ALRM handlers and try/finally. An I/O failure/TERM after first mkdir or claim leaves a real partial stage with no apply-terminal state, contrary to the advertised partial-terminal/finally guarantee. Existing stage then blocks retry, but absence of a terminal is not an explicit recorded outcome.

Minimal fix: prepare state and bounded handler/try/finally before the first allowed write, and cover stage/claim/backup-directory creation in that path. Record failures honestly, do not mark success or delete partial; if terminal file cannot be written, emit the attempted terminal to stdout/stderr/local launcher capture rather than masking the original failure. One shared bounded timer/deadline, no new manager. SIGKILL/power loss remain uncatchable and must not be promised. Add a targeted first-write/claim-write failure regression source; existing pure rewrite tests do not cover this lifecycle.

## B3 — verify stage leaf proof is not checked before read

Verify reads `(stage/'apply-terminal.json').read_bytes()` directly after checking the stage directory, without `real(exact_leaf)`/regular owner guard. It also rejects repeat verify only with `.exists()`, which misses dangling symlinks at verify-terminal.json. Thus stage owner/ancestry does not establish the leaf receipt is a real owned original, reintroducing the same leaf-boundary issue already closed in inspect.

Minimal fix: before reading apply-terminal, validate its exact owned real regular leaf, and use existence-or-symlink check for the exclusive verify-terminal target (and reject other unexpected node types). Bind prior receipt to expected phase/boot/config as well as successful exit; retain independent final61/backups/flat/NEEDED checks. No following receipt links outside the stage. Cover a symlinked prior receipt/dangling repeat marker with a small regression or explicit check assertions.

## Confirmed implementation facts

- All61 config path/bytes/SHA pairs match original inspect db8ffa0366f33bc67c09feb470e6337bae26a6cb45b5b31a909605d404ed6e56; kinds51console/5activation/5unchanged are correct. Source literal and config human quote are actual matching Unicode (console rendering was not used to infer encoding failure). Config pins nested359096B/SHA12e414...ca20, new flat and new3env RUNPATH.
- rewrite(console) changes only exact interpreter first-line prefix and preserves following LF/CRLF/body bytes; rewrite(activation) requires exactly one oldenv occurrence; unknown kind refuses. Non-mutated five remain SHA-checked. Original backups and exact new source/config binding support truthful before/after; original nested and old source are not edit targets.
- apply refuses existing stage/flat/retry, creates new flat from nested via exclusive temp+hardlink then patchelf only copy, checks exact newRPATH, records before/after and later all61/56transforms/originalnested/NEEDED equality. No Torch/ldd/dlopen/GPU/model/native36. Actual runtime loading is not claimed.
- cpu_permission uses original direct-user authorization until12, not a fabricated booking, checks fresh actual resource/no conflicting other CPU or whole-node lane (kindNone) and full apply+verify/cleanup reserve before11:58. GPU rows are not borrowed as CPU grants. Exact host/UID/boot/CPU50nice10 and1GiB AS,120s apply/60s verify, per-tool10s, signal finally are in source; B2 is the remaining placement gap.
- Five test methods cover LF/CRLF, wrong shebang/kind, activation uniqueness, CPU stale/conflict/whole-node/reserve; no claim they cover added startup, first-write terminal failures or receipt leaf guards. No new remote tests are requested by the reviewer before fixes/appropriate publication gates.

After fixes source/config/controller must have narrow G2/G5, Git-first push and real pre-API bytes proof before one new approved CPU unit. Previously executed inspect is not rerun; no Space final-publication/data changes. Human CPU extension does not waive file guards, unknown startup stops, actual result review or GPU gates.

GATE_RESULT: {"gate":"G2","decision":"REQUEST_CHANGES","blocking":3,"scope":"EPD_CPU_minimal_apply_verify","execute_now":false}

## 窄复审 2026-10-29T02:23:40Z（clock）

实际source SHA491aaad8e912fa15d643a6525ad674a2d2f258694394e5e9365dacfbf880a2a7；controller SHAa401670b9c47841cfd6480f077ad3e4f92050cd7582f71c6c49d0a2bed2acd9d。B1关闭：known_startup在两phase共用，新增site/usercustomize（含dangling）及额外.pth拒绝。B3关闭：prior精确叶子real+regular，marker real且exists/issymlink拒重复。B2首写部分已修：state/handler/timer在try前、mkdir+owned_stage短屏蔽TERM/INT/ALRM、claim/before均在try，existing stage失败owned_stage=false不会写陌生stage。

B2仍有单一终态余项：finally在终态保存前恢复旧TERM/INT，然后terminal.open/json.dump/fsync未容错，任何该处I/O失败将跳过print并覆盖原异常，不能按原B2要求输出attempted terminal fallback；恢复信号也使可捕获TERM在终态窗口直接终止。最小修复只需终态保全期间忽略/暂存TERM/INT、文件写try/except保存terminal_write_error且无论写盘成功与否print完整state，最后finally恢复原handler；保留外层unit120/60+30截止与SIGKILL不可捕获边界。不要求新框架或重复原5测试。当前G2 REQUEST_CHANGES/BLOCKING1，仅此B2余项；B1/B3不再重复提出。

controller其余G5契约已读：仅apply/verify、source491a/configafab双pin、samecommit lsremote、每phase pre-API双文件证明/sourcebytes/5min前置、所有相关非GPU CPU/whole票七字段、直接人类许可而非假票、native50nice10/I-S-B/120或60+kill30、本机+55有界、独占各phase输出、无自动重试。源修后必须同步controller source pin并重核精确SHA，才可发布G5；当前不批准执行。主线程报告sandbox Temp首版ERROR保留和workspace修后6PASS，不在本轮重复执行或冒称目标通过。

本轮只读源/config/controller/SHA，未测试/compile/SSH/网络/GPU或改代码。

GATE_RESULT: {"gate":"G2","decision":"REQUEST_CHANGES","blocking":1,"closed":["B1","B3"],"remaining":"B2 terminal-write fallback and signal restore placement"}

## Final narrow G2/G5 — B2 closed, 2026-10-29T02:25:50Z（clock）

已直接核terminal_report与调用finally：先保留original_failure，关alarm，终态保全期间TERM/INT/ALRM设置IGNORE；terminal_report捕获终态open/write/fsync失败、state.exit_code=1并附terminal_write_error，仍print完整失败state；后finally恢复原handlers。有原异常不以终态写失败覆写，无原异常则终态持久化失败导致RuntimeError非零退出。原B2剩余问题关闭；B1/B3不重复泛审，仍按已关闭项保留。

最终G2 APPROVE/BLOCKING0。精确源码d403e7df8ab3b87406a5e841a3f41ff487f5f76a0ec7843c88786d1327604363。实际读最后新增测试：预存verify marker引发FileExists，原marker保持，stdout有exit1+terminal_write_error；本地final.json的source/test SHA与当前字节一致，final.stderr原件记录Ran7tests/OK、exit0。只读核其记录，审查者未执行这些测试；首sandbox ERROR和6PASS历史不覆写，7PASS不表示目标apply已执行。

G5 APPROVE/BLOCKING0，限以下精确候选源/config/controller/plan/tests及既有审查材料发布，并允许primary在全部实际执行前置满足后一次apply、一次verify（任失败停止、不重试、不重跑inspect）：

|成员|SHA256|
|---|---|
|tools/relocate_epd_assets_cpu.py|d403e7df8ab3b87406a5e841a3f41ff487f5f76a0ec7843c88786d1327604363|
|epd/migration/qjh003-asset-relocation.json|afab6795c25600d7fdfa3de215e30ab97ae367d81deb3897cc2a7f29f3e09a66|
|epd-relocation-controller.py|b7455b7d3ea9b98922d7ab51dfb69baf3a44283d4cb2230d2c3f72869690c334|
|epd-relocation-plan.md|18487f0228f79434c6f1e3c771517d152ab92dc83f541abfc3af2f2dd00b5971|
|tools/test_relocate_epd_assets_cpu.py|363c88a106492a663646557d4d41e0cc5079bd7ca882463755040200c2b6bac2|

Controller source pin已同步d403；其先验samecommit source/config API proof、fresh/nonfuture<=5min、lsremote、有界Git/booking/SSH及CPU/whole-node七字段和单位argv的既有核查不变。执行前必须正常commit/push并真实API核这两blob原字节，生成本phase真实证明；任何前验失败不继续。实际freshAPI无他人CPU/整机冲突、人类直接未预约CPU原文/状态、host/UID/boot/CPU50nice10/AS1GiB/12:00边界与11:58收口保持。apply120+30且预留verify60+30，单一受控stage/原件备份/旧nested不改；不提升API权限，不凭GPU票代替CPU授权。不混Space最后publication或旧raw/Release，不授Torch/dlopen/模型/native36/GPU或新增预算。

本结论不证明发布、实际准入、目标写入、静态verify或运行迁移已成功。完成后须原件/差异/目标终态独立实际审查；未知/partial不得写completed。审查者本轮未运行compile/测试/controller、未SSH/API/网络、未改源码。

GATE_RESULT: {"gate":"G2","decision":"APPROVE","blocking":0,"closed":["B1","B2","B3"],"source_sha256":"d403e7df8ab3b87406a5e841a3f41ff487f5f76a0ec7843c88786d1327604363"}
GATE_RESULT: {"gate":"G5","decision":"APPROVE","blocking":0,"scope":"exact_CPU_apply_verify_candidate_publication_and_conditional_once_execution","API_before_execution_required":true,"GPU_authorized":false}
