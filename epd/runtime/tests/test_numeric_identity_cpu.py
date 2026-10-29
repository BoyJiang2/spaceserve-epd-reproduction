"""No Ray/Torch/NVML imports or GPU calls: numeric identity is not an HTTP service."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import production_identity as identity


class NumericIdentityTests(unittest.TestCase):
    def setUp(self):
        base = Path(os.environ['EPD_CPU_TEST_TMP']).resolve(strict=True)
        self.temp = tempfile.TemporaryDirectory(prefix='numeric-identity-', dir=base)
        self.root = Path(self.temp.name).resolve()
        self.env = dict(REPRO_IDENTITY='1', REPRO_NUMERIC_ONLY='1', REPRO_REQUEST_IDENTITY='0',
            EXP_ROOT=str(self.root), REPRO_RUN_ID='CPU-MOCK-numeric', REPRO_SOURCE_COMMIT='a'*40,
            REPRO_DEPLOY_SHA256='b'*64, REPRO_PROFILE_SHA256='c'*64,
            REPRO_ENDPOINT='gcs://127.0.0.1:45127', REPRO_GPU_UUIDS=json.dumps([
                'GPU-'+str(i)*8+'-1111-1111-1111-111111111111' for i in range(3)]))
        self.environ = patch.dict(os.environ, self.env); self.environ.start()
        self.cwd = patch.object(Path, 'cwd', return_value=self.root); self.cwd.start()

    def tearDown(self):
        self.cwd.stop(); self.environ.stop(); self.temp.cleanup()

    def test_numeric_mode_and_actual_gcs_endpoint_are_preserved(self):
        values = identity.environment()
        self.assertEqual(values['REPRO_NUMERIC_ONLY'], '1')
        self.assertEqual(values['REPRO_REQUEST_IDENTITY'], '0')
        self.assertEqual(values['REPRO_ENDPOINT'], self.env['REPRO_ENDPOINT'])

    def test_numeric_invalid_endpoint_or_http_diagnostics_rejected(self):
        for endpoint in ('http://127.0.0.1:45127', 'ray://127.0.0.1:45127',
                         'gcs://remote:45127', 'gcs://127.0.0.1', 'gcs://127.0.0.1:45127/',
                         'gcs://127.0.0.1:45127?x=1', 'gcs://u@127.0.0.1:45127',
                         'gcs://127.0.0.1:45127#x'):
            with self.subTest(endpoint=endpoint), patch.dict(os.environ, REPRO_ENDPOINT=endpoint):
                with self.assertRaises(ValueError): identity.environment()
        for change in ({'REPRO_REQUEST_IDENTITY':'1'}, {'REPRO_SOURCE_COMMIT':''}, {'REPRO_NUMERIC_ONLY':'2'}):
            with self.subTest(change=change), patch.dict(os.environ, change):
                with self.assertRaises(ValueError): identity.environment()

    def test_http_mode_stays_http_and_rejects_gcs(self):
        with patch.dict(os.environ, REPRO_NUMERIC_ONLY='0', REPRO_REQUEST_IDENTITY='1'):
            with self.assertRaises(ValueError): identity.environment()
            with patch.dict(os.environ, REPRO_ENDPOINT='http://127.0.0.1:17778'):
                self.assertEqual(identity.environment()['REPRO_REQUEST_IDENTITY'], '1')
                self.assertNotIn('REPRO_NUMERIC_ONLY', identity.environment())

    def test_numeric_cannot_publish_or_assemble_http_evidence(self):
        with patch.object(identity, 'write_exclusive') as write:
            with self.assertRaises(ValueError): identity.publish_service([{}], 45127)
            with self.assertRaises(ValueError): identity.assemble_services([], self.root/'fake.json')
            write.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_numeric_non_decoding_stage_rejected_before_torch_or_capture(self):
        with patch.dict(sys.modules, torch=None), patch.object(identity, 'capture_own_identity') as capture:
            with self.assertRaises(ValueError): identity.worker_identity(0, 'ENCODING')
            capture.assert_not_called()

    def test_numeric_cuda_identity_uses_observed_uuid_and_gcs_endpoint(self):
        uuid = json.loads(self.env['REPRO_GPU_UUIDS'])[2]
        torch = SimpleNamespace(cuda=SimpleNamespace(get_device_properties=lambda device: SimpleNamespace(uuid=uuid)))
        with patch.dict(sys.modules, torch=torch), patch.object(identity, 'capture_own_identity', return_value={}) as capture:
            identity.worker_identity(0, 'DECODING')
            self.assertEqual(capture.call_args.args[4:6], (uuid, 'DECODING'))
            self.assertEqual(capture.call_args.kwargs['endpoint'], self.env['REPRO_ENDPOINT'])


if __name__ == '__main__': unittest.main()
