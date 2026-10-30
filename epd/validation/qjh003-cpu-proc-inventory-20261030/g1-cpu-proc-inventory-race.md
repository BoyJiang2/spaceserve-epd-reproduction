# G1 — CPU /proc inventory race diagnosis and narrow next step

APPROVE_WITH_NITS / BLOCKING 0 for a diagnostic and narrowly scoped source plan only. No sourceG2, cleanup execution or new CPU run is authorized here.

## Actual evidence and uncertainty

Actual9a63 full4 terminal exit1, smoke=false, affinity[50], nice10; zero scenarios completed. Parent first fails at268562.700345702 with FileNotFoundError(2,'No such file or directory'), before driver connected268562.822181883, before actor_submitted268563.193180255 and ready268564.205044915. The parent journal contains no CPU_actor_submission_observed. Therefore this failure is not evidence that the new retained-handle code failed after ready. The later driver events and constructor receipt exist and are genuine late creation WAL, despite parent failure. Original terminal/error must remain failed.

HeadProc.children currently lists /proc/PID/task then reads each TID/children without a disappearing-TID exception branch. A thread disappearing between those operations can produce precisely FileNotFoundError; this is a plausible hypothesis only. The actual log lacks traceback and exception.filename, so other paths—including child observation during collector traversal, cwd/exe/stat reads, or unrelated process disappearance—cannot be excluded. Do not report this as a proven TID race or fixed root cause.

## Authorized narrow plan for implementation review

1. Add full traceback and exception filename/type to newly generated failure evidence without overwriting original journals. This establishes the actual site on a future failure; recording must not turn failure into success.
2. In children(), tolerate only the specific enumerated TID disappearing while its children file is read. Require actual task-directory stat to raise FileNotFoundError/ProcessLookupError, and parent PID/start identity stable before/after; keep raw disappeared-TID observation explicit. Do not treat an empty/missing children file while TID remains live as harmless. Parent missing/reused, PermissionError, malformed contents and identity uncertainty must still fail. Existing collector stable parent proof must remain mandatory, including on this branch.
3. Do not catch FileNotFoundError broadly around collect(), observe(), child ownership or final cleanup. Do not relax FNF-with-livePID or strict PID reuse. This plan does not authorize ignoring vanished unregistered child processes or claiming full inventory quiescence.

Meaningful fixtures: listed TID disappears and parent remains identical (one explicit vanished-TID record, other TIDs preserved); children file missing with TID still present (raises); parent disappears or start changes during enumeration (raises); PermissionError (raises); malformed children (raises); bound>4096 (raises); other exceptions preserve traceback/filename. Exercise collector integration so the new branch cannot bypass stable parent checks. Existing livePID/FNF, reuse, original parent-chain, unknown-process refusal and cleanup tests must continue passing. Local fixtures cannot establish the actual runtime cause or successful Ray lifecycle.

## Late-WAL cleanup plan

Stop only the originally registered driver using its exact stable PID identity, then freeze/read the complete five-event WAL and match the submitted/driver-ready/constructor ActorID a35e607cafb290a2b74baf0901000000/job01000000/namespace/nameCPU-0/non_detached, constructor PID1123333 and original registered raylet parent chain. The actor was not parent-registered before failure: do not invent a head_descendant_registered record or retroactively claim one. Capture original constructor start/UID/root/RUNID/ppid metadata and verify exact fresh GCS identity including pid, no restart/GPU allocation, stateDEAD plus original constructorPID absent and stopped driver/WAL quiescent. Only then may a separately reviewed execution clean the original nine known head identities through stable pidfds, raylet first and GCS last. Any extra/unknown live process is not silently authorized for kill; final empty scope and all original PID absence need actual proof. No old no-WAL cleanup recipe or historical DEAD readback substitution.

Reviewer read files/Git only and wrote these review artifacts; no tests, network, SSH, source modification, signals, Ray or GPU activity.
