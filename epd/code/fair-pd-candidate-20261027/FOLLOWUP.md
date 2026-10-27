# CPU candidate for the EPD / PD / replica followup

This directory is a new local implementation based on EPDServe commit
9b111f710dfb4724072b603d626a1e4dad93ef1f. It is not an approved deployment.
The PD system is an internal E+P / D ablation, not DistServe.

These are source entrypoints, not permission to rerun local CPU work. Per the
latest instruction, main must verify a legal remote CPU/project/host scope and
deploy an independently reviewed designated Git commit before further validation.
The scripts do not import torch/ray/vllm or issue model requests:

```powershell
python work/epd-pd-followup-20261027/v6/tests/test_pd_cpu.py
python work/epd-pd-followup-20261027/v6/experiment_plan.py
python work/epd-pd-followup-20261027/v6/experiment_plan.py --full
python work/epd-pd-followup-20261027/v6/experiment_plan.py --select calibration-rows.json
```

The select command takes a JSON object containing source_manifest_sha256,
runtime_binding_sha256, runtime_binding_file, qualification_inputs_sha256,
qualification_reference_sha256, qualification_receipts (all eight candidate IDs to
relative receipt paths) and all 48 calibration rows, including failures and not-run cells.
Each exact S/L candidate must first pass its own 15-request qualification, bound
to its canonical candidate-arguments SHA, source/runtime SHA and actual raw log
SHA. Calibration rows bind the same qualification receipt SHA and configuration.
A bare correctness_passed flag is insufficient. Source/runtime/profile mismatch,
changed raw log, insufficient case counts, unrealized concurrency or qualifying
only another profile is rejected. The selector output always blocks formal
admission until three selected exact configurations each complete independent
cold/restart/multimodal/concurrent G3 (120 requests each) and its review.

Qualification is 120 requests across eight candidates; final full G3 is 360 across
three selected configurations. The total correctness budget remains 480, with
960 calibration requests unchanged. There is no automatic runner-up/retry if a
selected final configuration fails G3. Schedules only print JSON and do not run.
The final-G3 evidence consumer/resource guard still needs implementation and
independent G2 before any actual formal run.

Fused PD ingress requires `--pd-fused --encoding-data-parallel-size 0` and
P:D equal to 1:2 or 2:1, with TP1/PP1. `--runtime-max-num-seqs` is 4 or 8;
`--context-max-batch-size`, `--decoding-max-batch-size` and EPD's encoding batch
must match the selected profile. The new common engine settings require GPU
memory utilization .65, MiniCPM-V-2_6, FP16, eager, 4096 context/batch tokens,
seed 0, eight-image support and no prefix/feature cache. RGB preload must be
identical across groups. `baseline_server.py` is the same vLLM adapter with
eight-image support and the shared settings; run three independent complete
replicas and distribute requests over their three endpoints. `benchmark.py`
supports 1/4/8 images, writes failures and refuses to append to existing results.

The local tests execute production methods extracted through AST, using CPU
fakes. They prove routing/control behavior and failure propagation under those
fakes. They do not prove CUDA correctness, actual model outputs, Ray placement,
memory availability, concurrent execution or performance. The Windows sandbox
cannot create asyncio's loopback socketpair; the tests therefore use immediate
CPU coroutine fakes, with no event loop or network. An initial attempt diagnosed
that limitation; the completed suite is not a skipped async integration test.

Before deployment: independent G1/G2; frozen model/dataset/calibration/formal
manifests; actual engine API compatibility and CUDA IPC extension provenance;
reviewed resource/budget guards; main-thread commit/push; designated commit
checkout and per-file verification on the server. The upstream source lacks
the built CUDA IPC extension in this copy; `CUDA_IPC_LIB_PATH` must point to an
independently pinned compatible environment artifact, never an untracked server
source fix. Run numeric checks, eight exact-candidate qualifications, independent calibration,
then full cold/restart/multimodal/concurrent G3 of the three selected configurations
and its independent review before formal admission. No GPU launcher or auto-deploy command is supplied here.

Keep the active Space window first and isolated. A new three-GPU EPD reservation
and explicit scope/UUID ownership are mandatory. The detailed unapproved budget
and complete-block schedules are in outputs/pd-baseline-proposal/plan-v6.md.


v3 admission corrections: qualification compares actual bound prompt/image/RGB
fixtures and native reference processed/output IDs; a reference_match boolean is
ignored. Calibration requires per-cell raw memory samples and process registry,
full 4+16 raw request timing, bytes/capacity/cap, host/boot and UID/RUNID/PID/start
attribution. The cap per GPU is min(floor(.65 * physical capacity), fresh admission
free bytes). No summary peak can substitute. Missing, stale, foreign, malformed,
oversized, wrong-unit, bad-SHA or uncovered data fail closed. The raw collectors
and final G3 consumer/guard are still pending independent implementation/review.

Scoring is fixed before data: mean the two repeats within each load, then take
the geometric mean over C/D/E. Ties require best_score / score <= 1.03; select
smaller profile, then P1:D2. GPU calls and request budgets remain unchanged.

The CLI reads runtime_binding_file with the specified SHA before accepting its
three-GPU capacity/free/cap/UID/host/boot policy. Each qualification receipt points
to inputs_file/reference_file/requests_file with their SHA values. Every passing
calibration row also names memory_receipt_file and memory_receipt_sha256, run_id,
warmup_start_monotonic and measure_end_monotonic. Memory receipts point to the
actual 20-request JSONL, process registry JSON and sample JSONL with separate SHAs.
A successful row whose raw evidence is inconsistent rejects the whole selection;
a genuinely failed candidate keeps its failed/not_run records and is ineligible.


v4 rates come only from a SHA-bound client-window.json and the corresponding
20 actual client request rows. The window records warmup/measurement outer start
and end perf_counter values, same host/boot/UID/run/source/config/runtime identity,
4/16 counts and requests.jsonl SHA. A calibration benchmark call requires
--calibration-metadata and exactly --warmup 4 --requests 16 --repetitions 1.
It captures measurement start immediately before creating/submitting the gather
and end immediately after awaiting its completion, retaining the original outer
batch wallclock definition. It writes actual raw rows/window without using summary
as the timing source. Each memory receipt additionally names client_window_file
and client_window_sha256; each calibration row includes measurement_start_monotonic.
Consumer recomputes 16 / duration, uses that rate to score, and rejects summary
mismatch (relative tolerance 1e-9, absolute 1e-12). It does not replace the outer
window with min-submit / max-response span. Client metadata/clock/header writer
has CPU fake roundtrip tests; no real calibration request was issued.


v5 adds fixed-H20 preflight interfaces only: preflight_guard.py, live_evidence.py,
selected_g3.py. See PREFLIGHT.md for the exact static/runtime whitelist, actual
read-only receipt requirements, immutable durable budget claims, NVML bytes/PID
identity raw capture and original independently reviewed full-G3 proof consumer.
The shipped static configuration is candidate-only with null scope and refuses
hardware admission. Controller/per-request/transfer wiring, worker registration,
actual POSIX and NVML verification remain blocked. No model/GPU/server/network or
push was performed; fake CPU fixtures are never actual runtime G3 evidence.

Latest CPU placement rule: local edits/view/review only; no repeated local suite.
Existing v5 new-suite result is 13 mocked passes before that instruction, with
real target POSIX/NVML still pending. The inherited v4 35-pass result is preserved
without claiming a v5 rerun. Do not infer CPU-lane permission from a GPU booking.


v6 is edit-only and untested. selected G3 now requires actual endpoint/API/worker
identity observations, full three-replica round-robin coverage in each cold/restart
session, and anchored actual durable-claim UTC/perf deadlines and cross-system
release ordering. Producers/controller are still blocked. cpu_target_runner.py
is a separate unreviewed conditional qjh001 CPU50 candidate; it has not run.
Do not label old v5 13 mocked passes as v6/target validation. See proposal
source-feasibility-v6.md for the exact remaining boundaries and conditional CPU
requirements. No resource handoff or execution is implied.
