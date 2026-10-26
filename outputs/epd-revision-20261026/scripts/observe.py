"""Bounded opt-in host events and CUDA stream windows; no in-window disk writes."""
import contextlib
import contextvars
import functools
import inspect
import itertools
import json
import os
from pathlib import Path
import time

enabled = os.environ.get('REPRO_OBSERVE') == '1'
LIMIT = 200000
records = []
gpu_windows = []
overflow = False
sequence = itertools.count()
step_counts = {}
request_context = contextvars.ContextVar('request_ids', default=())
STEPS = {'step_encoding', 'step_llm', 'migrate_blocks_encoding', 'migrate_blocks_context', 'baseline.execute_model'}


def mark(name, **fields):
    global overflow
    if not enabled:
        return
    if len(records) >= LIMIT:
        overflow = True
        return
    records.append({'name': name, 'pid': os.getpid(), 'host_ns': time.perf_counter_ns(), **fields})


def details(args, name, kwargs):
    value = args[1] if len(args) > 1 else kwargs.get('execute_model_req')
    if isinstance(value, (list, tuple)):
        return {('blocks' if 'migrate_blocks' in name else 'request_ids'): list(map(str, value))}
    if hasattr(value, 'req'):
        return {'request_ids': [str(value.req.request_id)]}
    metadata = getattr(value, 'seq_group_metadata_list', None)
    if metadata is not None:
        return {'request_ids': [str(row.request_id) for row in metadata], 'prompt': [bool(row.is_prompt) for row in metadata]}
    return {'operation': value} if isinstance(value, str) else {}


@contextlib.contextmanager
def span(name, **fields):
    if not enabled:
        yield
        return
    operation = fields.pop('op_id', f'{os.getpid()}:{next(sequence)}')
    mark(name + '.begin', op_id=operation, **fields)
    try:
        yield
    finally:
        mark(name + '.end', op_id=operation, **fields)


def worker_metadata(name, args):
    ids = list(request_context.get()) if 'migrate_blocks' in name else list(map(str, args[0]))
    return {'op_id': f'{os.getpid()}:{next(sequence)}', 'request_ids': ids, 'operation': name}


def call(name):
    def decorate(function):
        if not enabled:
            return function
        if inspect.iscoroutinefunction(function):
            @functools.wraps(function)
            async def asynchronous(*args, **kwargs):
                fields = details(args, name, kwargs)
                token = request_context.set(tuple(fields.get('request_ids', request_context.get())))
                try:
                    with span(name, **fields):
                        return await function(*args, **kwargs)
                finally:
                    request_context.reset(token)
            return asynchronous

        @functools.wraps(function)
        def synchronous(*args, **kwargs):
            fields = details(args, name, kwargs)
            meta = kwargs.pop('repro_meta', None)
            if meta:
                fields.update(meta)
            fields['stage'] = str(getattr(args[0], 'stage', 'baseline')) if args else ''
            fields['component'] = type(args[0]).__name__ if args else ''
            fields.setdefault('op_id', f'{os.getpid()}:{next(sequence)}')
            if name in ('step_llm', 'step_encoding', 'baseline.execute_model'):
                steps = []
                for request_id in fields.get('request_ids', []):
                    key = (fields['stage'], request_id)
                    step_counts[key] = step_counts.get(key, 0) + 1
                    steps.append(step_counts[key])
                fields['request_step_ordinals'] = steps
            timed = name in STEPS and not overflow
            if timed:
                import torch
                stream = torch.cuda.current_stream()
                begin, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
                fields['stream'] = int(stream.cuda_stream)
                fields['logical_device'] = int(torch.cuda.current_device())
                begin.record(stream)
            with span(name, **fields):
                result = function(*args, **kwargs)
            if timed:
                end.record(stream)
                gpu_windows.append((begin, end, name, dict(fields)))
            return result
        return synchronous
    return decorate


def reset():
    global overflow
    records.clear()
    gpu_windows.clear()
    step_counts.clear()
    overflow = False
    return {'pid': os.getpid(), 'reset': True}


def export():
    if not enabled:
        raise RuntimeError('lite observation disabled')
    windows = []
    for begin, end, name, fields in gpu_windows:
        # Only called after the timed measurement and completed requests.
        end.synchronize()
        windows.append({'name': name, **fields, 'stream_elapsed_ms': begin.elapsed_time(end)})
    root = Path(os.environ['EXP_ROOT']).resolve()
    destination = Path(os.environ['REPRO_LITE_OUTPUT']).resolve()
    if root != Path('/var/tmp/boyjiang-epd-revision-20261026') or not destination.is_relative_to(root / 'results'):
        raise RuntimeError('unexpected lite export destination')
    destination.mkdir(parents=True, exist_ok=True)
    result = {'pid': os.getpid(), 'overflow': overflow, 'events': records, 'gpu_stream_windows': windows,
              'run_id': os.environ['REPRO_RUN_ID'], 'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'),
              'clock': 'same-host perf_counter_ns; CUDA values are relative same-stream windows, not global timestamps/kernel busy time'}
    path = destination / f'process-{os.getpid()}.json'
    with path.open('x') as output:
        json.dump(result, output)
    return {'pid': os.getpid(), 'path': str(path), 'events': len(records), 'gpu_windows': len(windows), 'overflow': overflow}


def model_runtime(worker):
    import torch
    counts, devices, dtypes = {}, {}, {}
    for name, value in worker.model_runner.model.named_parameters():
        component = name.split('.')[0]
        counts[component] = counts.get(component, 0) + value.numel()
        devices[str(value.device)] = devices.get(str(value.device), 0) + value.numel()
        dtypes[str(value.dtype)] = dtypes.get(str(value.dtype), 0) + value.numel()
    config = getattr(worker, 'vllm_model_config', getattr(worker, 'model_config', None))
    return {'pid': os.getpid(), 'stage': str(getattr(worker, 'stage', 'baseline')),
            'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'),
            'parameters_by_component': counts, 'parameters_by_device': devices, 'parameters_by_dtype': dtypes,
            'max_model_len': getattr(config, 'max_model_len', None),
            'current_device': torch.cuda.current_device(), 'device_name': torch.cuda.get_device_name()}


def install_api(app, engine_provider):
    from fastapi import HTTPException, Request

    @app.post('/repro/observe')
    async def control(request: Request):
        operation = (await request.json())['operation']
        if operation == 'status':
            return {'pid': os.getpid(), 'enabled': enabled, 'capturing': enabled, 'overflow': overflow}
        if operation not in ('reset', 'export', 'runtime') or (operation != 'runtime' and not enabled):
            raise HTTPException(400, 'invalid lite operation')
        engine = engine_provider()
        results = []
        if hasattr(engine, 'orchestrator'):
            import ray
            pending = []
            for name in ('encoding_cluster', 'context_cluster', 'decoding_cluster'):
                for instance in getattr(engine.orchestrator, name).engines:
                    for group in instance.workers:
                        pending.extend(worker.repro_lite.remote(operation) for worker in group)
            results.extend(ray.get(pending, timeout=60))
        if operation == 'runtime':
            if not hasattr(engine, 'orchestrator'):
                results.append(model_runtime(engine.engine.model_executor.driver_worker))
        else:
            results.append(reset() if operation == 'reset' else export())
        if any(row.get('overflow') for row in results):
            raise HTTPException(500, 'lite event buffer overflow')
        return {'pid': os.getpid(), 'operation': operation, 'results': results}
