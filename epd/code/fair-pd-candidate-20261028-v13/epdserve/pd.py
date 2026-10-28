"""CPU-only validation and ingress for the internal E+P / D ablation."""


def validate_pd_config(model, config):
    if "MiniCPM-V-2_6" not in model.model:
        raise ValueError("Fused PD currently supports MiniCPM-V-2_6 only")
    if model.dtype != "fp16":
        raise ValueError("Fused PD requires fp16")
    if config.encoding.data_parallel_size != 0:
        raise ValueError("Fused PD must not create encoding actors")
    p, d = config.context, config.decoding
    if (p.data_parallel_size, d.data_parallel_size) not in ((1, 2), (2, 1)):
        raise ValueError("Fused PD requires P1:D2 or P2:D1")
    for stage in (config.encoding, p, d):
        if stage.tensor_parallel_size != 1 or stage.pipeline_parallel_size != 1:
            raise ValueError("Fused PD requires TP1/PP1")


def validate_pd_batch(request_ids, seqs, requests):
    if not request_ids or len(set(request_ids)) != len(request_ids):
        raise ValueError("Empty batch or duplicate request IDs")
    if any(type(rid) is not int for rid in request_ids):
        raise ValueError("Fused PD requires unsharded integer request IDs")
    if len(seqs) != len(requests) or len(requests) != len(request_ids):
        raise ValueError("PD batch lengths differ")
    for rid, seq, request in zip(request_ids, seqs, requests):
        if request.request_id != rid or set(seq.seq_data) != {rid}:
            raise ValueError("PD request/sequence ID or ordering mismatch")
        if request.enable_irp or request.is_sharded:
            raise ValueError("Fused PD requires unsharded requests")


def enqueue_pd_request(engines, request):
    if type(request.request_id) is not int or request.enable_irp or request.is_sharded:
        raise ValueError("Fused PD requires unsharded integer request IDs")
    eligible = [engine for engine in engines
                if request.get_num_input_tokens() <= engine.sched_config.max_tokens_per_batch
                and engine.scheduler._get_block_needed(request.get_num_input_tokens())
                <= engine.block_manager.max_num_gpu_blocks]
    if not eligible:
        raise ValueError("No active fused P can admit the request")
    def load(engine):
        scheduler = engine.scheduler
        return sum(req.get_num_input_tokens() for req in scheduler.waiting_queue) + (
            scheduler.num_on_fly_request_block * engine.cache_config.block_size)
    engine = min(eligible, key=load)
    engine.scheduler.waiting_queue.append(request)
