import contextlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

try:
    import mps_recovery
except ModuleNotFoundError as error:
    if error.name=='psutil':
        raise unittest.SkipTest('requires copied target psutil; execute on qjh000 CPU') from error
    raise
import run_numeric


class RecoveryTests(unittest.TestCase):
    def test_numeric_start_raises_after_spawn_still_calls_recovery(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory).resolve()
            for name in ('results','evidence'):
                (root/name).mkdir()
            calls=[]
            def command(args,**kwargs):
                calls.append(args)
                if args[-2:]==['start','4']:
                    intent_path=Path(kwargs['env']['REPRO_MPS_INTENT'])
                    self.assertTrue(intent_path.exists())
                    intent=json.loads(intent_path.read_text())
                    self.assertEqual(intent['root'],str(root))
                    raise RuntimeError('injected daemon spawned but start did not return')
            with patch.object(run_numeric,'ROOT',root),patch.object(run_numeric,'UUIDS',['CPU-MOCK-GPU']),patch.object(run_numeric,'DEVICES',(4,)),patch.dict(run_numeric.CONFIG.config,{'cuda_home':'/CPU-MOCK/cuda'}), \
                 patch.object(run_numeric,'exclusive',return_value=contextlib.nullcontext('candidate-code')), \
                 patch.object(run_numeric,'idle'),patch.object(run_numeric.os,'getuid',return_value=0,create=True), \
                 patch.object(run_numeric.subprocess,'run',side_effect=command):
                with self.assertRaisesRegex(RuntimeError,'injected daemon'):
                    run_numeric.main()
            self.assertTrue(any(args[-1]=='recover-stop' for args in calls))
            self.assertFalse((root/'results/numeric/COMPLETED.json').exists())

    def test_only_unique_matching_daemon_can_be_recovered(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory).resolve()
            (root/'tmp/mps').mkdir(parents=True)
            control=root/'tmp/mps/control'
            control.write_text('CPU fixture')
            uid=control.stat().st_uid
            intent={'root':str(root),'uid':uid,'pipe':str(root/'tmp/mps'),
                    'token':str(root)+':unique','run_id':str(root)+':run','started_epoch':10,'uuid':'fixture'}
            env={'EXP_ROOT':str(root),'REPRO_MPS_OWNER':intent['token'],
                 'CUDA_MPS_PIPE_DIRECTORY':intent['pipe'],'REPRO_RUN_ID':intent['run_id']}
            process=types.SimpleNamespace(pid=123,name=lambda:'nvidia-cuda-mps-control',
                uids=lambda:types.SimpleNamespace(real=uid),status=lambda:'sleeping',
                environ=lambda:env,create_time=lambda:11)
            with patch.object(mps_recovery.os,'getuid',return_value=uid,create=True):
                self.assertEqual(mps_recovery.recover(root,intent,[process])['pid'],123)
                with self.assertRaisesRegex(RuntimeError,'unique private'):
                    mps_recovery.recover(root,intent,[process,process])
                with patch.object(process,'environ',side_effect=mps_recovery.psutil.AccessDenied(123)):
                    with self.assertRaisesRegex(RuntimeError,'identity unconfirmed'):
                        mps_recovery.recover(root,intent,[process])


if __name__=='__main__':
    unittest.main()
