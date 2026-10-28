"""Frozen configuration binding only; no directories outside temporary fixtures."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import types
from unittest.mock import patch
import runtime_config


class ConfigurationTests(unittest.TestCase):
    def test_non_four_device_and_incomplete_selection(self):
        self.assertEqual(runtime_config.device_argument(types.SimpleNamespace(gpu_devices=(2,))),'2')
        for devices in ((),(2,3)):
            with self.assertRaises(ValueError):
                runtime_config.device_argument(types.SimpleNamespace(gpu_devices=devices))

    def fixture(self,base):
        (base/'scripts').mkdir();(base/'configs').mkdir()
        config={'schema':'reproduction-project-v1','project':'spaceserve','state':'candidate',
            'project_root':'/local/boyjiang/spaceserve','host':'qjh003','uid':2147,
            'run_id':None,'gpu_devices':[],'gpu_uuids':[],'booking':None}
        frozen=base/'configs/project.json';frozen.write_text(json.dumps(config))
        external=base/'external.json';external.write_text(json.dumps(config))
        return config,frozen,external

    def test_equal_external_input_switches_to_frozen_file(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);config,frozen,external=self.fixture(base)
            with patch.object(runtime_config,'__file__',str(base/'scripts/runtime_config.py')), \
                 patch.dict(os.environ,{'SPACESERVE_CONFIG':str(external)}):
                self.assertEqual(runtime_config.context().config,config)
                self.assertEqual(os.environ['SPACESERVE_CONFIG'],str(frozen))

    def test_changed_booking_or_actions_refused_before_scope_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);config,frozen,external=self.fixture(base)
            for key,value in (('booking',{'end_ms':999}),('allowed_actions',['formal'])):
                external.write_text(json.dumps({**config,key:value}))
                with patch.object(runtime_config,'__file__',str(base/'scripts/runtime_config.py')), \
                     patch.dict(os.environ,{'SPACESERVE_CONFIG':str(external)}):
                    with self.assertRaises(ValueError):runtime_config.context()

    def test_candidate_cannot_export_gpu_environment(self):
        with patch.object(runtime_config,'context',return_value=runtime_config.ProjectLayout({
            'schema':'reproduction-project-v1','project':'spaceserve','state':'candidate',
            'project_root':'/local/boyjiang/spaceserve','host':'qjh003','uid':2147,
            'run_id':None,'gpu_devices':[],'gpu_uuids':[]})):
            with self.assertRaises(ValueError):runtime_config.shell('numeric')


if __name__=='__main__':unittest.main()
