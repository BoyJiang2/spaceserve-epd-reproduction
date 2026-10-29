"""Finite native-cache orchestration contract; no GPU backend or admission grant."""
import math
from pathlib import Path
import time

from numeric_cache import SCRATCH_RESERVE_BYTES, match_geometry, transfer_vector


def identity_scope(claim, profile_sha256):
    return dict(host=claim.config['host'], uid=claim.config['uid'], root=claim.config['root'],
                run_id=claim.inputs['run_id'], boot_id=claim.deployed['boot_id'],
                source_commit=claim.deployed['commit'], deploy_sha256=claim.inputs['deploy_sha256'],
                candidate_config_sha256=profile_sha256, engine_stage='DECODING')


def validate_identity(row, scope, uuids):
    if (any(row.get(k) != v for k, v in scope.items()) or row.get('gpu_uuid') not in uuids
            or type(row.get('pid')) is not int or row['pid'] <= 0
            or type(row.get('proc_start_ticks')) is not int or row['proc_start_ticks'] < 1
            or not isinstance(row.get('endpoint'), str) or not row['endpoint']
            or not Path(row.get('cwd', '')).is_absolute()
            or not Path(row['cwd']).is_relative_to(Path(scope['root']))):
        raise ValueError('Numeric worker identity differs from this exact unit')
    return row['pid'], row['proc_start_ticks']


def validate_allocation(row, identity, kind, capacity):
    if (row.get('identity') != identity or row.get('model_loaded') is not False
            or row.get('workload_scope') != 'numeric_native_cache_no_model_weights'
            or row.get('scratch_reserve_bytes') != SCRATCH_RESERVE_BYTES):
        raise ValueError('Actual numeric allocation scope differs')
    geometry = row['geometry']; shape = geometry['shape']; axis = 2 if kind == 'kv' else 0
    if (geometry.get('kind') != kind or len(shape) != (6 if kind == 'kv' else 3)
            or any(type(n) is not int or n < 1 for n in shape)
            or geometry.get('dtype') != 'torch.float16' or kind == 'kv' and shape[1] != 2
            or kind == 've' and shape != [3000, 64, 3584]
            or geometry.get('stride') != [math.prod(shape[i + 1:]) for i in range(len(shape))]
            or geometry.get('block_axis') != axis or geometry.get('blocks') != shape[axis]
            or geometry.get('elements') != math.prod(shape)
            or geometry.get('storage_bytes') != math.prod(shape) * 2):
        raise ValueError('Incomplete native allocation geometry')
    cuda_capacity = row.get('GPU_capacity_bytes')
    if (type(cuda_capacity) is not int or cuda_capacity < 1 or type(capacity) is not int
            or capacity < 1 or geometry['storage_bytes'] + SCRATCH_RESERVE_BYTES > min(capacity, cuda_capacity) * 65 // 100):
        raise ValueError('Full allocation and scratch exceed common capacity')
    if (not isinstance(row.get('handle'), list) or len(row['handle']) != 64
            or any(type(n) is not int or not 0 <= n <= 255 for n in row['handle'])):
        raise ValueError('Original native IPC handle required')
    for key in ('model_config_sha256', 'worker_source_sha256', 'probe_source_sha256'):
        value = row.get(key)
        if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Allocation lacks actual model/source bindings')


def validate_release(receipt, identity, capacity, idle_bytes, earliest, now):
    proc = receipt.get('proc_observation', {}); raw = receipt.get('raw_nvml', {})
    if (receipt.get('identity') != identity or receipt.get('gpu_uuid') != identity['gpu_uuid']
            or proc.get('path') != '/proc/' + str(identity['pid']) or proc.get('exists') is not False
            or proc.get('boot_id') != identity['boot_id']
            or type(proc.get('monotonic_s')) not in (int, float)
            or not earliest <= proc['monotonic_s'] <= now
            or raw.get('capacity_bytes') != capacity or raw.get('processes') != []
            or type(raw.get('used_bytes')) is not int or not 0 <= raw['used_bytes'] <= idle_bytes):
        raise ValueError('Original importer PID/context exit is not confirmed by raw observations')


def execute(claim, backend, emit, profile_sha256, *, clock=time.perf_counter):
    """Backend calls receive remaining time; real Ray/NVML integration stays separate."""
    claim.verify_reservation()
    if (claim.phase != 'numeric' or claim.unit != 'numeric' or claim.requests != 0
            or claim.transfers != 36 or not 0 < claim.deadline - clock() <= 1800
            or type(profile_sha256) is not str or len(profile_sha256) != 64
            or any(c not in '0123456789abcdef' for c in profile_sha256)):
        raise ValueError('One complete recorded numeric36 claim required')
    uuids = claim.config['gpu_uuids']; vector = transfer_vector(uuids)
    if len(vector) != 36 or [r['ordinal'] for r in vector] != list(range(36)):
        raise ValueError('Finite numeric vector changed')
    scope = identity_scope(claim, profile_sha256)
    seen, released, attempted = set(), set(), set()
    completed, groups, cleanup_errors, failure = 0, 0, [], None
    pair, mapping_possible, valid = None, False, {}

    def remaining(work=True):
        if work: claim.check()
        value = claim.deadline - clock() - (claim.config['cleanup_seconds'] if work else 0)
        if value <= 0: raise TimeoutError('Common numeric deadline; no new operation')
        return value

    def close(identity, *, work):
        key = identity['pid'], identity['proc_start_ticks']
        if key in attempted: raise ValueError('Do not retry an unconfirmed actor release')
        attempted.add(key); start = clock()
        raw = backend.close(identity['gpu_uuid'], identity, timeout=remaining(work))
        validate_release(raw, identity, claim.resources['gpus'][identity['gpu_uuid']]['capacity_bytes'],
                         claim.config['max_idle_bytes'], start, clock())
        released.add(key)
        return raw

    try:
        for offset in range(0, 36, 3):
            rows = vector[offset:offset + 3]; group = rows[0]
            pair = group['source_uuid'], group['target_uuid']; mapping_possible = False; valid = {}
            emit('group_start', dict(index=groups, transfers=rows))
            identities = backend.create_group(uuids, timeout=remaining())
            valid, errors = {}, []
            for row in identities:
                try:
                    key = validate_identity(row, scope, uuids)
                    if key in seen or row['gpu_uuid'] in valid: raise ValueError('Worker process/UUID reused')
                    seen.add(key); valid[row['gpu_uuid']] = row
                except Exception as error: errors.append(repr(error))
            if errors or set(valid) != set(uuids) or len(identities) != 3 or len({r['endpoint'] for r in identities}) != 1:
                raise ValueError('Three fresh exact worker identities required: ' + repr(errors))
            emit('group_workers', dict(index=groups, identities=identities))
            source_uuid, target_uuid, kind = group['source_uuid'], group['target_uuid'], group['kind']
            allocations = {}
            for uuid in (source_uuid, target_uuid):
                row = backend.call(uuid, 'allocate', kind, timeout=remaining())
                validate_allocation(row, valid[uuid], kind, claim.resources['gpus'][uuid]['capacity_bytes'])
                allocations[uuid] = row
                emit('allocation', row)
            source, target = allocations[source_uuid], allocations[target_uuid]
            match_geometry(source['geometry'], target['geometry'])
            if any(source[k] != target[k] for k in ('model_config_sha256', 'worker_source_sha256', 'probe_source_sha256')):
                raise ValueError('Source/target native configuration differs')
            for transfer in rows:
                remaining(); claim.admit_transfer()
                emit('submitted', transfer)
                prepared = backend.call(source_uuid, 'prepare', transfer, timeout=remaining())
                expected = dict(full_equal=True, checked_elements=source['geometry']['elements'], seed=transfer['seed'])
                if (any(prepared.get(k) != v for k, v in source.items()) or prepared.get('transfer') != transfer
                        or prepared.get('source_validation') != expected):
                    raise ValueError('Complete actual source preparation differs')
                mapping_possible = True  # A failing native copy may already have imported the IPC mapping.
                copied = backend.call(target_uuid, 'copy', dict(transfer=transfer, source=prepared), timeout=remaining())
                if (copied.get('transfer') != transfer or copied.get('source_identity') != valid[source_uuid]
                        or copied.get('target_identity') != valid[target_uuid] or copied.get('geometry') != target['geometry']
                        or copied.get('destination_validation') != expected
                        or copied.get('requires_importer_context_exit_before_source_release') is not True):
                    raise ValueError('Complete destination/native transfer evidence differs')
                completed += 1
                emit('completed', dict(source=prepared, destination=copied))
            sync = backend.call(target_uuid, 'sync', None, timeout=remaining())
            if sync != dict(identity=valid[target_uuid], synchronized=True): raise ValueError('Importer synchronization differs')
            emit('importer_sync', sync)
            for uuid in (target_uuid, source_uuid, next(u for u in uuids if u not in (source_uuid, target_uuid))):
                emit('release', close(valid[uuid], work=True))
            groups += 1
            emit('group_released', dict(index=groups - 1))
    except BaseException as error:
        failure = error
    finally:
        # Importer exit is a dependency, including on failure; unrelated actors remain independent.
        try: known = backend.known_identities()
        except BaseException as error:
            cleanup_errors.append('registry: ' + repr(error)); known = list(valid.values())
        available, ambiguous = {}, set()
        for row in known:
            try:
                key = validate_identity(row, scope, uuids)
                if key in released: continue
                uuid = row['gpu_uuid']
                if uuid in available or uuid in ambiguous:
                    available.pop(uuid, None); ambiguous.add(uuid)
                    raise ValueError('Ambiguous numeric actor registry; refuse signal')
                available[uuid] = row
            except BaseException as error: cleanup_errors.append(repr(error))
        order = list(uuids) if pair is None else [pair[1], pair[0], next(u for u in uuids if u not in pair)]
        for uuid in order:
            row = available.get(uuid)
            if row is None: continue
            key = row['pid'], row['proc_start_ticks']
            if pair is not None and uuid == pair[0] and mapping_possible:
                importer = valid.get(pair[1])
                if importer is None or (importer['pid'], importer['proc_start_ticks']) not in released:
                    cleanup_errors.append('exporter retained: importer context exit unconfirmed')
                    try: emit('cleanup_blocked', dict(identity=row, depends_on_importer=importer))
                    except BaseException as error: cleanup_errors.append('journal: ' + repr(error))
                    continue
            if key in attempted:
                cleanup_errors.append('actor release already attempted but unconfirmed: ' + str(key))
                continue
            try:
                raw = close(row, work=False)
                emit('failure_cleanup', raw)
            except BaseException as error: cleanup_errors.append(repr(error))
        if failure is not None or cleanup_errors:
            try: emit('failure', dict(error=repr(failure), cleanup_errors=cleanup_errors, completed_transfers=completed))
            except BaseException as error: cleanup_errors.append('journal: ' + repr(error))
    if failure is not None: raise failure
    if cleanup_errors: raise RuntimeError('Numeric actor release unconfirmed: ' + repr(cleanup_errors))
    return dict(completed_transfers=completed, fresh_groups=groups,
                scope='orchestration observations, not independent numeric G3')
