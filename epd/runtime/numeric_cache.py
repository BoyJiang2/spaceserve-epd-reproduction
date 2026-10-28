"""Native full-cache probe component, not a runnable controller or a G3 approval."""
import hashlib
import json
import math
import os
from pathlib import Path

CHUNK_ELEMENTS = 1 << 20
SCRATCH_RESERVE_BYTES = 128 << 20
PARALLEL = [1, 0, 1, 0, 1, 0]


def transfer_vector(uuids):
    if len(uuids) != 3 or len(set(uuids)) != 3 or any(not isinstance(u, str) or not u for u in uuids):
        raise ValueError('Exactly three distinct approved UUIDs required')
    rows = []
    for source in uuids:
        for target in uuids:
            if source == target: continue
            for kind in ('kv', 've'):
                for repetition in range(3):
                    rows.append({'ordinal': len(rows), 'source_uuid': source, 'target_uuid': target,
                                 'kind': kind, 'repetition': repetition, 'seed': len(rows) + 1})
    return rows


def chunk_ranges(elements):
    if type(elements) is not int or elements < 1:
        raise ValueError('Nonempty full tensor required')
    return [(start, min(elements, start + CHUNK_ELEMENTS)) for start in range(0, elements, CHUNK_ELEMENTS)]


def worker_policy(worker, kind):
    if os.environ.get('REPRO_NUMERIC_ONLY') != '1' or kind not in ('kv', 've'):
        raise ValueError('Explicit numeric-only scope and payload required')
    if (worker.stage.name != 'DECODING' or worker.model is not None or hasattr(worker, 'model_runner')
            or worker.parallel_config.to_list() != PARALLEL):
        raise ValueError('Only fresh model-free TP1/PP1 DECODING probe workers allowed')
    model, cache = worker.model_config, worker.cache_config
    if (Path(model.model).name != 'MiniCPM-V-2_6' or model.dtype != 'fp16'
            or model.pd_fused or model.use_dummy_weights or cache.cpu_swap_space != 0
            or cache.gpu_memory_utilization != .65 or type(cache.block_size) is not int or cache.block_size < 1):
        raise ValueError('Frozen MiniCPM/FP16/native cache policy differs')


def geometry(tensor, kind):
    axis = 2 if kind == 'kv' else 0
    shape = list(tensor.shape)
    if (kind not in ('kv', 've') or len(shape) != (6 if kind == 'kv' else 3)
            or any(type(n) is not int or n < 1 for n in shape) or str(tensor.dtype) != 'torch.float16'
            or tensor.device.type != 'cuda' or not tensor.is_contiguous() or tensor.storage_offset() != 0):
        raise ValueError('Native CUDA FP16 contiguous full-cache tensor required')
    if kind == 'kv' and shape[1] != 2:
        raise ValueError('Native KV axis differs')
    storage = tensor.untyped_storage().nbytes()
    if storage != math.prod(shape) * 2:
        raise ValueError('Tensor must own the exact full native allocation')
    return {'kind': kind, 'shape': shape, 'stride': list(tensor.stride()), 'dtype': str(tensor.dtype),
            'storage_bytes': storage, 'block_axis': axis, 'blocks': shape[axis], 'elements': math.prod(shape)}


def match_geometry(source, target):
    if source != target:
        raise ValueError('Source/target complete geometry differs; native KV uses target block stride')


def allocate(worker, kind, torch):
    worker_policy(worker, kind)
    if getattr(worker, '_numeric_probe_state', None) is not None:
        raise ValueError('One payload allocation per fresh worker lifetime')
    identity = worker.qualification_identity()
    if identity is None:
        raise ValueError('Actual registered CUDA worker identity required before payload allocation')
    cache, model, parallel = worker.cache_config, worker.model_config, worker.parallel_config
    if kind == 'kv':
        blocks, cpu_blocks = worker._profile_num_available_blocks(cache.block_size, .65, 0)
        bytes_per_block = worker._get_block_size_in_bytes(cache.block_size, model, parallel)
    else:
        blocks, cpu_blocks = worker._profile_num_available_blocks_encoding(cache.block_size, .65, 0)
        bytes_per_block = worker._get_block_size_in_bytes_encoding(cache.block_size, model, parallel)
        if blocks != 3000 or tuple(worker.get_perimage_embedding_size()) != (64, 3584):
            raise ValueError('Official MiniCPM VE geometry changed; do not shrink the payload')
    if type(blocks) is not int or blocks < 1 or cpu_blocks != 0 or type(bytes_per_block) is not int or bytes_per_block < 1:
        raise ValueError('Official cache capacity is invalid')
    capacity = torch.cuda.get_device_properties(worker.device).total_memory
    planned = blocks * bytes_per_block
    if planned + torch.cuda.memory_reserved(worker.device) + SCRATCH_RESERVE_BYTES > int(capacity * .65):
        raise ValueError('Full native cache plus bounded scratch exceeds common memory policy')
    handle = (worker.init_kvcache_and_swap if kind == 'kv' else worker.init_vecache_and_swap)(blocks, 0)
    tensor = worker.kv_cache if kind == 'kv' else worker.ve_cache
    actual = geometry(tensor, kind)
    if actual['blocks'] != blocks or actual['storage_bytes'] != planned:
        raise ValueError('Actual native allocation differs from the official capacity calculation')
    config_file = Path(model.model) / 'config.json'
    descriptor = {'geometry': actual, 'identity': identity, 'handle': handle,
        'model_config_sha256': hashlib.sha256(config_file.read_bytes()).hexdigest(),
        'worker_source_sha256': hashlib.sha256((Path(__file__).parent/'epdserve/worker.py').read_bytes()).hexdigest(),
        'probe_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'workload_scope': 'numeric_native_cache_no_model_weights', 'model_loaded': False,
        'GPU_capacity_bytes': capacity, 'scratch_reserve_bytes': SCRATCH_RESERVE_BYTES}
    worker._numeric_probe_state = {'tensor': tensor, 'descriptor': descriptor,
        'prepared': 0, 'copied': 0, 'registration': None}
    return descriptor


def expected_chunk(torch, start, end, seed, device):
    # Int64 indices, in-place remainder, FP16 expectation and bool comparison fit the scratch reserve.
    indices = torch.arange(start + seed * 37, end + seed * 37, dtype=torch.int64, device=device)
    indices.remainder_(1021)
    return indices.to(dtype=torch.float16)


def fill_and_check(tensor, seed, torch, fill):
    flat = tensor.view(-1)
    for start, end in chunk_ranges(tensor.numel()):
        expected = expected_chunk(torch, start, end, seed, tensor.device)
        if fill: flat[start:end].copy_(expected)
        if not bool(torch.all(flat[start:end] == expected).item()):
            raise ValueError('Full native cache numeric comparison failed at ' + str(start))
    torch.cuda.synchronize(tensor.device)
    return {'full_equal': True, 'checked_elements': tensor.numel(), 'seed': seed}


def validate_transfer(worker, transfer, destination):
    state = worker._numeric_probe_state
    uuids = json.loads(os.environ['REPRO_GPU_UUIDS'])
    vector = transfer_vector(uuids)
    ordinal = transfer.get('ordinal')
    if type(ordinal) is not int or not 0 <= ordinal < len(vector) or vector[ordinal] != transfer:
        raise ValueError('Transfer is not in the exact finite 36-item vector')
    own = state['descriptor']['identity']['gpu_uuid']
    key, counter = ('target_uuid', 'copied') if destination else ('source_uuid', 'prepared')
    if (own != transfer[key] or state['descriptor']['geometry']['kind'] != transfer['kind']
            or transfer['repetition'] != state[counter] or state[counter] >= 3):
        raise ValueError('Wrong payload/UUID/order or fourth transfer in a worker lifetime')
    return state


def prepare_source(worker, transfer, torch):
    worker_policy(worker, transfer['kind'])
    state = validate_transfer(worker, transfer, False)
    if state.get('source_pair') not in (None, transfer['target_uuid']):
        raise ValueError('Fresh worker required for a different directed pair')
    state['source_pair'] = transfer['target_uuid']
    state['prepared'] += 1  # Failed preparation cannot be retried in this worker lifetime.
    checked = fill_and_check(state['tensor'], transfer['seed'], torch, True)
    return {**state['descriptor'], 'transfer': transfer, 'source_validation': checked}


def copy_full_cache(worker, transfer, source, torch):
    worker_policy(worker, transfer['kind'])
    state = validate_transfer(worker, transfer, True)
    target = state['descriptor']
    match_geometry(source['geometry'], target['geometry'])
    if (source['transfer'] != transfer or source['model_loaded'] is not False
            or source['workload_scope'] != target['workload_scope']
            or source['model_config_sha256'] != target['model_config_sha256']
            or source['worker_source_sha256'] != target['worker_source_sha256']
            or source['probe_source_sha256'] != target['probe_source_sha256']
            or source['source_validation'] != {'full_equal': True,
                'checked_elements': target['geometry']['elements'], 'seed': transfer['seed']}):
        raise ValueError('Actual source payload/config/numeric scope differs')
    for key in ('uid','root','host','run_id','boot_id','source_commit','deploy_sha256','candidate_config_sha256','endpoint'):
        if source['identity'][key] != target['identity'][key]:
            raise ValueError('Source worker is not in this exact unit')
    if source['identity']['gpu_uuid'] != transfer['source_uuid'] or source['identity']['pid'] == target['identity']['pid']:
        raise ValueError('Distinct actual source CUDA process required')
    registration = {'handle': source['handle'], 'identity': source['identity']}
    if state['registration'] is not None and state['registration'] != registration:
        raise ValueError('Handle/source identity changed; fresh process required')
    state['copied'] += 1  # Charge before native registration/copy; any failure stops this group.
    tensor = state['tensor']; tensor.fill_(-1); torch.cuda.synchronize(tensor.device)
    if state['registration'] is None:
        if transfer['kind'] == 'kv': worker.register_kvcache_mem_handles_context(worker.parallel_config, [[source['handle']]])
        else: worker.register_kvcache_mem_handles_encoding(worker.parallel_config, [[source['handle']]])
        state['registration'] = registration
    blocks = list(range(target['geometry']['blocks']))
    if transfer['kind'] == 'kv': worker.migrate_blocks_context(blocks, worker.parallel_config, blocks)
    else: worker.migrate_blocks_encoding(blocks, worker.parallel_config, blocks)
    torch.cuda.synchronize(tensor.device)
    checked = fill_and_check(tensor, transfer['seed'], torch, False)
    if state['copied'] == 3 and transfer['kind'] == 'kv':
        worker.unregister_kvcache_mem_handles_context(worker.parallel_config)
    return {'transfer': transfer, 'source_identity': source['identity'], 'target_identity': target['identity'],
            'geometry': target['geometry'], 'destination_validation': checked,
            'requires_importer_context_exit_before_source_release': True,
            'scope': 'raw_numeric_facts_not_independent_G3'}


def probe(worker, action, argument, torch):
    if getattr(worker, '_numeric_probe_failed', False):
        raise ValueError('Failed numeric worker cannot continue or retry')
    try:
        if action == 'allocate': return allocate(worker, argument, torch)
        if action == 'prepare': return prepare_source(worker, argument, torch)
        if action == 'copy': return copy_full_cache(worker, argument['transfer'], argument['source'], torch)
        raise ValueError('Unknown numeric probe operation')
    except BaseException:
        worker._numeric_probe_failed = True
        raise
