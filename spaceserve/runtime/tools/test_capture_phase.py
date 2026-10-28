"""Synthetic failed-service file discovery, before any device-record copytree."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import types

from capture_phase import selected_files, phase_code


class CaptureTests(unittest.TestCase):
    def test_model_checks_archived_numeric_and_current_model_separately(self):
        numeric=Mock(return_value='numeric-producer')
        model=Mock(return_value='current-model-producer')
        with patch.dict('sys.modules',{'resource_guard':types.SimpleNamespace(code_identity=numeric),
                                      'model_guard':types.SimpleNamespace(model_code=model)}):
            self.assertEqual(phase_code('model'),('numeric-producer','current-model-producer'))
            numeric.assert_called_once_with(None);model.assert_called_once_with()
            numeric.reset_mock();model.reset_mock()
            self.assertEqual(phase_code('numeric'),('numeric-producer','numeric-producer'))
            numeric.assert_called_once_with('numeric');model.assert_not_called()

    def test_failed_model_keeps_uncopied_devices_intent_and_launcher(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory)
            names = ['results/runtime-devices/preflight-cold-space/worker-11.json',
                     'results/runtime-devices/preflight-cold-space/sm-stream-11.jsonl',
                     'evidence/mps-start-intent-model-SYNTHETIC.json',
                     'evidence/models-attempt1-launcher-stdout.log']
            for name in names:
                path = root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('SYNTHETIC FAILED SERVICE')
            self.assertFalse((root/'results/preflight-models-attempt1').exists())
            selected = selected_files(root,'model')
            self.assertTrue(all(root/name in selected for name in names))
            self.assertNotIn(root/'models/weights',selected)


if __name__ == '__main__':
    unittest.main()
