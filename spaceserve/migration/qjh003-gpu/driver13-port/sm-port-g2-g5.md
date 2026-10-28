G2/G5 initial review: BLOCKING 1; execution not yet approved. reviewed_at 2026-10-28T21:05:10Z.

Source tools/probe_space_driver13_offset.py SHA256 1aa47ac3b701d22a3b275fd6626f37bffd4a649ee1f65648f84ef6483846bb2f; independent static compile PASS without execution.

The fixed three inputs, native-only/no-MPS scope, owned host lock, exact GPU0UUID/boot and fresh dual-booking checks, maximum32 offsets, complete SM records and strict subset/restore/reapply validation, three independent repetitions, abnormal-exit stop and pidfd session cleanup are consistent with the final G1 scope.

Unique blocking finding: idle() at lines33-40 checks the work deadline before two queries but each query has an unconditional10-second timeout and no post-query work check. A last successful repetition can therefore finish work past180 seconds and still report passed, while cleanup queries can pass the300-second total endpoint. Bind each query timeout to its remaining appropriate endpoint (work deadline or cleanup started+300), reject nonpositive remaining time, and recheck the work deadline after both normal idle queries. Cleanup must use its separate endpoint. No broader changes required.

No diagnostics, tests, SSH, network or GPU operations performed by reviewer. This file is the sole requested review output written. Native success would remain a compatibility candidate only, not MPS/service/GPU G3 or model permission.

Closure addendum reviewed_at 2026-10-28T21:06:02Z: G2/G5 APPROVE; BLOCKING 0. Both query timeouts now consume the correct remaining work/cleanup endpoint and check again after querying; unique blocking finding closed. Final source SHA256 278228d9ea84833f64bb9879bb33fecfe461a1a6cf5d2a24eb21071203ba7d4f.

Exact approved inputs: original compiled probe e1c739868516e399c0499419d7559d0bdef73786dd00c59a6c27b9e633535797 (1030224 bytes); original probe_sm_mask.cu 2919f83d0988ec23576199389b2d3b2765944188f9526393a34f8daea21e1935 (3019 bytes); original assets/build/libsmctrl.so 529e2502f633b0d7ef07db2848c64e42154cea73992a794c27a31d0361e5e7c5 (21440 bytes). These match sm-port-inputs.json and hardcoded INPUTS. Boot65f52a67-afe4-4919-8646-4694255b48ee, GPU0/UUID GPU-dd8ab4ed-e34e-4141-ced9-271897da8282, qjh003 UID2147 remain fixed.

Allows ordinary publication and, after actual ref/exact-source-byte verification plus fresh owned CPU/GPU booking and current idle/identity/lock admission, one bounded native diagnostic:32 candidates maximum0..248 step8, each3s, first success followed by at most three independent repetitions,180 work plus120 cleanup. Any abnormal exit/timeout/CUDA error/unconfirmed release stops the entire sequence. No retries, MPS/model launch, old evidence modification or G3 success authorization.

GATE_RESULT: {"gate":"G2+G5-bounded-native-diagnostic","decision":"APPROVE","blocking":0,"reviewed_at":"2026-10-28T21:06:02Z","MPS_or_model_authorized":false}
