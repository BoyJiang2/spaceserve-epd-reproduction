# v5 local preflight interfaces — not an execution approval

Only H20, exactly three approved UUIDs, TP1, the frozen numeric / 8 qualification /
48 calibration / 3 final-G3 units are supported. No backend search, scheduler,
booking mutation, model launcher, process killer or formal-run grant is provided.

`preflight-static.candidate.json` intentionally has candidate state, null host/UID/
root/time and no UUIDs, NUMA map, booking IDs or reviewer authority. It fails before
hardware access. Do not fill these from the old Space ticket or an account booking.

## Static source versus runtime data

The eventual approved `preflight-static.json` must be a Git-tracked, manifest-bound
source file. Static keys are exactly `preflight_guard.STATIC_KEYS`: host, UID,
absolute source root, three UUIDs, exact NUMA map, H20 resource/user, explicitly
approved booking intervals and user time bounds; independent reviewer IDs;
immutable phase request/transfer/wallclock limits, cleanup >=120 seconds and zero
automatic retries. Its approval digest is canonical compact sorted JSON SHA256;
the source manifest also pins the actual file bytes. A runtime file cannot replace
or override it.

Runtime inputs have exactly `INPUT_KEYS`: run ID and bound paths/SHAs for original
booking, source manifest, designated pushed-commit proof, deployment, original
human instruction/approval, independent G1/G2 originals and phase prerequisite.
All artifact paths resolve under their owning artifact directory. Runtime outputs
are confined to `ROOT/runtime/`; code-like untracked files are refused. Environment,
model weights, caches and credentials are outside the source checkout. This code
never reads credentials, `/proc/*/environ`, other-process command lines or network
credentials. Only a process registering itself reads EXP_ROOT and REPRO_RUN_ID.

No current runtime approval files, approved static scope, server deployment or
three-GPU budget are shipped. The candidate cannot be used as a permission grant.

## 1. Fresh source/resource/booking and a durable unit claim

`Claim(config, inputs, owner, unit, phase, candidate, snapshot, now_ms=...)` consumes
original user/G1/G2 scope-bound artifacts, pushed remote raw commit evidence,
actual `git HEAD`, clean tracked files and every deployed source SHA. A source
manifest omitting the guard/collector/consumer/client/static config is refused.
Runtime/deploy host, UID, root, boot, UUIDs and NUMA must match exactly. Original
booking receipt contains the complete read-only API resource/booking records,
origin, observed_ms, explicit matching ID/user/kind/start/end; age <=5 minutes,
no future observation, continuous coverage, active resource and user cutoff minus
cleanup. A filesystem lock is never a booking or authorization.

The resource snapshot is an actual fresh NVML/identity receipt from a separately
authorized read-only admission probe. It must cover only the selected UUIDs and
H20 names/NUMA, empty startup memory or exclusively exact owned processes. No
admission-probe/controller bootstrap is wired here yet; that is a blocking
integration task, not permission to call NVML from an unapproved candidate.

`Claim.reserve(ROOT/runtime/budget.json)` is Linux-only: persistent owned regular
flock, immutable per-unit claim/resource/source record, atomic ledger replace and
file/directory fsync. Reservations are non-refundable even if launch fails.
Duplicate units cannot retry. Accounting is recomputed from frozen unit records,
not trusted summary counters. A crash/partial claim is a preserved manual-review
checkpoint, not an automatic restart. A mere reserved=True does not admit work:
the immutable claim SHA and actual ledger/unit must still agree.

Unit allocations are exact: numeric 0 model requests/36 transfers/1800s;
qualification 8×15 requests/300s; calibration 48×20/225s; selected G3 3×120/1600s;
cleanup reserve 600s. Totals remain 1440 requests, 36 transfers and 20400s=340min.
Every next request/transfer must call admit_request/admit_transfer, which rechecks
durable evidence, unit counters and monotonic/booking deadlines. All formal phases
are rejected. Qualification/calibration/final G3 additionally consume original
independent prerequisite reviews bound to their actual raw evidence.

BLOCKED: no controller currently invokes these calls for every operation; no
actual POSIX flock/fsync/signal or request-cancellation/owned-cleanup test has run.
Checking a deadline before requests does not itself stop a stuck in-flight GPU
operation. The bounded controller/watchdog and exact-owned release integration
must pass independent G2 and target CPU checks before any model/transfer run.

## 2. Actual raw NVML and process registry

`capture_own_identity` runs inside the pinned owned worker, verifies its two
whitelisted identity env values and cwd, and writes its own PID/UID/root/RUNID/
startticks/boot/source/deploy/UUID/stage sidecar. Collector reads only the selected
compute PIDs: UID first, then proc stat/cwd; unknown/foreign UID, inaccessible or
reused PID, wrong root/RUNID/source/sidecar causes a stop without any signal.
There is no global process scan and no cleanup implementation.

`live_evidence.snapshot` uses NVML GetMemoryInfo / ComputeRunningProcesses_v3 /
PCI/Name. It records real integer bytes, UUID, physical capacity/free/used and
NUMA; NVML/driver/API versions are saved. N/A/unresolved process memory fails.
The raw API value is preserved before identity validation can fail. `collect`
requires a genuine durable Claim before constructing the backend; it samples
every 100ms through the caller's actual outer window, records raw API/full frames,
normalized bytes samples and root/UID/run/start/stage registry, then hashes all
originals. Failure preserves partial raw hashes and failure.json. Existing output
directories cannot be reused. Capture receipts say captured_not_G3_approved.

BLOCKED: the baseline and EPD worker registration adapters and the real outer-
window/controller coupling are not wired yet. NVML APIs, PID/cwd behavior, NUMA,
100ms timing, whole-window coverage and target POSIX semantics have CPU mocks
only. No NVML import, device query or server operation occurred in this work.

## 3. Consume selected-three full G3 without signing a gate

`selected_g3.consume` takes a complete bound bundle and the original independently
authored G3 JSON result. Original review must identify an approved independent
reviewer (not the implementer), gate G3, exact proof-scope SHA, APPROVE or
APPROVE_WITH_NITS, blocking=0 and its original text. Review bytes are SHA-bound;
there is no function to issue or synthesize an approval. Real review records must
come from the reviewer/tool output, not copied booleans or CPU test fixtures.

The proof binds static/source/commit/deploy/runtime/NUMA, actual selected three
configs, original claim/ledger/admission booking, common input/reference, and cold
plus complete-process restart evidence per system. Each session has 60 actual
requests, 12 windows covering 1/4/8 images ×32/128 output ×C1/C8; actual IDs/input/
outputs are compared to the selected native reference. Actor stage counts, each
GPU PID/start identity, fresh historical booking scope, full raw memory/provider/
registry/windows and actual empty-GPU release before restart are checked. Every
descriptor is read and hashed. Missing raw, reused processes, changed IDs or a
summary passed flag cannot substitute. Source/full-G3 budgets remain unchanged.

Even a complete consumed proof returns formal_admission blocked: a separate user-
approved formal budget and reviewed execution entrypoint are still required.

## Existing CPU results and target entrypoints

The new mocked suite already ran locally: 13 passed before the latest remote-
CPU-priority instruction. The inherited 35-test suite was not rerun in v5. Do not
repeat either locally now. Main must first verify a CPU reservation/project/host
scope (a GPU ticket is not CPU-lane authority), review and commit/push the source,
then deploy that designated commit to its dedicated remote CPU directory. Pending
target entrypoints are tests/test_pd_cpu.py and tests/test_preflight_v5.py; the
actual POSIX/NVML/integration work needs separately reviewed target checks.

All extra evidence/review artifacts in these tests are explicit CPU-MOCK fixtures
inside owned temporary directories and are deleted after testing. The collector's
durable-claim method is explicitly mocked because real POSIX tests remain pending.
No fixture is a real booking, deployment, user approval, independent runtime G3,
or evidence that any GPU/model mechanism passed.


## v6 edit-only addendum

No v6 suite, syntax check, patch application or target CPU run has been performed.
The old v5 13 mocked passes are historical, not a v6 result. The new endpoint
manifest/actual API and worker route observations are mandatory; baseline cold
and restart each require 20/20/20 requests over three bound APIs. Actual producer
adapters and finite official-CLI controller remain blocked.

Durable claims now carry actual perf_counter/UTC start and exact allocation
boundaries; G3 session/snapshot/release/API-exit clocks must be finite, same boot,
within 100ms of that anchor and inside the true 1600s unit, with previous system
release preceding the next claim. New rejection tests are only source, unrun.

cpu_target_runner.py is a separate unreviewed short CPU candidate. It has no
permit/handoff artifacts and must not run merely because the clock passed 18:00.
Parent invocation must already be taskset CPU50 with empty CUDA visibility; only
fresh actual CPU15–21 booking, four-domain 18+ releases, no new takeover/CPU50
conflict, designated reviewed pushed commit and full 330s before 19:00 permit it.
It preserves AF_UNIX/self-pipe for real asyncio, allows reviewed git/own-Python
POSIX helpers, and blocks GPU imports/TCP/UDP/unknown services. It records actual
test IDs/raw logs/exit/source-before-after for retrieval if eventually authorized.
Child RLIMIT_AS is 1GiB; cgroup-total RSS is not claimed. POSIX timeout/cleanup and
all new tests are unverified. Scope/review/resource/G5 gaps each keep it blocked.

Next integration uses one non-refundable finite unit argv/request-vector claim,
then unitID and the existing raw journal during measurement. Do not wire the old
heavy per-request ledger/manifest/API checks into the timed benchmark. Numeric
36 transfers remain a separate non-performance phase with per-transfer checks.
