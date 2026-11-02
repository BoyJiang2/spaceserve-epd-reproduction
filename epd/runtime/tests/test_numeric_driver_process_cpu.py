"""CPU-MOCK production driver boundary tests. No actual Ray, NVML, CUDA or grants."""
import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numeric_driver_process as child
import numeric_execution as envelope
from preflight_guard import digest


class DriverProcessTests(unittest.TestCase):
    def setUp(self):
        if not hasattr(socket, 'SO_PEERCRED'): self.skipTest('Linux inherited Unix credentials required')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        runtime = self.root/'runtime'; (runtime/'claims').mkdir(parents=True)
        self.ledger = runtime/'gpu-budget.json'
        self.claim_path = runtime/'claims'/(digest('numeric/numeric')+'.json')
        self.parent = dict(pid=os.getpid(), uid=os.getuid(), boot_id='CPU-MOCK-boot',
            cwd=str(self.root), environment={'EXP_ROOT':str(self.root), 'REPRO_RUN_ID':'CPU-MOCK-run'},
            proc_start_ticks=100, ppid=1, exe='/CPU-MOCK-python', argv=['CPU-MOCK'])
        self.config = dict(root=str(self.root), uid=os.getuid(), host='CPU-MOCK',
            gpu_uuids=['A','B','C'], cleanup_seconds=120, authorized_end_ms=2000000,
            authorized_start_ms=0, numa_by_uuid=dict(A=0,B=0,C=0), max_idle_bytes=1024,
            resource_id='h20/CPU-MOCK', booking_user='CPU-MOCK',
            booking_windows=[dict(id='CPU-MOCK-booking', start_ms=0, end_ms=2000000)])
        self.booking = dict(observed_ms=0, origin='gputime_read_only_api', read_only=True,
            resources=[dict(id='h20/CPU-MOCK', active=True)], bookings=[dict(
                id='CPU-MOCK-booking', resource_id='h20/CPU-MOCK', node='CPU-MOCK',
                user='CPU-MOCK', kind='gpu', start_ms=0, end_ms=2000000)])
        booking_raw = json.dumps(self.booking).encode()
        (self.root/'booking.json').write_bytes(booking_raw)
        self.inputs = dict(run_id='CPU-MOCK-run', source_manifest_sha256='a'*64,
            deploy_sha256='b'*64, booking_file='booking.json',
            booking_sha256=hashlib.sha256(booking_raw).hexdigest())
        self.execution = envelope.execution('/CPU-MOCK/MiniCPM-V-2_6', ['A','B','C'], 'a'*64)
        self.deployed = dict(boot_id='CPU-MOCK-boot', commit='d'*40)
        timing = dict(start_monotonic=0, deadline_monotonic=1800, start_utc_ms=0,
            deadline_utc_ms=1800000, allocation_seconds=1800, host='CPU-MOCK', boot_id='CPU-MOCK-boot')
        unit = dict(run_id=self.inputs['run_id'], phase='numeric', unit='numeric', candidate=None,
            allocation=[0,36,1800], timing=timing, deploy_sha256='b'*64,
            booking_sha256=self.inputs['booking_sha256'],
            execution_sha256=digest(self.execution))
        resources = dict(host='CPU-MOCK', uid=os.getuid(), root=str(self.root), boot_id='CPU-MOCK-boot',
            run_id=self.inputs['run_id'], observed_ms=0, gpus={u:dict(numa=0, unit='bytes', name='CPU-MOCK H20',
            capacity_bytes=100000, used_bytes=0, processes=[]) for u in ['A','B','C']})
        self.claim = dict(execution=self.execution, execution_sha256=digest(self.execution), resources=resources,
            static_config_sha256=digest(self.config), unit=unit, timing=timing, source=self.deployed)
        self.scope = dict(host='CPU-MOCK', uid=os.getuid(), root=str(self.root), run_id=self.inputs['run_id'],
            boot_id='CPU-MOCK-boot', source_commit='d'*40, deploy_sha256='b'*64,
            candidate_config_sha256=self.execution['candidate_config_sha256'], engine_stage='DECODING')
        self.layout = SimpleNamespace(require_scope=Mock(), ray_tmp=self.root/'ray')
        base = self.layout.ray_tmp/('n-'+digest(self.inputs['run_id'])[:12])
        self.spec = dict(config=self.config, inputs=self.inputs, owner=str(self.root/'inputs.json'),
            execution=self.execution, parent=self.parent, scope=self.scope,
            reservation=dict(ledger=str(self.ledger), claim=str(self.claim_path), key='numeric/numeric', claim_sha256=''),
            parameters=dict(temp_dir=str(base), gcs_server_port=27180), session=str(base/'session_CPU-MOCK'),
            ray_package='/CPU-MOCK/ray', nonce='e'*64)
        self.save_claim()
        self.sock, self.peer = socket.socketpair(); self.sock.setblocking(False)
        self.addCleanup(self.sock.close); self.addCleanup(self.peer.close)
        self.proc = Mock(boot=Mock(return_value='CPU-MOCK-boot'),
            snapshot=Mock(side_effect=lambda *args: {'identity':copy.deepcopy(self.parent)}))
        self.env = dict(EXP_ROOT=str(self.root), REPRO_RUN_ID=self.inputs['run_id'],
            REPRO_SOURCE_COMMIT='d'*40, REPRO_DEPLOY_SHA256='b'*64,
            REPRO_PROFILE_SHA256=self.scope['candidate_config_sha256'], REPRO_NUMERIC_ONLY='1',
            REPRO_REQUEST_IDENTITY='0', REPRO_IDENTITY='1', REPRO_ENDPOINT='gcs://127.0.0.1:27180',
            REPRO_GPU_UUIDS='["A","B","C"]')
        for target, value in [('numeric_driver_process.authorize', Mock(return_value=self.deployed)),
            ('numeric_driver_process.paths_for', Mock(return_value=self.layout)),
            ('numeric_driver_process.validate', Mock()), ('numeric_driver_process.HeadProc', Mock(return_value=self.proc)),
            ('numeric_driver_process.os.getppid', Mock(return_value=os.getpid())),
            ('numeric_driver_process.time.perf_counter', Mock(return_value=1)),
            ('numeric_driver_process.time.time', Mock(return_value=1)),
            ('production_identity.environment', Mock(return_value=self.env))]:
            active = patch(target, value); active.start(); self.addCleanup(active.stop)
        active = patch.dict(os.environ, CUDA_VISIBLE_DEVICES='A,B,C'); active.start(); self.addCleanup(active.stop)

    def save_claim(self):
        raw = json.dumps(self.claim).encode()
        self.claim_path.write_bytes(raw)
        self.ledger.write_text(json.dumps(dict(static_config_sha256=digest(self.config),
            units={'numeric/numeric':self.claim['unit']})), encoding='utf8')
        if hasattr(self, 'spec'):
            self.spec['reservation']['claim_sha256'] = hashlib.sha256(raw).hexdigest()

    def grant(self): return child.DriverGrant(self.spec, self.sock)

    def test_consumes_original_claim_and_rechecks_parent_and_ledger(self):
        grant = self.grant(); grant.check()
        self.proc.snapshot.return_value = {'identity':{}}
        self.proc.snapshot.side_effect = None
        with self.assertRaises(ValueError): grant.check()

    def test_authorization_fails_before_private_head_or_configs(self):
        with patch.object(child, 'authorize', side_effect=ValueError('CPU-MOCK unauthorized')), \
                patch.object(child, 'connect_private_head') as connect, patch.object(child, 'worker_configs') as config:
            with self.assertRaises(ValueError): child.serve(self.spec, self.sock, Mock())
            connect.assert_not_called(); config.assert_not_called()

    def test_ledger_missing_unit_not_accepted(self):
        self.ledger.write_text(json.dumps(dict(static_config_sha256=digest(self.config), units={})), encoding='utf8')
        with self.assertRaises(ValueError): self.grant()

    def test_altered_claim_or_wrong_unit_or_shortened_budget_rejected(self):
        for mutate in [lambda: self.claim['unit'].update(allocation=[0,3,1800]),
                       lambda: self.claim['timing'].update(deadline_monotonic=1801),
                       lambda: self.claim['unit'].update(candidate='CPU-MOCK-wrong')]:
            original = copy.deepcopy(self.claim); mutate(); self.save_claim()
            with self.assertRaises((ValueError, TimeoutError)): self.grant()
            self.claim = original; self.save_claim()
        grant = self.grant(); self.claim_path.write_bytes(b'{}')
        with self.assertRaises(ValueError): grant.check()

    def test_foreign_socket_or_scope_or_visibility_rejected(self):
        for key, value in [('scope', {**self.scope,'deploy_sha256':'f'*64}),
                           ('parent', {**self.parent,'pid':os.getpid()+100000}),
                           ('session', '/CPU-MOCK/wrong/session')]:
            original = self.spec[key]; self.spec[key] = value
            with self.assertRaises(ValueError): self.grant()
            self.spec[key] = original
        with patch.dict(os.environ, CUDA_VISIBLE_DEVICES='C,B,A'):
            with self.assertRaises(ValueError): self.grant()

    def test_cleanup_interval_stops_business(self):
        with patch.object(child.time, 'perf_counter', return_value=1680), \
                patch.object(child.time, 'time', return_value=1680):
            with self.assertRaises(TimeoutError): self.grant()

    def test_missing_or_wrong_resource_scope_refused(self):
        original = copy.deepcopy(self.claim)
        mutations = [lambda: self.claim.pop('resources'),
            lambda: self.claim['resources'].update(boot_id='CPU-MOCK-old-boot'),
            lambda: self.claim['resources']['gpus'].pop('C'),
            lambda: self.claim['resources']['gpus']['A'].update(numa=1),
            lambda: self.claim['resources'].update(observed_ms=-300001),
            lambda: self.claim['resources']['gpus']['A'].update(processes=[{'pid':123}])]
        for mutate in mutations:
            mutate(); self.save_claim()
            with self.assertRaises((KeyError,ValueError)): self.grant()
            self.claim = copy.deepcopy(original); self.save_claim()

    def test_original_booking_bytes_freshness_and_coverage_refused(self):
        path = self.root/'booking.json'
        original = copy.deepcopy(self.booking)
        for mutate in [lambda: self.booking.update(observed_ms=-300001),
                       lambda: self.booking['bookings'][0].update(user='CPU-MOCK-foreign'),
                       lambda: self.booking['bookings'][0].update(end_ms=1800000)]:
            mutate(); raw = json.dumps(self.booking).encode(); path.write_bytes(raw)
            self.inputs['booking_sha256'] = hashlib.sha256(raw).hexdigest()
            self.claim['unit']['booking_sha256'] = self.inputs['booking_sha256']; self.save_claim()
            with self.assertRaises(ValueError): self.grant()
            self.booking = copy.deepcopy(original)
        raw = json.dumps(original).encode(); path.write_bytes(raw)
        self.inputs['booking_sha256'] = hashlib.sha256(raw).hexdigest()
        self.claim['unit']['booking_sha256'] = self.inputs['booking_sha256']; self.save_claim()
        grant = self.grant(); path.write_bytes(b'{}')
        with self.assertRaises(ValueError): grant.check()

    def test_original_admission_remains_valid_after_five_minutes_inside_same_unit(self):
        with patch.object(child.time,'perf_counter',return_value=601), patch.object(child.time,'time',return_value=601):
            self.grant().check()

    def test_matching_original_booking_too_short_after_cleanup_refused(self):
        self.booking['bookings'][0]['end_ms'] = 1800000
        self.config['booking_windows'][0]['end_ms'] = 1800000
        self.config['authorized_end_ms'] = 1800000
        raw = json.dumps(self.booking).encode(); (self.root/'booking.json').write_bytes(raw)
        self.inputs['booking_sha256'] = hashlib.sha256(raw).hexdigest()
        self.claim['unit']['booking_sha256'] = self.inputs['booking_sha256']
        self.claim['static_config_sha256'] = digest(self.config); self.save_claim()
        with self.assertRaisesRegex(ValueError, 'complete numeric unit plus cleanup'):
            self.grant()

    def test_source_boot_and_utc_allocation_must_match_actual_boot_and_unit(self):
        self.claim['timing']['deadline_utc_ms'] += 1000; self.save_claim()
        with self.assertRaises(TimeoutError): self.grant()
        self.claim['timing']['deadline_utc_ms'] -= 1000
        self.deployed['boot_id'] = 'CPU-MOCK-old-source-boot'; self.save_claim()
        with self.assertRaises(TimeoutError): self.grant()

    def test_actual_route_order_and_rpc_failure_no_shutdown_or_retry(self):
        order = []; factory = Mock(); configs = (Mock(), Mock(), Mock())
        grant = Mock(claim={'timing':{'deadline_monotonic':1800}})
        def connected(*args): order.append('connect'); return ('CPU-MOCK-ray', Mock())
        def configured(*args): order.append('configs'); return configs
        def loaded(*args, **kw): order.append('factory'); self.assertEqual(args[:3], configs); return factory
        rpc = Mock(); rpc.serve_once.side_effect = EOFError('CPU-MOCK peer closed')
        with patch.object(child, 'DriverGrant', return_value=grant), \
                patch.object(child, 'connect_private_head', side_effect=connected), \
                patch.object(child, 'worker_configs', side_effect=configured), \
                patch.object(child, 'load_factory', side_effect=loaded), \
                patch.object(child, 'NumericDriver') as driver, patch.object(child, 'NumericRPC', return_value=rpc):
            with self.assertRaises(EOFError): child.serve(self.spec, self.sock, Mock())
            self.assertEqual(order, ['connect','configs','factory'])
            self.assertEqual(rpc.serve_once.call_count, 1)
            self.assertIs(rpc.serve_once.call_args.args[0], driver.return_value.handle)


class ExecutionTests(unittest.TestCase):
    def test_exact_profile_full_vector_and_type_sensitive_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            model = Path(temp)/'MiniCPM-V-2_6'; model.mkdir()
            layout = SimpleNamespace(asset=lambda name: model)
            spec = envelope.execution(model, ['A','B','C'], 'a'*64)
            self.assertEqual(len(envelope.validate(spec, layout, {'gpu_uuids':['A','B','C']}, 'a'*64)['transfers']),36)
            for key, value in [('max_requests',False), ('max_transfers',3), ('wall_seconds',1799), ('candidate','x')]:
                bad = copy.deepcopy(spec); bad[key] = value
                with self.assertRaises(ValueError): envelope.validate(bad, layout, {'gpu_uuids':['A','B','C']}, 'a'*64)


if __name__ == '__main__': unittest.main()
