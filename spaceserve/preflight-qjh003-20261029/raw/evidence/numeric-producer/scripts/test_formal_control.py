import contextlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    import formal_service
    import formal_guard
except ModuleNotFoundError as error:
    if error.name=='psutil': raise unittest.SkipTest('requires actual target CPU dependencies') from error
    raise


class FormalControlTests(unittest.TestCase):
    def test_all_roles_disable_diagnostics_and_start_failure_still_recovers(self):
        for role in ('baseline-space','space','space-mask'):
            with self.subTest(role=role),tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
                root=Path(directory).resolve()
                (root/'evidence').mkdir()
                calls=[]
                def command(args,environment,*unused):
                    calls.append((args,environment))
                    self.assertEqual(environment['REPRO_SM_PROBE'],'0')
                    self.assertNotIn('VLLM_TORCH_PROFILER_DIR',environment)
                    if args[-2:]==['start','4']: raise RuntimeError('injected start fault')
                with patch.object(formal_service,'ROOT',root),patch.object(formal_service,'UUIDS',['CPU-MOCK-GPU']),patch.object(formal_service,'DEVICES',(4,)),patch.object(formal_service,'require',return_value=3600), \
                     patch.object(formal_service,'idle'),patch.object(formal_service,'command',side_effect=command), \
                     patch.object(formal_service.os,'getuid',return_value=0,create=True), \
                     patch.dict(os.environ,VLLM_TORCH_PROFILER_DIR='must-be-cleared'),patch.object(formal_service,'stop'):
                    with self.assertRaisesRegex(RuntimeError,'injected start'):
                        with formal_service.service(role,0,root/'cell'): self.fail('must not enter failed service')
                self.assertEqual(calls[-1][0][-1],'recover-stop')

    @unittest.skipUnless(os.name=='posix','requires POSIX interval timer')
    def test_formal_needs_actual_model_gate_and_never_accepts_data_approval(self):
        with patch.object(formal_guard,'run_signals',return_value=contextlib.nullcontext()), \
             patch.object(formal_guard,'require',return_value=3600),patch.object(formal_guard.signal,'setitimer'), \
             patch.object(formal_guard,'_exclusive',return_value=contextlib.nullcontext()), \
             patch.object(formal_guard,'model_code',return_value='model-producer'), \
             patch.object(formal_guard,'gate',return_value={'scope':'Space-model-preflight-for-formal','formal_data_approved':True}), \
             patch.object(formal_guard,'formal_code') as code:
            with self.assertRaisesRegex(RuntimeError,'actual model G3'):
                with formal_guard.exclusive_formal(): self.fail('invalid proof accepted')
            code.assert_not_called()


if __name__=='__main__': unittest.main()
