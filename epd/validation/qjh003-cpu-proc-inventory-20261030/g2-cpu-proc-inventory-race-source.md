# G2 — narrow CPU /proc inventory handling and diagnostic evidence source

APPROVE_WITH_NITS / BLOCKING 0. Source-only gate for the exact four files below; no remote execution approval.

Read-only normalized diff against9a63 confirms production edits are limited to HeadProc.children and diagnostic traceback logging. In children(), parent start ticks are read before enumeration. Only FileNotFoundError from a listed TID children read reaches the new branch; task must be absent twice around a fresh equal parent-start observation. Reappeared/live TID raises the original exception, changed/missing parent raises, and PermissionError remains uncaught. Successful vanished-TID observations are explicitly raw=None/children=[] with tid_absent_before_and_after=True and release_or_quiescence_granted=False, not an empty normal read or cleanup grant. Ordinary child parsing and4096TID bound remain. The collector's original observe()/same_identity()/stable(parent) after children, child original-parent chain verification, FNF-with-livePID refusal, PIDreuse checks and cleanup permission logic are unchanged. Thus this branch cannot grant ownership or release for an unknown process.

Diagnostic change adds traceback.format_exc() and original exception.filename to the first CPU_diagnostic_failed event. Later cleanup failure may remain the terminal error while original failure evidence remains in the journal. It does not claim the old actual FileNotFoundError site was proven. The actual9a63 cause is still unlocated; TID exit remains a plausible hypothesis. Local counterexamples establish the new guard behavior, not the old runtime cause or a successful actual Ray rerun.

Tests: six new fixtures cover vanished/live/reused-parent/reappeared/permission/ordinary TID cases; existing parser fixture supplies the now-required parent stat. One new lifecycle fixture verifies traceback/filename survive subsequent pending-scenario cleanup failure. Primary log cpu-proc-race-final-v3.log records183tests OK; preserved policy log records4tests OK, total187distinct. Prior183/3ERROR and intermediate logs remain evidence rather than being relabeled passed. Reviewer did not execute tests.

Nit: the tests do not add a dedicated parent-deleted fixture, but the uncaught fresh parent stat read and existing collector stable checks fail closed; no new broad FileNotFoundError catch was introduced. No further wrapper framework is required.

Before any remote rerun: retain failed raw/late-WAL cleanup evidence, publish fixed source, deploy exact reviewed commit, verify actual source Gate and obtain a new concrete execution binding/fresh CPU ticket. No GPU, shortened scenario or relaxed CPU configuration is authorized. No network, SSH, tests, source modification or Ray/GPU work by reviewer.

- epd/runtime/numeric_descendants.py: `f5a27a61a8374e70e87bb8264f8a9da4bb4ec856883e373b7354c73c1e0620ed`

- epd/runtime/numeric_cpu_lifecycle.py: `4c37f83fcbad5c6610a2f83b39ccb8b2263ecc118b19b6abb983014e65c487e7`

- epd/runtime/tests/test_numeric_descendants_cpu.py: `268e650e086159d7fd7aa641e9177a559c3f156f4d092bfeabf8aec8c4013791`

- epd/runtime/tests/test_numeric_cpu_lifecycle_cpu.py: `400af7543ccf8a67ea32816b21b1db2b0145f33959dd07fa642bbf9423d42852`
