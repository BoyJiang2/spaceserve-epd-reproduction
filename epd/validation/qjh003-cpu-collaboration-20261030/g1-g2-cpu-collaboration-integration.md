# G1/G2 — CPU collaboration integration plan and source

Decision: APPROVE_WITH_NITS / BLOCKING 0, conditional source/plan only. This does not authorize deployment or CPU execution and does not reuse the rejected prior2d2 deployment approval.

The newly fetched collaborator commit e0fada6b435917e065bc4e7ab9a41dfb66c0b156 has parent2d2f8018f3f9125ead3da169bf7ea8753141f5b9 and changes exactly three paths: new lifecycle_policy.py, its four pure tests, and numeric_cpu_lifecycle.py. Reviewer inspected the actual Git diff read-only. User-authorized collaborator changes must be preserved. Proposed merge has parents6550b48ae8d80588ccd73db5e1f97828fff06a3d ande0fada6b435917e065bc4e7ab9a41dfb66c0b156; their changed code paths are disjoint. Keep e0's three files byte-identical and retain6550 driver54fd9f719649c25c08d5710e5dd2ba022c549358bfcb7d32b500980f92746ad2 and test7d2709e4ae7ce651a97f2c1f64adb043eb6ee7d1d898f67d1766e0c62ca9f3ff.

For default smoke=False, lifecycle_scenarios returns exactly((False,False),(True,False),(False,True),(True,True)); budgets returns started+180/started+300, keeping120seconds cleanup; scenario_deadline returns min(work_end,now+30). Identity, GCS, descendant collection, pidfd cleanup and GPU paths are unchanged. Exact CPU50/nice10 is still required when args.smoke is false. Terminal merely adds truthful smoke/affinity/nice fields.

The current run_cpu_actor_reference_remote.py sets sys.argv only to script,--config,configpath and passes no --smoke. argparse store_true defaults False, so the reviewed four-scenario path does not reach the relaxed affinity/nice branch. No smoke test may be counted as full4 success; no shorter budgets or relaxed CPU configuration are approved for this regression.

Before final merged-source binding: primary must provide exact merged tree and actual combined180fixture log, demonstrating all three collaborator files unchanged and6550's two actor-reference files unchanged. New publication, fixed merged commit/bundle, fresh actual server prior/source/no-live checks, deployment execution G2, physical deployed source G3, and fresh CPU ticket are still required sequentially. This report creates no markers for those future steps.

Nit: new policy tests assert length and first entry rather than full scenario tuple; direct source review establishes the unchanged order here. The reviewed full regression should retain the original scenario lifecycle tests. No unrelated refactor is needed.

Reviewer executed no tests, network, SSH, deployment, Ray or GPU work; only file/Git reads and review-file writes.
