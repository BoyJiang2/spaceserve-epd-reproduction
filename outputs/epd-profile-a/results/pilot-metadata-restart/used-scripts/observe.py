"""Opt-in NVTX annotations; never synchronize CUDA or change inference results."""
import contextlib
import functools
import inspect
import json
import os
import time

enabled = os.environ.get('REPRO_OBSERVE') == '1'
capture_id = None
if enabled:
    from torch.cuda import nvtx


def details(args, name, kwargs=None):
    if len(args) < 2 and not kwargs:
        return {}
    value = args[1] if len(args) > 1 else kwargs.get('execute_model_req')
    if isinstance(value, (list, tuple)):
        kind = 'blocks' if 'migrate_blocks' in name else 'request_ids'
        return {kind: list(map(str, value)), 'batch': len(value)}
    if hasattr(value, 'req'):
        return {'request_id': str(value.req.request_id)}
    metadata = getattr(value, 'seq_group_metadata_list', None)
    if metadata is not None:
        return {'ids': [str(item.request_id) for item in metadata],
                'prompt': [bool(item.is_prompt) for item in metadata], 'batch': len(metadata)}
    return {'operation': value} if isinstance(value, str) else {}


@contextlib.contextmanager
def span(name, **fields):
    if not enabled:
        yield
        return
    label = json.dumps({'name': name, 'pid': os.getpid(), 'perf_ns': time.perf_counter_ns(), **fields}, separators=(',', ':'))
    token = nvtx.range_start(label)
    try:
        yield
    finally:
        nvtx.range_end(token)


def mark(name, **fields):
    if enabled:
        nvtx.mark(json.dumps({'name': name, 'pid': os.getpid(), 'perf_ns': time.perf_counter_ns(), **fields}, separators=(',', ':')))


def call(name):
    def decorate(function):
        if not enabled:
            return function
        if inspect.iscoroutinefunction(function):
            @functools.wraps(function)
            async def wrapped(*args, **kwargs):
                with span(name, component=type(args[0]).__name__, **details(args, name, kwargs)):
                    return await function(*args, **kwargs)
        else:
            @functools.wraps(function)
            def wrapped(*args, **kwargs):
                fields = details(args, name, kwargs)
                fields['stage'] = str(getattr(args[0], 'stage', 'baseline')) if args else ''
                with span(name, component=type(args[0]).__name__, **fields):
                    return function(*args, **kwargs)
        return wrapped
    return decorate


def install_api(app):
    from fastapi import HTTPException, Request

    @app.post('/repro/observe')
    async def control(request: Request):
        global capture_id
        operation = (await request.json())['operation']
        if operation == 'status':
            return {'pid': os.getpid(), 'enabled': enabled, 'capturing': capture_id is not None}
        if not enabled:
            raise HTTPException(400, 'observation disabled')
        if operation == 'start' and capture_id is None:
            capture_id = nvtx.range_start('repro_capture')
            mark('capture.anchor')
        elif operation == 'stop' and capture_id is not None:
            nvtx.range_end(capture_id)
            capture_id = None
        else:
            raise HTTPException(400, 'invalid capture transition')
        return {'pid': os.getpid(), 'enabled': enabled, 'capturing': capture_id is not None}
