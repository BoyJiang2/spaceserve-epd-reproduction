# G1 — observed child exit during descendant collection

APPROVE_WITH_NITS / BLOCKING 0 for narrow repair planning only. No sourceG2, cleanup execution or new run is approved.

## Actual a4b evidence

Runtime a4b2070624b09bbbc3ad3fd3d5fcb451f5e182aa full4 exited1 with0scenarios completed. Raw archive366533B/SHAbb51f1585af14d91f9c98c6342ea558c7e9ae649be6fd4ea3737402bc3965844 was independently rehashed. The new traceback locates this run's exception precisely: numeric_descendants.collect line139 child=self.observe(child_pid), snapshot line10 reads /proc/1181270/status and raises ENOENT. This is not the TID/children read site. PID1181270/start26969004 was previously recorded as ray::CPUActor. Parent CPU_normal_live_actor_bound269691.333410263 and driver parent_observed_live_actor269691.366958607 both occurred before the failure269691.423428583. Thus the actor-reference/ACK path actually progressed in this run; do not relabel the entire lifecycle successful. The collector does not currently handle this stale enumerated child-PID disappearance.

Earlier9a63 had no traceback; its original FNF location remains unknown and cannot be inferred from a4b. Existing TID guard remains defensible as a separate locally tested guard, not a proven fix for9a63 or cause of this run.

## Narrow implementation plan

1. Extend the existing known-parent observe exception boundary to the same iteration's children() and stable(parent) reads. Only actual parent PID absence may record existing head_known_pid_absent and continue. If parent PID still exists, propagate the original failure. Preserve known entries, boot/start/UID/root/RUNID checks and no release/quiescence grant. A missing TID with live parent is handled only by the existing dedicated TID guard; do not blanket-ignore it here.
2. For a listed child observe→parent stable→child stable sequence, catch only FileNotFoundError/ProcessLookupError. Continue only after explicit child PID absence before and after a successful fresh stable(parent) check. Emit a distinct event containing the enumerated PID, original parent evidence, missing-path/error, and absence observations; ownership/release/quiescence must all remain false. Do not invent a new child identity from a numeric PID, remove known entries, or treat an empty unknown record as registered.
3. If child PID exists at either absence check—including PIDreuse—or parent identity/start changes or cannot be verified, raise. All ValueError/PermissionError/unknown-identity conditions remain strict. The fresh parent stable check must execute outside any broad handler that could hide its own failure. No retry loops, grace waits, scheduling changes or altered lifecycle scenario budget are needed.

Fixture requirements: listed child absent before first snapshot; child vanishes during second stable snapshot; successful doubleabsence with stable parent emits explicit no-ownership/no-release evidence and retains known map; missing status/cwd while child PID remains live raises; PIDreappears on second existence check raises; parent disappears/reuses/has permission failure during child-absence verification raises; known-parent disappears in children/stable reads records absence only if actualPIDabsent, otherwise raises. Existing original-parent relation, PIDreuse, UID/root/RUNID, TID guards, unknown process cleanup and full4 order tests must remain. Fixtures prove safe disappearance handling, not actual lifecycle completion.

Actual cleanup for this failed run remains separate: complete late WAL/constructor/GCS reconciliation and original PID identity checks before any head cleanup. No release may be inferred from ENOENT alone; only new independent execution/deployment/actualG3 chain can authorize a later rerun.

Reviewer used file reads only and wrote review artifacts; no tests, SSH, network, source modification, signals, Ray or GPU work.
