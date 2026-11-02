"""Selected lifecycle tests: real small files, injected executor/NVML, no GPU or HTTP."""
import copy
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import selected_execution as execution
import preflight_controller
from preflight_guard import digest
import test_selected_unit


class SelectedExecutionTests(unittest.TestCase):
    def setUp(self):
        fixture = test_selected_unit.SelectedUnitTests()
        fixture.setUp()
        self.spec = fixture.spec
        parent = Path(os.environ['EPD_CPU_TEST_TMP']).resolve(strict=True)
        self.temp = tempfile.TemporaryDirectory(prefix='selected-cpu-', dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / 'runtime/fixture-unit'
        self.output.mkdir(parents=True)
        self.sidecars = self.root / 'runtime/endpoints'
        self.sidecars.mkdir()
        self.active = self.root / 'runtime/controller-active.json'
        self.inputs = {'run_id': 'fixture-unit'}
        self.config = {'root': str(self.root), 'uid': getattr(os, 'getuid', lambda: 0)(),
                       'cleanup_seconds': 120, 'max_idle_bytes': 0}
        self.deployed = {'boot_id': 'CPU-fixture-boot'}
        self.claim = types.SimpleNamespace(execution_sha256=digest(self.spec),
            reservation_receipt={'claim': 'CPU-fixture-original-claim', 'key': 'selected_g3/replicas'},
            deadline=time.perf_counter() + 1600,
            timing={'deadline_utc_ms': int(time.time() * 1000) + 1600000},
            verify_reservation=lambda: None, check=lambda: None)
        self.claim.reserve = self.claim.admit_request = lambda *args: self.fail('Claim must never be renewed')
        self.global_claim = {'state': 'claimed', 'claim': self.claim.reservation_receipt, 'run_id': 'fixture-unit'}
        self.active.write_text(json.dumps(self.global_claim))
        (self.output / 'execution.json').write_text(json.dumps(self.spec))
        self.calls, self.bookings = [], []
        self.report_failure, self.cleanup_state = None, 'gone'
        self.gpu_processes, self.extra_sidecar = [], False
        self.pid_error, self.pid_present = None, False
        self.actual_stat = os.stat
        self.proc = types.SimpleNamespace(boot=lambda: 'CPU-fixture-boot')
        self.booking_error = None

    def booking(self, name, cancelled):
        self.assertEqual(json.loads(self.active.read_bytes()), self.global_claim)
        self.bookings.append(name)
        if name == 'restart' and self.booking_error:
            raise self.booking_error
        return {'fixture': name}

    def execute(self, config, inputs, deployed, spec, claim, backend, proc, output, active, *, cancelled=None):
        self.assertIs(claim, self.claim)
        self.assertEqual(json.loads(self.active.read_bytes()), self.global_claim)
        self.assertNotEqual(active, self.active)
        self.assertEqual(json.loads((self.output / 'execution.json').read_bytes()), self.spec)
        name = output.name
        self.calls.append(name)
        self.assertEqual(spec['client_argv'][-2:], ['--session', name])
        self.assertEqual(spec['max_requests'], 120)
        self.assertEqual(sum(len(b['requests']) for b in spec['sessions'][name]), 60)
        pid = 990001 if name == 'cold' else 990002
        api = {'pid': pid, 'proc_start_ticks': pid * 10}
        service = {'url': 'http://127.0.0.1:18310', 'api_identity': api, 'worker_keys': []}
        manifest = {'run_id': inputs['run_id'], 'host': 'fixture-host', 'boot_id': deployed['boot_id'],
                    'services': [service]}
        (output / 'endpoints.json').write_text(json.dumps(manifest))
        sidecar = self.sidecars / f"{inputs['run_id']}-{pid}-{pid * 10}.json"
        sidecar.write_text(json.dumps(manifest))
        if self.extra_sidecar:
            (self.sidecars / 'fixture-unit-unknown.json').write_text('{}')
        report = {'state': 'released', 'failure': self.report_failure, 'errors': [],
                  'cleanup': [{'state': self.cleanup_state, 'identity': api}]}
        (output / 'terminal.json').write_text(json.dumps(report))
        active.write_text(json.dumps({'state': 'released'}))
        return report

    def snapshot(self, *args):
        return {'gpus': {'GPU-fixture': {'processes': self.gpu_processes, 'used_bytes': 0}},
                **execution.clock_point()}

    def observed_stat(self, path, *args, **kwargs):
        if str(path).startswith('/proc/99000'):
            if self.pid_error:
                raise self.pid_error
            if not self.pid_present:
                raise FileNotFoundError(str(path))
            return types.SimpleNamespace()
        return self.actual_stat(path, *args, **kwargs)

    def run_unit(self):
        with patch.object(execution, 'execute_claimed', self.execute), \
             patch.object(execution, 'snapshot', self.snapshot), \
             patch.object(execution, 'booking_remaining', return_value=1700), \
             patch.object(os, 'stat', self.observed_stat), \
             patch.object(os, 'O_NOFOLLOW', getattr(os, 'O_NOFOLLOW', 0), create=True):
            return execution.execute_sessions(self.config, self.inputs, self.deployed, self.spec,
                self.claim, object(), self.proc, self.output, self.active, self.booking)

    def test_single_claim_two_sessions_with_actual_archived_sidecars(self):
        result = self.run_unit()
        self.assertEqual(result['state'], 'released')
        self.assertEqual(self.calls, ['cold', 'restart'])
        self.assertEqual(self.bookings, ['cold', 'restart'])
        self.assertEqual(list(self.sidecars.iterdir()), [])
        for name in self.calls:
            folder = self.output / name
            relocated = json.loads((folder / 'endpoint-relocation.json').read_bytes())
            self.assertEqual(len(relocated), 1)
            self.assertTrue(Path(relocated[0]['archive']).is_file())
            release = json.loads((folder / 'release.json').read_bytes())
            session = json.loads((folder / 'session.json').read_bytes())
            self.assertGreaterEqual(release['api_exit_observations'][0]['observed_ms'], session['end_utc_ms'])
            self.assertGreaterEqual(release['observed_ms'], release['api_exit_observations'][0]['observed_ms'])
        self.assertEqual(result['formal_admission'], 'blocked')

    def test_cold_failure_stops_before_restart(self):
        self.report_failure = {'error': 'actual executor failure'}
        result = self.run_unit()
        self.assertEqual(self.calls, ['cold'])
        self.assertEqual(result['state'], 'stopped_no_next_unit')
        self.assertTrue(list(self.sidecars.iterdir()))

    def test_unknown_cleanup_stops_before_restart(self):
        self.cleanup_state = 'identity_unknown_refused'
        self.assertEqual(self.run_unit()['state'], 'stopped_no_next_unit')
        self.assertEqual(self.calls, ['cold'])

    def test_reused_or_live_pid_does_not_count_as_absent(self):
        self.pid_present = True
        self.assertEqual(self.run_unit()['state'], 'stopped_no_next_unit')
        self.assertEqual(self.calls, ['cold'])
        self.assertFalse((self.output / 'cold/release.json').exists())

    def test_permission_error_does_not_count_as_absent(self):
        self.pid_error = PermissionError('CPU fixture cannot observe proc')
        self.assertEqual(self.run_unit()['state'], 'stopped_no_next_unit')
        self.assertEqual(self.calls, ['cold'])
        self.assertFalse((self.output / 'cold/release.json').exists())

    def test_gpu_process_stops_before_endpoint_movement(self):
        self.gpu_processes = [{'pid': 998888}]
        self.assertEqual(self.run_unit()['state'], 'stopped_no_next_unit')
        self.assertEqual(self.calls, ['cold'])
        self.assertTrue(list(self.sidecars.iterdir()))
        self.assertTrue((self.output / 'cold/release.json').exists())

    def test_unknown_same_run_sidecar_is_preserved_and_blocks_restart(self):
        self.extra_sidecar = True
        self.assertEqual(self.run_unit()['state'], 'stopped_no_next_unit')
        self.assertEqual(self.calls, ['cold'])
        self.assertEqual(len(list(self.sidecars.iterdir())), 2)

    def test_expired_restart_booking_never_launches_restart(self):
        self.booking_error = ValueError('actual restart booking is stale')
        self.assertEqual(self.run_unit()['state'], 'stopped_no_next_unit')
        self.assertEqual(self.bookings, ['cold', 'restart'])
        self.assertEqual(self.calls, ['cold'])
        self.assertFalse((self.output / 'restart').exists())

    def test_original_execution_digest_required_before_executor(self):
        self.claim.execution_sha256 = '0' * 64
        with self.assertRaises(ValueError):
            self.run_unit()
        self.assertEqual(self.calls, [])

    def test_global_claim_required_before_executor(self):
        self.active.write_text(json.dumps({'state': 'released'}))
        with self.assertRaises(ValueError):
            self.run_unit()
        self.assertEqual(self.calls, [])

    def test_claim_deadline_is_not_reset_for_restart(self):
        deadline = self.claim.deadline
        timing = copy.deepcopy(self.claim.timing)
        self.run_unit()
        self.assertEqual(self.claim.deadline, deadline)
        self.assertEqual(self.claim.timing, timing)

    def test_cancellation_during_booking_does_not_start_executor(self):
        def cancelled(name, event):
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            return {'fixture': name}
        self.booking = cancelled
        self.assertEqual(self.run_unit()['state'], 'stopped_no_next_unit')
        self.assertEqual(self.calls, [])

    def test_pending_cancel_handoff_reaches_real_executor_before_popen(self):
        self.spec['server_environments'] = [{}] * len(self.spec['servers'])
        self.claim.execution_sha256 = digest(self.spec)
        self.config['gpu_uuids'] = ['GPU-fixture']
        def handoff(*args, **kwargs):
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            return preflight_controller.execute_claimed(*args, **kwargs)
        self.execute = handoff
        with patch.object(preflight_controller.subprocess, 'Popen', side_effect=AssertionError('no process allowed')) as popen, \
             patch.object(preflight_controller, 'cleanup_owned', return_value=[]), \
             patch.object(preflight_controller, 'verify_checkout', return_value={}):
            self.assertEqual(self.run_unit()['state'], 'stopped_no_next_unit')
        self.assertEqual(popen.call_count, 0)

    def test_cancel_after_last_archive_cannot_write_success_terminal(self):
        archive = execution.archive_endpoints
        def cancelled(*args):
            result = archive(*args)
            if args[2].name == 'restart':
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            return result
        with patch.object(execution, 'archive_endpoints', cancelled):
            self.assertEqual(self.run_unit()['state'], 'stopped_no_next_unit')
        self.assertEqual(self.calls, ['cold', 'restart'])


if __name__ == '__main__':
    unittest.main()
