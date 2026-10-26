# SpaceServe / EPD: bounded artifact reproduction

This private repository preserves a small-scale reproduction of fixed public implementations, including negative results. It does not reproduce the complete paper systems or claim their reported speedups. Access to the repository and Release assets requires authorization.

| Experiment | Fair baseline | Observed result |
|---|---|---|
| SpaceServe, Qwen2-VL-7B, one H20 | Native vLLM on the same GPU | Decoupled throughput changes from -6.32% to +5.86%; encoder-mask changes from -7.52% to +6.29% |
| EPD profile A, MiniCPM-V-2_6, three H20 GPUs | Three complete-model replicas on those GPUs | Profiler-off throughput is 0.930x / 0.941x at the low/high workload points |

SpaceServe's encoder/decoder overlap and encoder-stream mask were observed; complete SIS/TWSRFT and mutually exclusive decoder partitioning were not reproduced. EPD uses E:P:D=1:1:1 with IRP and dynamic role switching disabled. Visual-token storage and migration remain present. Fixed-concurrency results are not arrival-rate SLO results. Fixed run order and three repeats limit causal interpretation; differing output IDs and regressions are retained.

Start with the [Chinese results and commands](README.md), [paper-claim coverage](PAPER_VS_REPRO.md), [patch audit](PATCH_AUDIT.md), [portability and verification status](PORTABLE.md), and [upstream licenses](THIRD_PARTY_NOTICES.md). Small request records and readable reports are in Git; complete original archives, including large traces, are indexed with sizes/SHA256 in [ASSETS](publication/ASSETS.md).

CPU-only descriptive figure regeneration from the checked-out data:

```bash
python scripts/revision/compare_existing_space.py
```

Requires Python with Matplotlib 3.9.2; the source measurement environments are pinned separately per batch. This command does not run inference. No new GPU run has been used to produce the documentation revision. Internal LLM review is not external peer review.
