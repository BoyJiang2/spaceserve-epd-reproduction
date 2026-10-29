import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    import run_models
except ModuleNotFoundError as error:
    if error.name=='psutil':
        raise unittest.SkipTest('requires target psutil; execute CPU tests on qjh000') from error
    raise


class ModelControlTests(unittest.TestCase):
    def test_failed_mps_start_still_recovers_with_separate_identity(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory).resolve()
            (root/'evidence').mkdir()
            calls=[]
            def command(args,environment,*unused):
                calls.append((args,environment))
                if args[-2:]==['start','4']:
                    intent=json.loads(Path(environment['REPRO_MPS_INTENT']).read_text())
                    self.assertEqual(intent['run_id'],environment['REPRO_RUN_ID'])
                    raise RuntimeError('injected start fault')
            with patch.object(run_models,'ROOT',root),patch.object(run_models,'UUIDS',['CPU-MOCK-GPU']),patch.object(run_models,'DEVICES',(4,)),patch.object(run_models,'require',return_value=3600), \
                 patch.object(run_models,'idle'),patch.object(run_models,'command',side_effect=command), \
                 patch.object(run_models.os,'getuid',return_value=0,create=True),patch.object(run_models,'stop') as stop:
                with self.assertRaisesRegex(RuntimeError,'injected start'):
                    with run_models.service('space-mask','cold',root/'trial'):
                        self.fail('must not enter service after failed start')
            self.assertEqual(calls[-1][0][-1],'recover-stop')
            start=next(environment for args,environment in calls if args[-2:]==['start','4'])
            self.assertNotEqual(stop.call_args.args[0],start['REPRO_RUN_ID'])
            self.assertTrue(stop.call_args.args[0].startswith(str(root)+':service:'))


if __name__=='__main__':
    unittest.main()
