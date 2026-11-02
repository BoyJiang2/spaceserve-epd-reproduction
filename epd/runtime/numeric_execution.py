"""Frozen native36 execution envelope; no hardware imports or authorization issuer."""
from pathlib import Path

from numeric_cache import transfer_vector
from preflight_guard import digest


def profile(model):
    return dict(model=str(model), dtype='fp16', seed=0, pd_fused=False,
        use_dummy_weights=False, parallel=[1, 0, 1, 0, 1, 0], block_size=16,
        max_num_blocks_per_req=256, gpu_memory_utilization=.65, cpu_swap_space=0,
        max_model_len=4096, max_num_seqs=8, enforce_eager=True)


def execution(model, uuids, source_sha):
    settings = profile(model)
    return dict(schema='epd-fixed-unit-v1', phase='numeric', unit='numeric', candidate=None,
        source_manifest_sha256=source_sha, candidate_config_sha256=digest(settings),
        profile=settings, max_requests=0, max_transfers=36, wall_seconds=1800,
        request_diagnostics=False, transfers=transfer_vector(uuids))


def validate(spec, layout, config, source_sha):
    expected = execution(layout.asset('models/MiniCPM-V-2_6'), config['gpu_uuids'], source_sha)
    # JSON equality alone accepts True == 1 and integer/float substitutions.
    if digest(spec) != digest(expected):
        raise ValueError('Exact full native36 profile/vector/source required')
    model = Path(spec['profile']['model'])
    if model.resolve(strict=True) != model or not model.is_dir():
        raise ValueError('Canonical existing project model metadata required')
    for path in (model, *model.parents):
        if path.is_symlink(): raise ValueError('Linked numeric model ancestry refused')
    return spec


def worker_configs(settings, check):
    """Only called after real authorization and private-head connection."""
    check()
    import inspect
    from vllm import EngineArgs
    from epdserve.config import ModelConfig, CacheConfig, ClusterParallelConfig
    from runtime_options import engine_options
    options = engine_options(settings['model'], .65, 8, inspect.signature(EngineArgs).parameters)
    engine = EngineArgs(**options).create_engine_config()
    check()
    model = ModelConfig(settings['model'], settings['model'], dtype='fp16', seed=0,
                        use_dummy_weights=False, vllm_config=engine, pd_fused=False)
    cache = CacheConfig(16, 256, .65, 0)
    parallel = ClusterParallelConfig()
    check()
    return model, cache, parallel
