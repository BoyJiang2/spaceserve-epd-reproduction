"""Exercise real CLI dispatch and locked controller; fake authorized adapters only."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import entry
import preflight_controller as controller
import selected_booking
import selected_execution
import selected_inputs
from preflight_guard import digest
import test_selected_unit


class SelectedRouteTests(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ['EPD_CPU_TEST_TMP']).resolve(strict=True)
        self.temp = tempfile.TemporaryDirectory(prefix='selected-route-cpu-', dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.template = self.root / 'selected-template.json'
        self.template.write_text(json.dumps({'phase': 'selected_g3'}))
        self.inputs_path = self.root / 'inputs.json'
        self.inputs = {'run_id': 'fixture-unit', 'deploy_sha256': 'd' * 64}
        self.inputs_path.write_text(json.dumps(self.inputs))
        fixture = test_selected_unit.SelectedUnitTests()
        fixture.setUp()
        self.spec = fixture.spec
        self.config = {'root': str(self.root), 'uid': getattr(os, 'getuid', lambda: 0)()}
        self.backend = types.SimpleNamespace(close=Mock())
        self.layout = types.SimpleNamespace(run_root=self.root, require_scope=Mock(),
                                            host_lock=self.root / 'host.lock')
        self.claim = types.SimpleNamespace(reserve=Mock(), admit_request=Mock(),
            reservation_receipt={'key': 'selected_g3/replicas', 'claim_sha256': 'c' * 64})
        self.result = {'state': 'released', 'failure': None, 'errors': [], 'formal_admission': 'blocked'}

    def cli(self, *extra):
        argv = ['entry.py', 'selected_g3', '--inputs', str(self.inputs_path),
                '--unit-template', str(self.template), *extra]
        with patch.object(sys, 'argv', argv), patch.object(entry, 'context', return_value=self.layout), \
             patch.object(os, 'chdir') as chdir, patch.dict(os.environ), \
             patch.object(controller, 'run', return_value=self.result) as run:
            code = entry.main()
        return code, run, chdir

    def test_cli_dispatches_selected_system_to_production_controller(self):
        code, run, chdir = self.cli('--system', 'pd')
        self.assertEqual(code, 0)
        self.assertEqual(run.call_args.kwargs, {'selected_system': 'pd'})
        self.assertEqual(run.call_args.args[1], self.inputs)
        self.layout.require_scope.assert_called_once_with('selected_g3')
        chdir.assert_called_once_with(self.root)

    def test_cli_missing_system_stops_before_controller(self):
        with self.assertRaises(SystemExit) as error:
            self.cli()
        self.assertEqual(error.exception.code, 2)

    def test_cli_failed_release_is_failure_exit(self):
        self.result['state'] = 'release_unconfirmed'
        self.assertEqual(self.cli('--system', 'epd')[0], 1)

    @unittest.skipUnless(os.name == 'posix', 'real advisory locking requires POSIX')
    def test_real_locked_route_reserves_once_and_uses_selected_executor(self):
        with patch.object(controller, 'authorize', return_value={'CPU-MOCK': 'authorized'}), \
             patch.object(controller, 'paths_for', return_value=self.layout), \
             patch.object(selected_inputs, 'load_execution', return_value=copy.deepcopy(self.spec)) as load, \
             patch.object(controller, 'booking_for_unit') as booking, \
             patch.object(controller, 'NvmlBackend', return_value=self.backend), \
             patch.object(controller, 'snapshot', return_value={'gpus': {'CPU-MOCK': {'processes': []}}}), \
             patch.object(controller, 'Claim', return_value=self.claim), \
             patch.object(controller, 'child_environment', return_value={}), \
             patch.object(selected_booking, 'for_session', return_value={'CPU-MOCK': 'raw'}) as provider, \
             patch.object(selected_execution, 'execute_sessions', return_value=self.result) as execute:
            result = controller.run(self.config, self.inputs, self.inputs_path, self.template, selected_system='replicas')
            arguments = execute.call_args.args
            self.assertEqual(arguments[-1]('restart', object()), {'CPU-MOCK': 'raw'})
        self.assertIs(result, self.result)
        self.assertEqual(load.call_args.args[4], 'replicas')
        self.assertEqual(booking.call_count, 2)
        self.claim.reserve.assert_called_once()
        self.claim.admit_request.assert_called_once_with(120)
        self.assertIs(arguments[4], self.claim)
        actual = json.loads((self.root / 'runtime/fixture-unit/execution.json').read_bytes())
        self.assertEqual(digest(actual), digest(arguments[3]))
        self.assertEqual(provider.call_args.args[0], 'restart')
        self.backend.close.assert_called_once()

    def test_wrong_system_rejected_before_nvml(self):
        with patch.object(controller, 'authorize', return_value={}), \
             patch.object(controller, 'paths_for', return_value=self.layout), \
             patch.object(controller, 'NvmlBackend') as backend:
            with self.assertRaises(ValueError):
                controller.run(self.config, self.inputs, self.inputs_path, self.template, selected_system=None)
        backend.assert_not_called()


if __name__ == '__main__':
    unittest.main()
