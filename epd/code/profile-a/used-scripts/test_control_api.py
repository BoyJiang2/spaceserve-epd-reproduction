"""Register the actual FastAPI control route without loading a model or CUDA."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from starlette.requests import Request

os.environ.pop('REPRO_OBSERVE', None)
path = Path(__file__).resolve().parents[1] / 'scripts/observe.py'
spec = importlib.util.spec_from_file_location('observe', path)
observe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observe)
app = FastAPI()
observe.install_api(app)
route = next(route for route in app.routes if route.path == '/repro/observe')
assert not route.dependant.query_params, 'Request annotation must resolve to injected Request'


async def invoke(operation):
    body = json.dumps({'operation': operation}).encode()
    async def receive():
        return {'type': 'http.request', 'body': body, 'more_body': False}
    request = Request({'type': 'http', 'method': 'POST', 'path': '/repro/observe', 'headers': []}, receive)
    return await route.endpoint(request)


state = asyncio.run(invoke('status'))
assert state == {'pid': os.getpid(), 'enabled': False, 'capturing': False}
try:
    asyncio.run(invoke('start'))
except HTTPException as error:
    assert error.status_code == 400
else:
    raise AssertionError('disabled capture accepted start')
print('Real FastAPI route registration, Request injection, status, disabled capture rejection: PASS; no model/CUDA execution')
