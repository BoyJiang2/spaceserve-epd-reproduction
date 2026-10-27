"""Same vLLM engine settings for the followup replicas, PD and EPD."""


def engine_options(model, memory_utilization, max_num_seqs, supported):
    if "MiniCPM-V-2_6" not in model or max_num_seqs not in (4, 8):
        raise ValueError("Followup requires MiniCPM-V-2_6 and batch profile 4 or 8")
    if memory_utilization != 0.65:
        raise ValueError("Followup requires common GPU memory utilization 0.65")
    options = dict(model=model, dtype="float16", tensor_parallel_size=1,
                   enforce_eager=True, trust_remote_code=True, seed=0,
                   max_model_len=4096, max_num_seqs=max_num_seqs,
                   max_num_batched_tokens=4096, enable_prefix_caching=False,
                   disable_mm_preprocessor_cache=True,
                   gpu_memory_utilization=memory_utilization,
                   limit_mm_per_prompt={"image": 8})
    if "disable_mm_preprocessor_cache" not in supported:
        # vLLM 0.6.1 has no multimodal preprocessor feature cache.
        options.pop("disable_mm_preprocessor_cache")
    missing = set(options) - set(supported)
    if missing:
        raise ValueError(f"Runtime lacks required engine arguments: {sorted(missing)}")
    return options
