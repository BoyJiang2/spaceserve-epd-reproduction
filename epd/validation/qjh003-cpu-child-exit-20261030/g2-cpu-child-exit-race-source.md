# G2 — child exit handling during CPU descendant collection

APPROVE_WITH_NITS / BLOCKING 0. Source-only gate for exact two files below. No remote execution, cleanup or release approval.

Read-only diff againsta4b confirms collector-only narrow change. Known parent observe, equality check, children read and stable(parent) now share the existing absence handler; live parent PID still raises, ValueError/PermissionError remain unhandled and known entries remain historical. That event still expressly grants no release/quiescence.

Child observe, ppid/start relation, parent stable and child stable are enclosed only for FileNotFoundError/ProcessLookupError. Handler requires childPID absent, successful fresh stable(parent), then childPID absent again. The fresh parent stable call is inside the handler body and cannot be recaught by that same exception clause, so parent missing/identity uncertainty propagates. PID reappearing at either check raises. UID/root/RUNID/PIDreuse/ppid/start ValueErrors are unchanged. Successful disappearance records only an enumerated PID, existing known_identity orNone, parentbefore/after and release_or_quiescence_granted=False, then continues before registration. It neither grants unknown child ownership, deletes prior known entries nor authorizes a signal. Existing TID guard and cleanup implementation remain unchanged.

Eight new fixtures cover known child exit retaining history, unknown child exit without registration, missingfield withlivePID, exit between first/second identity reads, PIDreappearance, parent exit during children read, liveparent missingchildren, parentreuse during child disappearance. Existing strict identity/budget/parent-chain cases remain. Primary beforelog191tests/5ERROR preserves stale-child counterexamples; final191numeric plus4policy logs report195distinctPASS. Reviewer did not run tests. These fixtures support the narrow collector behavior, not actualfull4 or GPU success.

Actuala4b traceback established stale child snapshot /proc/1181270/status; earlier9a63 FNF remains unlocated. The fixed actor ACK progression is evidence of partial progress, not passed scenario. All failed runs and their cleanup evidence remain separate. New source must be published/deployed under fixedcommit and actualG3/new concrete execution approval before any fresh CPUfull4. No shortened budgets, smoke or relaxed CPU profile are approved.

Nit: the disappearance event lacks the caught exception filename, although it preserves exact enumeratedPID and parent observations; previous failed traceback is retained separately. This does not weaken identity/refusal semantics or justify a new framework. No source edits, tests, network, SSH, Ray or GPU by reviewer.

- epd/runtime/numeric_descendants.py: `94cec4b21d881c18bb0383740e1fd649a18944c676475708b838067c360892cf`

- epd/runtime/tests/test_numeric_descendants_cpu.py: `ae3a08672d4bbd244c1a788484c7768571f2bb788d8549b326d8b3608c79ec4a`
