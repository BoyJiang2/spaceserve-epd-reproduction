"""CPU-MOCK controller-to-real numeric_unit route, with simulated hardware only."""
import os
from pathlib import Path
import signal
import tempfile
import threading
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import numeric_controller as controller
import numeric_unit
from test_numeric_unit_cpu import BackendFixture, ClaimFixture, PROFILE


class ControllerRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.clock=NS(value=100.); self.events=[]
        self.claim=ClaimFixture(self.clock,self.events)
        self.claim.config['root']=self.temp.name
        self.claim.reservation_receipt={'CPU-MOCK-only':'not a real admission receipt'}
        self.backend=BackendFixture(self.claim,self.clock,self.events)
        self.c=object.__new__(controller.NativeController)
        self.c.claim=self.claim; self.c.config=self.claim.config; self.c.inputs=self.claim.inputs
        self.c.root=Path(self.temp.name); self.c.output=self.c.root; self.c.run_id=self.claim.inputs['run_id']
        self.c.layout=NS(asset=lambda name:self.c.root/'CPU-MOCK-assets'/name)
        self.c.spec={'candidate_config_sha256':PROFILE}; self.c.parameters={'gcs_server_port':27180}
        self.c.start=Mock(); self.c.backend=self.backend; self.c.record=Mock(); self.c.poll=Mock()
        self.c.source_snapshot=Mock()
        self.c.cleanup=Mock(return_value={'CPU-MOCK-idle':True})
        self.c.cancelled=threading.Event();self.c.stop=threading.Event()
        self.c.sampler=None;self.c.reader=None;self.c.logs=[];self.c.errors=[];self.c.sample_errors=[]

    def run_route(self):
        def actual_unit(claim,backend,emit,profile):
            return numeric_unit.execute(claim,backend,emit,profile,clock=lambda:self.clock.value)
        with patch.object(controller,'execute',side_effect=actual_unit):return self.c.run()

    def test_controller_runs_complete_original_unit_and_persists_raw_terminal(self):
        report=self.run_route()
        self.assertEqual(report['result']['completed_transfers'],36)
        self.assertEqual(report['result']['fresh_groups'],12)
        self.assertEqual(self.backend.copies,list(range(36)))
        self.assertEqual(self.claim.issued_transfers,36)
        self.assertEqual(report['state'],'released');self.assertIsNone(report['failure'])
        self.assertEqual(report['formal_admission'],'blocked')
        self.assertEqual(report['evidence_state'],'raw_not_independently_reviewed')
        self.assertEqual([c.args[0] for c in self.c.source_snapshot.call_args_list],['before','after'])
        self.c.cleanup.assert_called_once();self.assertTrue((self.c.output/'terminal.json').is_file())

    def test_transfer_failure_is_preserved_and_does_not_retry_business(self):
        self.backend.fail_copy=1
        report=self.run_route()
        self.assertEqual(self.backend.copies,[0,1]);self.assertEqual(self.claim.issued_transfers,2)
        self.assertIsNotNone(report['failure']);self.assertIsNone(report['result'])
        self.c.cleanup.assert_called_once()

    def test_unconfirmed_cleanup_stays_failed_and_restores_signals_and_environment(self):
        self.c.start.side_effect=RuntimeError('CPU-MOCK startup failure')
        self.c.cleanup.side_effect=RuntimeError('CPU-MOCK importer retained')
        before={n:signal.getsignal(n) for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
        with patch.dict(os.environ,EXP_ROOT='CPU-MOCK-original'):
            report=self.run_route()
            self.assertEqual(os.environ['EXP_ROOT'],'CPU-MOCK-original')
        self.assertEqual(before,{n:signal.getsignal(n) for n in before})
        self.assertEqual(report['state'],'release_unconfirmed')
        self.assertIn('importer retained',report['errors'][0])


if __name__=='__main__':unittest.main()
