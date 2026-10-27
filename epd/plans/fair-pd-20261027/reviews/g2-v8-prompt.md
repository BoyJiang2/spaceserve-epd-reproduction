# G2 v8 narrow independent review

Actual reviewer /root/profile_instrument_review; read-only, no tests/compilation/patch application/network/GPU/writes.

Frozen work/epd-pd-followup-20261027/v8; source-manifest-v8.json SHA256 6cdcda3423ea7f0c88e0bc298aa25622c6602868a43be3ef0961909cf9857f07; 49 members. Delta epd-pd-v7-to-v8.patch SHA256 5bc208d8f61e3f59984d8de97e18b63de4b60affa7ee55490030eeb3db08730f. UNEXECUTED receipt cpu-receipt-v8-unexecuted.json SHA256 e569840ecda6b18a0932523219baa131ca5478f36770c9c58cb30f9cfb81986d.

Only cpu_target_runner.py and tests/test_cpu_target_runner.py changed. Review closure of v7 launch race: TERM/INT are deferred while acquiring Popen object and identity, then routed to unified cleanup. Empty cleanup is unconfirmed. New POSIX test sources deterministically signal after actual fork but before wrapper returns. Check race closure and regression source coverage without execution.

Return actual UTC, APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES, exact blocking locations. Candidate code review only: target CPU remains unexecuted; CPU50 project handoff pending, prior final_release absent. No remote/GPU/publication permission.

