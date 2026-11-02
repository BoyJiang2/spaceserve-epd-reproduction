"""CPU-MOCK public routing tests; no original runtime receipts or GPU grants."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import entry
import numeric_controller


class NumericEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.config=self.root/'project.json'; self.config.write_text('{}',encoding='utf8')
        self.inputs=self.root/'inputs.json'; self.inputs.write_text('{"CPU-MOCK-input":true}',encoding='utf8')
        self.template=self.root/'numeric.json'; self.template.write_text('{"phase":"numeric"}',encoding='utf8')
        self.layout=NS(run_root=self.root,config={'run_id':'CPU-MOCK'},require_scope=Mock())
        self.argv=['entry.py','numeric','--config',str(self.config),'--inputs',str(self.inputs),
                   '--unit-template',str(self.template)]

    def call(self, report):
        original_read=Path.read_bytes
        def read(path):
            # No approved static file exists yet; inject only at this mocked boundary.
            if path==Path(entry.__file__).with_name('preflight-static.json'):
                return b'{"CPU-MOCK-static":"not an authorization"}'
            return original_read(path)
        with patch.object(entry,'context',return_value=self.layout), patch('sys.argv',self.argv), \
                patch.object(entry.os,'chdir') as changed, patch.dict(os.environ,clear=False), \
                patch.object(Path,'read_bytes',read), \
                patch.object(numeric_controller,'run',return_value=report) as run:
            result=entry.main()
            self.layout.require_scope.assert_called_once_with('numeric')
            changed.assert_called_once_with(self.root)
            self.assertEqual(run.call_args.args[0],{'CPU-MOCK-static':'not an authorization'})
            self.assertEqual(run.call_args.args[1],{'CPU-MOCK-input':True})
            self.assertEqual(run.call_args.args[2:],(self.inputs.resolve(),self.template.resolve()))
            return result

    def test_numeric_routes_to_production_controller_with_original_paths(self):
        self.assertEqual(self.call({'state':'released','failure':None,'errors':[]}),0)

    def test_unconfirmed_or_failed_result_is_nonzero(self):
        for report in [dict(state='release_unconfirmed',failure=None,errors=[]),
                       dict(state='released',failure={'CPU-MOCK':'failed'},errors=[]),
                       dict(state='released',failure=None,errors=['CPU-MOCK observation failed'])]:
            self.layout.require_scope.reset_mock()
            self.assertEqual(self.call(report),1)

    def test_actual_candidate_scope_rejects_before_controller_or_gpu(self):
        with patch('sys.argv',['entry.py','numeric']), patch.dict(os.environ,clear=False), \
                patch.object(numeric_controller,'run') as run, patch.object(numeric_controller,'NvmlBackend') as nvml:
            with self.assertRaisesRegex(ValueError,'Candidate'):entry.main()
            run.assert_not_called();nvml.assert_not_called()

    def test_selected_remains_explicitly_blocked(self):
        with patch('sys.argv',['entry.py','selected_g3']), patch.dict(os.environ,clear=False), \
                patch.object(numeric_controller,'run') as run:
            with self.assertRaises(NotImplementedError):entry.main()
            run.assert_not_called()

    def test_wrong_phase_template_fails_before_controller(self):
        self.template.write_text('{"phase":"qualification"}',encoding='utf8')
        with patch.object(entry,'context',return_value=self.layout),patch('sys.argv',self.argv), \
                patch.dict(os.environ,clear=False),patch.object(numeric_controller,'run') as run:
            with self.assertRaisesRegex(ValueError,'phase'):entry.main()
            run.assert_not_called()

    def test_relative_input_owner_resolved_before_actual_cohort_chdir(self):
        cohort=self.root/'cohort';cohort.mkdir()
        self.layout.run_root=cohort
        (cohort/'inputs.json').write_text('{"CPU-MOCK-wrong-cohort-input":true}',encoding='utf8')
        args=['entry.py','numeric','--config','project.json','--inputs','inputs.json','--unit-template','numeric.json']
        original_read=Path.read_bytes
        def read(path):
            if path==Path(entry.__file__).with_name('preflight-static.json'):
                return b'{"CPU-MOCK-static":"not an authorization"}'
            return original_read(path)
        saved=Path.cwd()
        try:
            os.chdir(self.root)
            with patch.object(entry,'context',return_value=self.layout),patch('sys.argv',args), \
                    patch.dict(os.environ,clear=False),patch.object(Path,'read_bytes',read), \
                    patch.object(numeric_controller,'run',return_value={'state':'released','failure':None,'errors':[]}) as run:
                self.assertEqual(entry.main(),0)
                self.assertEqual(Path.cwd(),cohort)
                self.assertEqual(run.call_args.args[1],{'CPU-MOCK-input':True})
                self.assertEqual(run.call_args.args[2],self.inputs.resolve())
                self.assertEqual(run.call_args.args[3],self.template.resolve())
        finally:os.chdir(saved)


if __name__=='__main__':unittest.main()
