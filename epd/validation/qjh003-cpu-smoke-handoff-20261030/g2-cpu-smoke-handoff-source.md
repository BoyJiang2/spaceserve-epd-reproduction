# G2 — single CPU smoke handoff source and connection provenance

APPROVE_WITH_NITS / BLOCKING 0 for exact two-file source only. This does not approve a remote run or assert any actual smoke criterion passed.

Production source reads the existing owned bounded driver journal through events(), consuming complete newline records. It rejects more than one connected_existing_head, requires exact five source fields, expected loopbackaddress/private session, owns_processes isFalse, numeric nonbool finite nonnegative nonfuture monotonic time. Parent mirrors actual sourceaddress/session/owns flag plus helddriverPID, original driver_event_monotonic_s and explicit verified_current_driver_events provenance. Parent monotonic timestamp is its own observation time. Connection state prevents duplicate parent emission across polling; actor submission is rejected unless a real connection event was accepted. No old journal is rewritten and no fact is synthesized from configuration alone.

The trusted writer is the fixed deployed driver, which emits connected_existing_head only after actualray.init and verified owns-processes=False/address validation. Fresh exclusive runfolder and exact sourcepins are essential assumptions: this source gate does not authorize an external sameUID writer replacing journal bytes during the run. Nit: once accepted, the single connection row is not revalidated for later in-place mutation, and timestamp lowerbound is zero rather than an explicitly held driver-spawn time. For the current fixed append-only driver and exclusive output this does not fabricate a fact; strengthen if arbitrary competing writers are ever allowed, without reinterpreting sourceG2 as actual evidence.

Normaldriver exit barrier6c952 remains source-intact, preserving original deadline/cancellation/returncode and strict collector checks. The source does not alter lifecyclepolicy; concrete new wrapper must pass --smoke explicitly and retain CPU50/nice10/noGPU. Old run_smoke3.sh shortcuts are not adopted. Venv/loader connection was already actually progressing previously, so these changes do not resurrect obsolete address/import failure claims.

Seven new source fixtures independently check original timestamp/provenance/address/private session/driverPID and ordering before actor acceptance, wrongaddress/session/owns flag, duplicate/missing connection andNaN. Original201tests/7FAIL and final201OK logs plus existingpolicy4OK give205distinctlocaltests. Reviewer did not execute them. Local facts are not actualsmoke.

User handoff five acceptance criteria remain correctly wired for future actualrun: original process exit0; terminalexit0/smokeTrue; actualparent connection event127.0.0.2:49180 with source matching; ordered actor_submission→livebinding→scenario_terminal→knownprocessesabsent; exact own-run finalscope empty and originalknownPID absence with unknown/refusal strict. This source addition supplies parent connection provenance only; remaining criteria still require new original runtime evidence. Single normal non_detached smoke success must not be called full4/GPU/backend pass. Exact wrapper/config source review, publicationG4/G5, actualfixeddeploymentG3, freshCPUpermission and concrete executionG2 remain required.

Reviewer read local source/logs only and wrote these artifacts, without tests/network/SSH/source edits/Ray/GPU execution.

- epd/runtime/numeric_cpu_lifecycle.py: `ebf2a1589374b68f90be43d2394a1733d17ff6556499c388dff7f9baf66d2963`

- epd/runtime/tests/test_numeric_cpu_lifecycle_cpu.py: `e7775d718e156503283134a9cb2c90fe92758f00db732af9fc968bacd512dcea`
