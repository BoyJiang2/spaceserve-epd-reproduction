"""Native worker RPC handler. Internal component; the public entry stays blocked.

Only the authorized controller may load the production factory. No Ray/CUDA
imports, head connection, or actor creation occur at module import time.
"""
import math
import importlib
import importlib.metadata
import os
from pathlib import Path
import re
import sys
import time

from numeric_cache import transfer_vector
from numeric_unit import validate_identity


def remaining(deadline, check):
    check()
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError('Finite driver deadline required')
    value = deadline-time.monotonic()
    if value <= 0: raise TimeoutError('Numeric driver deadline')
    return value


def connect_private_head(parameters, session, namespace, package, authorize, record):
    authorize()
    from numeric_head import node_parameters
    from numeric_cpu_ray import verify_sources, PINNED_SOURCES
    from numeric_cpu_driver import CONTEXT_SHA
    if parameters != node_parameters(parameters['temp_dir'], parameters['gcs_server_port'], gpu_count=3):
        raise ValueError('Exact GPU head parameters required')
    if not isinstance(namespace, str) or not re.fullmatch('[A-Za-z0-9_.:-]{1,160}', namespace):
        raise ValueError('Private numeric namespace required')
    base, session, package = Path(parameters['temp_dir']), Path(session), Path(package)
    if session.parent != base or not session.name.startswith('session_'):
        raise ValueError('Actual selected session must belong to the private head base')
    for path in (base, session):
        if not path.is_absolute() or path.resolve(strict=True) != path or path.is_symlink():
            raise ValueError('Canonical private head paths required')
        if not path.is_dir() or path.stat().st_uid != os.getuid():
            raise ValueError('Private head directory owner differs')
    if any(name == 'ray' or name.startswith('ray.') or name == 'torch' or name.startswith('torch.')
           or name == 'epdserve' or name.startswith('epdserve.') for name in sys.modules):
        raise ValueError('Hardware libraries imported before numeric source checks')
    distribution = importlib.metadata.distribution('ray')
    if distribution.version != '2.10.0' or Path(distribution.locate_file('ray')).absolute() != package:
        raise ValueError('Installed Ray package/version differs')
    sources = verify_sources(package, dict(PINNED_SOURCES, **{'runtime_context.py': CONTEXT_SHA}), os.getuid())
    authorize()
    ray = importlib.import_module('ray')
    if ray.__version__ != '2.10.0' or Path(ray.__file__).absolute() != package/'__init__.py':
        raise ValueError('Imported Ray differs from verified package')
    if importlib.import_module('ray._private.utils').check_dashboard_dependencies_installed() is not False:
        raise ValueError('The verified minimal dashboard branch is required')
    address = '127.0.0.1:'+str(parameters['gcs_server_port'])
    ray.init(address=address, namespace=namespace, log_to_driver=False, _node_ip_address='127.0.0.1')
    worker = importlib.import_module('ray._private.worker')
    def verify_head():
        authorize()
        node = worker._global_node
        if (node is None or node.is_head() is not False or node.all_processes or node.address != address
                or Path(node.get_session_dir_path()) != session
                or ray.get_runtime_context().namespace != namespace):
            raise ValueError('Driver private head/session/namespace or process ownership differs')
    verify_head()
    record('numeric_driver_connected', address=address, session=str(session), namespace=namespace,
           owns_processes=False, sources=sources)
    return ray, verify_head


def load_factory(model, cache, parallel, authorize, *, connection=None):
    authorize()  # The controller supplies actual authorization, not an environment switch.
    if (Path(model.model).name != 'MiniCPM-V-2_6' or model.dtype != 'fp16'
            or model.pd_fused or model.use_dummy_weights or parallel.to_list() != [1, 0, 1, 0, 1, 0]
            or cache.cpu_swap_space != 0 or cache.gpu_memory_utilization != .65
            or type(cache.block_size) is not int or cache.block_size < 1):
        raise ValueError('Frozen no-model native worker configuration required')
    from production_identity import environment
    values = environment()
    if values.get('REPRO_NUMERIC_ONLY') != '1':
        raise ValueError('Explicit authorized native numeric scope required')
    if connection is None:
        raise ValueError('Actual source-pinned private-head connection required')
    ray, verify_head = connection
    verify_head()
    worker = importlib.import_module('epdserve.worker')
    if Path(worker.__file__).resolve() != Path(__file__).parent/'epdserve/worker.py':
        raise ValueError('Imported Worker differs from this deployed source directory')
    from epdserve.utils import EngineStage
    return RayNumericFactory(ray, worker.Worker, EngineStage.DECODING, model, cache, parallel, verify_head)


class RayNumericFactory:
    def __init__(self, ray, worker, stage, model, cache, parallel, verify_head):
        self.ray, self.worker, self.stage = ray, worker, stage
        self.model, self.cache, self.parallel = model, cache, parallel
        self.verify_head = verify_head

    def create(self, intent, deadline, check):
        remaining(deadline, check)
        self.verify_head()
        actor = self.worker.options(name=intent['name'], namespace=intent['namespace'],
                                    lifetime='detached', max_restarts=0, max_task_retries=0).remote(
            worker_id=intent['slot'], stage=self.stage, model_config=self.model,
            cache_config=self.cache, parallel_config=self.parallel)
        submitted = dict(actor_id=actor._actor_id.hex(),
            job_id=self.ray.get_runtime_context().get_job_id(), namespace=intent['namespace'],
            name=intent['name'], detached=True)
        return actor, submitted

    def call(self, actor, operation, argument, deadline, check):
        self.verify_head()
        timeout = remaining(deadline, check)
        result = actor.reproduction_numeric_cache.remote(operation, argument)
        timeout = min(timeout, remaining(deadline, check))
        value = self.ray.get(result, timeout=timeout)
        remaining(deadline, check)
        return value


class NumericDriver:
    def __init__(self, scope, uuids, factory, record):
        self.scope, self.uuids = dict(scope), list(uuids)
        self.vector = transfer_vector(self.uuids)
        self.factory, self.record = factory, record
        self.created, self.failed, self.pending = 0, False, None
        self.actors, self.identities, self.history = {}, {}, []

    def handle(self, action, argument, deadline, check):
        try:
            if self.failed: raise RuntimeError('Driver failed; no business retry')
            remaining(deadline, check)
            if action == 'create_actor':
                return self.create(argument, deadline, check)
            if action != 'call' or set(argument) != {'gpu_uuid', 'operation', 'argument'}:
                raise ValueError('Fixed numeric RPC action required')
            uuid, operation, payload = argument['gpu_uuid'], argument['operation'], argument['argument']
            if self.created % 3 or len(self.actors) != 3 or uuid not in self.actors:
                raise ValueError('Complete current three-worker group required')
            if operation == 'allocate':
                if payload not in ('kv', 've'): raise ValueError('Native cache payload required')
            elif operation in ('prepare', 'copy'):
                transfer = payload if operation == 'prepare' else payload['transfer']
                ordinal = transfer.get('ordinal')
                if type(ordinal) is not int or not 0 <= ordinal < 36 or transfer != self.vector[ordinal]:
                    raise ValueError('Original finite native transfer required')
                if ordinal // 3 != (self.created-1) // 3:
                    raise ValueError('Transfer belongs to another worker lifetime')
                expected = transfer['source_uuid'] if operation == 'prepare' else transfer['target_uuid']
                if uuid != expected: raise ValueError('Actual source/importer UUID differs')
                if operation == 'copy' and payload['source']['identity'] != self.identities[transfer['source_uuid']]:
                    raise ValueError('Original registered exporter identity differs')
            elif operation != 'sync' or payload is not None:
                raise ValueError('Fixed numeric worker operation required')
            return self.factory.call(self.actors[uuid], operation, payload, deadline, check)
        except BaseException as error:
            self.failed = True
            self.record('numeric_driver_failed', error=repr(error), pending=self.pending)
            raise

    def create(self, intent, deadline, check):
        slot, group = self.created % 3, self.created // 3
        expected = dict(namespace=self.scope['run_id'], name='native-g'+str(group)+'-n'+str(slot),
                        group=group, slot=slot, allowed_gpu_uuids=self.uuids, scope=self.scope)
        if (group >= 12 or type(intent.get('group')) is not int or type(intent.get('slot')) is not int
                or intent != expected or self.pending is not None):
            raise ValueError('Exact fresh actor creation intent required')
        self.pending = dict(intent=intent, submitted=None)
        self.record('numeric_driver_creation_started', intent=intent)
        if slot == 0: self.actors, self.identities = {}, {}
        actor, submitted = self.factory.create(intent, deadline, check)
        self.pending['submitted'] = submitted
        self.record('numeric_driver_actor_submitted', intent=intent, submitted=submitted)
        if (set(submitted) != {'actor_id', 'job_id', 'namespace', 'name', 'detached'}
                or not isinstance(submitted['actor_id'], str) or not re.fullmatch('[0-9a-f]{32}', submitted['actor_id'])
                or not isinstance(submitted['job_id'], str) or not re.fullmatch('[0-9a-f]{8}', submitted['job_id'])
                or submitted['namespace'] != intent['namespace'] or submitted['name'] != intent['name']
                or submitted['detached'] is not True):
            raise ValueError('Original named Ray actor submission required')
        identity = self.factory.call(actor, 'identity', None, deadline, check)
        validate_identity(identity, self.scope, self.uuids)
        uuid = identity['gpu_uuid']
        if uuid in self.actors:
            raise ValueError('Duplicate actual GPU UUID in new worker group')
        self.record('numeric_driver_actor_identity', submitted=submitted, identity=identity)
        self.history.append(dict(submitted=submitted, identity=identity))
        self.actors[uuid], self.identities[uuid] = actor, identity
        self.created += 1
        self.pending = None  # Original raw identity is durably recorded before acknowledgment.
        return identity
