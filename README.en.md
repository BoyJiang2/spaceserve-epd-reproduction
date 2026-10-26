# SpaceServe / EPD: bounded artifact reproduction

This public repository preserves a small-scale reproduction of fixed public implementations, including negative results. It does not reproduce the complete paper systems or claim their reported speedups. The owner made the repository and Release assets public on 2026-10-26; initial private-publication receipts are retained as historical evidence.

## SpaceServe

[Independent SpaceServe project page](spaceserve/README.md): one H20/Qwen2-VL-7B, compared with native vLLM on that GPU. All six workload points, regressions, mechanisms, legacy4090/L20 results and commands stay together.

## EPD Disaggregation

[Independent EPD project page](epd/README.md): MiniCPM-V-2_6, three H20 GPUs, compared with three full replicas using the same GPU budget. Profile-A, historical H20 results and offline follow-up are kept distinct.

SpaceServe's encoder/decoder overlap and encoder-stream mask were observed; complete SIS/TWSRFT and mutually exclusive decoder partitioning were not reproduced. EPD uses E:P:D=1:1:1 with IRP and dynamic role switching disabled. Visual-token storage and migration remain present. Fixed-concurrency results are not arrival-rate SLO results. Fixed run order and three repeats limit causal interpretation; differing output IDs and regressions are retained.

Start with the [Chinese results and commands](README.md), [paper-claim coverage](PAPER_VS_REPRO.md), [patch audit](PATCH_AUDIT.md), [portability and verification status](PORTABLE.md), and [upstream licenses](THIRD_PARTY_NOTICES.md). Small request records and readable reports are in Git; complete original archives, including large traces, are indexed with sizes/SHA256 in [ASSETS](publication/ASSETS.md).

CPU-only descriptive figure regeneration from the checked-out data:

```bash
python scripts/revision/compare_existing_space.py
```

Requires Python with Matplotlib 3.9.2; the source measurement environments are pinned separately per batch. This command does not run inference. No new GPU run has been used to produce the documentation revision. Internal LLM review is not external peer review.
