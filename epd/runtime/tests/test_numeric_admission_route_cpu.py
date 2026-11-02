"""CPU-MOCK admission-to-controller route. No actual Claim or GPU proof is issued."""
import contextlib
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import numeric_controller as controller


class AdmissionRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.trace=[]
        self.config=dict(root=str(self.root),uid=os.getuid(),gpu_uuids=['A','B','C'])
        self.inputs={'run_id':'CPU-MOCK-unit'}
        self.spec={'schema':'epd-fixed-unit-v1','phase':'numeric','unit':'numeric',
                   'candidate':None,'max_requests':0,'max_transfers':36,'wall_seconds':1800}
        self.layout=NS(host_lock=self.root/'host.lock',require_scope=Mock(side_effect=lambda *a:self.trace.append('scope')))
        self.fresh={'gpus':{u:{'processes':[]} for u in ['A','B','C']}}
        self.claim=NS(reservation_receipt={'CPU-MOCK-only':'never a usable claim'})
        self.claim.reserve=Mock(side_effect=lambda *a:self.trace.append('reserve'))
        self.report={'state':'released','failure':None,'errors':[],'CPU-MOCK-only':True}
        self.supervisor=Mock(sampler=None,run=Mock(side_effect=self.run_supervisor))
        self.nvml=Mock(close=Mock(side_effect=lambda:self.trace.append('nvml_close')))
        self.authorize=Mock(side_effect=lambda *a:self.trace.append('authorize') or {'CPU-MOCK-source':True})
        self.template=Mock(side_effect=lambda *a:self.trace.append('template') or self.spec)
        self.booking=Mock(side_effect=lambda *a:self.trace.append('booking'))
        self.snapshot=Mock(side_effect=lambda *a:self.trace.append('snapshot') or self.fresh)
        self.make_claim=Mock(side_effect=lambda *a,**kw:self.trace.append('Claim') or self.claim)
        self.make_supervisor=Mock(side_effect=lambda *a:self.trace.append('NativeController') or self.supervisor)
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        for name,value in [('authorize',self.authorize),('paths_for',Mock(return_value=self.layout)),
            ('load_execution',self.template),('booking_for_unit',self.booking),
            ('NvmlBackend',Mock(side_effect=lambda:self.trace.append('nvml_init') or self.nvml)),
            ('snapshot',self.snapshot),('Claim',self.make_claim),('NativeController',self.make_supervisor)]:
            self.stack.enter_context(patch.object(controller,name,value))

    def run_supervisor(self):
        self.trace.append('run')
        path=self.root/'runtime'/self.inputs['run_id']/'terminal.json'
        path.write_text(json.dumps(self.report),encoding='utf8')
        return self.report

    def run_route(self):return controller.run(self.config,self.inputs,self.root/'CPU-MOCK-inputs.json',self.root/'CPU-MOCK-template')

    def test_exact_numeric_claim_reserved_once_before_private_head_controller(self):
        self.assertEqual(self.run_route(),self.report)
        self.assertEqual(self.trace,['authorize','scope','template','booking','nvml_init','snapshot',
            'Claim','reserve','NativeController','run','nvml_close'])
        self.assertEqual(self.make_claim.call_args.args[3:6],('numeric','numeric',None))
        self.claim.reserve.assert_called_once_with(self.root/'runtime/gpu-budget.json',self.spec)
        self.assertEqual(json.loads((self.root/'runtime/controller-active.json').read_text())['state'],'released')

    def test_template_or_booking_refusal_has_no_nvml_claim_or_spawn(self):
        for boundary in (self.template,self.booking):
            boundary.side_effect=ValueError('CPU-MOCK original prerequisite refused')
            with self.assertRaises(ValueError):self.run_route()
            self.assertNotIn('nvml_init',self.trace);self.make_claim.assert_not_called()
            self.make_supervisor.assert_not_called()
            boundary.side_effect=lambda *a:self.spec

    def test_busy_original_gpu_never_creates_claim_or_starts_controller(self):
        self.fresh['gpus']['A']['processes']=[{'pid':123}]
        with self.assertRaisesRegex(ValueError,'empty'):self.run_route()
        self.make_claim.assert_not_called();self.make_supervisor.assert_not_called();self.nvml.close.assert_called_once()

    def test_original_claim_rejection_stops_before_reservation_or_head(self):
        self.make_claim.side_effect=ValueError('CPU-MOCK source or booking binding wrong')
        with self.assertRaises(ValueError):self.run_route()
        self.claim.reserve.assert_not_called();self.make_supervisor.assert_not_called();self.nvml.close.assert_called_once()

    def test_previous_unconfirmed_unit_blocks_new_nvml_even_with_locks(self):
        runtime=self.root/'runtime';runtime.mkdir()
        (runtime/'controller-active.json').write_text('{"state":"release_unconfirmed"}',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Prior unit'):self.run_route()
        self.assertNotIn('nvml_init',self.trace);self.make_claim.assert_not_called()

    def test_original340minute_ledger_prevents_new_numeric_reservation(self):
        runtime=self.root/'runtime';runtime.mkdir()
        (runtime/'gpu-budget.json').write_text(json.dumps({'units':{'CPU-MOCK-old':{
            'timing':{'start_monotonic':time.perf_counter()-340*60}}}}),encoding='utf8')
        with self.assertRaisesRegex(TimeoutError,'340min'):self.run_route()
        self.claim.reserve.assert_not_called();self.make_supervisor.assert_not_called();self.nvml.close.assert_called_once()

    def test_source_or_observation_error_blocks_next_unit_despite_released_gpu(self):
        self.report['errors']=['CPU-MOCK final source changed']
        self.run_route()
        active=json.loads((self.root/'runtime/controller-active.json').read_text())
        self.assertEqual(active['state'],'stopped_no_next_unit')


if __name__=='__main__':unittest.main()
