"""Private native36 driver process; the supervisor owns admission and all cleanup."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import stat
import struct
import time

from numeric_channel import NumericChannel
from numeric_descendants import HeadProc
from numeric_driver import NumericDriver, connect_private_head, load_factory
from numeric_execution import validate, worker_configs
from numeric_rpc import NumericRPC
from preflight_controller import authorize
from preflight_guard import booking_remaining, digest, load_bound, validate_resources
from project_config import paths_for


def owned_bytes(path, uid, limit=4*1024**2):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError('Canonical owned driver receipt required')
    for parent in (path, *path.parents):
        if parent.is_symlink(): raise ValueError('Linked driver receipt ancestry')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != uid
                or not 0 < before.st_size <= limit):
            raise ValueError('Owned bounded regular driver receipt required')
        raw = stream.read(limit+1)
        after = os.fstat(stream.fileno())
    if (len(raw) != before.st_size or (before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_ino, after.st_size, after.st_mtime_ns)):
        raise ValueError('Driver receipt changed during read')
    return raw


class DriverGrant:
    def __init__(self, spec, sock):
        keys = {'config', 'inputs', 'owner', 'reservation', 'execution', 'parent',
                'parameters', 'session', 'ray_package', 'nonce', 'scope'}
        if set(spec) != keys or not isinstance(spec['nonce'], str) or not re.fullmatch('[0-9a-f]{64}', spec['nonce']):
            raise ValueError('Exact inherited driver envelope required')
        self.spec, self.proc = spec, HeadProc()
        config, inputs = spec['config'], spec['inputs']
        self.deployed = authorize(config, inputs, Path(spec['owner']))
        layout = paths_for(config); layout.require_scope('numeric')
        validate(spec['execution'], layout, config, inputs['source_manifest_sha256'])
        base = layout.ray_tmp/('n-'+digest(inputs['run_id'])[:12])
        if (spec['parameters']['temp_dir'] != str(base)
                or Path(spec['session']).parent != base):
            raise ValueError('Exact run-bound private head base required')
        if sock.family != socket.AF_UNIX or sock.type & socket.SOCK_STREAM != socket.SOCK_STREAM or sock.getblocking():
            raise ValueError('Inherited nonblocking private Unix stream required')
        credentials = struct.unpack('3i', sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        parent = spec['parent']
        if (credentials[:2] != (parent['pid'], config['uid']) or os.getppid() != parent['pid']
                or parent['uid'] != config['uid'] or parent['boot_id'] != self.proc.boot()
                or parent['cwd'] != config['root']
                or parent['environment'] != {'EXP_ROOT': config['root'], 'REPRO_RUN_ID': inputs['run_id']}):
            raise ValueError('Actual inherited peer/parent scope differs')
        self.parent = dict(parent)
        self.claim_raw = owned_bytes(spec['reservation']['claim'], config['uid'])
        if hashlib.sha256(self.claim_raw).hexdigest() != spec['reservation']['claim_sha256']:
            raise ValueError('Original durable claim hash differs')
        self.claim = json.loads(self.claim_raw)
        self.check()

    def check(self):
        spec, config, inputs, claim = self.spec, self.spec['config'], self.spec['inputs'], self.claim
        reservation = spec['reservation']
        runtime = Path(config['root'])/'runtime'
        key = 'numeric/numeric'
        if (set(reservation) != {'ledger', 'claim', 'claim_sha256', 'key'}
                or reservation['key'] != key
                or Path(reservation['claim']) != runtime/'claims'/(digest(key)+'.json')
                or Path(reservation['ledger']) != runtime/'gpu-budget.json'):
            raise ValueError('Claim/ledger path escaped exact native unit')
        if owned_bytes(reservation['claim'], config['uid']) != self.claim_raw:
            raise ValueError('Original durable claim changed')
        ledger = json.loads(owned_bytes(reservation['ledger'], config['uid']))
        unit, timing = claim['unit'], claim['timing']
        if (claim['execution'] != spec['execution'] or claim['execution_sha256'] != digest(spec['execution'])
                or unit['execution_sha256'] != claim['execution_sha256']
                or claim['static_config_sha256'] != digest(config)
                or ledger['static_config_sha256'] != digest(config)
                or ledger['units'].get(key) != unit or unit['timing'] != timing
                or any(unit.get(k) != v for k, v in dict(run_id=inputs['run_id'], phase='numeric',
                    unit='numeric', candidate=None, allocation=[0, 36, 1800],
                    deploy_sha256=inputs['deploy_sha256'], booking_sha256=inputs['booking_sha256']).items())
                or claim['source'] != self.deployed):
            raise ValueError('Actual durable numeric claim/source differs')
        now = time.perf_counter(); utc = int(time.time()*1000)
        start, end = timing['start_monotonic'], timing['deadline_monotonic']
        if (any(type(n) not in (int, float) or not math.isfinite(n) for n in (start, end, now))
                or end-start != 1800 or timing['allocation_seconds'] != 1800
                or type(timing['start_utc_ms']) is not int or type(timing['deadline_utc_ms']) is not int
                or timing['deadline_utc_ms']-timing['start_utc_ms'] != 1800000
                or timing['host'] != config['host'] or timing['boot_id'] != self.proc.boot()
                or self.deployed['boot_id'] != self.proc.boot()
                or abs(utc-(timing['start_utc_ms']+(now-start)*1000)) > 100
                or not start <= now < end-config['cleanup_seconds']
                or utc >= timing['deadline_utc_ms']-config['cleanup_seconds']*1000
                or utc >= config['authorized_end_ms']-config['cleanup_seconds']*1000):
            raise TimeoutError('Original numeric clock/cleanup boundary')
        # Validate freshness at original admission, not against a later RPC's wall time.
        admitted = timing['start_utc_ms']
        validate_resources(claim['resources'], config, inputs['run_id'], self.deployed, admitted)
        if any(gpu['processes'] for gpu in claim['resources']['gpus'].values()):
            raise ValueError('Original numeric admission requires three empty GPUs')
        booking = load_bound(Path(spec['owner']), inputs['booking_file'], inputs['booking_sha256'])
        if booking_remaining(booking, config, admitted) < 1800:
            raise ValueError('Original complete numeric unit plus cleanup did not fit booking')
        actual = self.proc.snapshot(self.parent['pid'], config['uid'])['identity']
        if actual != self.parent or os.getppid() != self.parent['pid']:
            raise ValueError('Original supervisor identity changed or disappeared')
        scope = dict(host=config['host'], uid=config['uid'], root=config['root'], run_id=inputs['run_id'],
            boot_id=self.deployed['boot_id'], source_commit=self.deployed['commit'],
            deploy_sha256=inputs['deploy_sha256'],
            candidate_config_sha256=spec['execution']['candidate_config_sha256'], engine_stage='DECODING')
        if spec['scope'] != scope: raise ValueError('Worker scope differs from actual claim')
        from production_identity import environment
        values = environment()
        expected = dict(EXP_ROOT=config['root'], REPRO_RUN_ID=inputs['run_id'],
            REPRO_SOURCE_COMMIT=scope['source_commit'], REPRO_DEPLOY_SHA256=scope['deploy_sha256'],
            REPRO_PROFILE_SHA256=scope['candidate_config_sha256'], REPRO_NUMERIC_ONLY='1',
            REPRO_REQUEST_IDENTITY='0', REPRO_IDENTITY='1',
            REPRO_ENDPOINT='gcs://127.0.0.1:'+str(spec['parameters']['gcs_server_port']))
        if (any(values.get(k) != v for k, v in expected.items())
                or json.loads(values['REPRO_GPU_UUIDS']) != config['gpu_uuids']
                or os.environ.get('CUDA_VISIBLE_DEVICES') != ','.join(config['gpu_uuids'])):
            raise ValueError('Actual driver identity/visibility differs')


def serve(spec, sock, record):
    grant = DriverGrant(spec, sock)
    grant.check()
    connection = connect_private_head(spec['parameters'], spec['session'], spec['inputs']['run_id'],
                                      spec['ray_package'], grant.check, record)
    settings = worker_configs(spec['execution']['profile'], grant.check)
    factory = load_factory(*settings, grant.check, connection=connection)
    driver = NumericDriver(spec['scope'], spec['config']['gpu_uuids'], factory, record)
    rpc = NumericRPC(NumericChannel(sock), spec['inputs']['run_id'], spec['nonce'], 'driver', record)
    deadline = grant.claim['timing']['deadline_monotonic']-spec['config']['cleanup_seconds']
    record('numeric_driver_ready', parent=spec['parent'], scope=spec['scope'])
    # EOF/failure terminates this client only. Detached actors/head stay parent-owned.
    while True:
        grant.check()
        rpc.serve_once(driver.handle, deadline, grant.check)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--spec-sha256', required=True)
    parser.add_argument('--fd', type=int, required=True)
    parser.add_argument('--session-dir', type=Path, required=True)
    args = parser.parse_args()
    raw = owned_bytes(args.spec, os.getuid())
    if hashlib.sha256(raw).hexdigest() != args.spec_sha256:
        raise ValueError('Parent-pinned driver envelope differs')
    spec = json.loads(raw)
    if str(args.session_dir) != spec['session']:
        raise ValueError('Driver selected private session differs')
    folder = Path(spec['config']['root'])/'runtime'/spec['inputs']['run_id']
    if args.spec != folder/'driver-spec.json': raise ValueError('Exact private driver spec path required')
    journal = folder/'driver-events.jsonl'
    fd = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w', encoding='utf8') as output:
        def record(event, **data):
            output.write(json.dumps(dict(event=event, monotonic_s=time.monotonic(), **data))+'\n')
            output.flush(); os.fsync(output.fileno())
        with socket.socket(fileno=args.fd) as sock:
            try: serve(spec, sock, record)
            except BaseException as error:
                record('numeric_driver_terminal_error', error=repr(error), cleanup_authorized=False)
                raise


if __name__ == '__main__': main()
