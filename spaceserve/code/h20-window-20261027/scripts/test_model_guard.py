import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import contextlib
from unittest.mock import patch

import model_guard


class GuardTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='posix','requires POSIX interval timer')
    def test_numeric_transition_cannot_claim_model_correctness(self):
        for numeric in ({'scope':'wrong','model_correctness_approved':False},
                        {'scope':'Space-numeric-for-model-preflight','model_correctness_approved':True}):
            with patch.object(model_guard,'run_signals',return_value=contextlib.nullcontext()), \
                 patch.object(model_guard,'require',return_value=3600), \
                 patch.object(model_guard.signal,'setitimer',create=True), \
                 patch.object(model_guard,'_exclusive',return_value=contextlib.nullcontext('numeric-producer')), \
                 patch.object(model_guard,'gate',return_value=numeric),patch.object(model_guard,'model_code') as code:
                with self.assertRaisesRegex(RuntimeError,'consumer scope'):
                    with model_guard.exclusive_models(): self.fail('invalid numeric scope accepted')
                code.assert_not_called()

    @unittest.skipUnless(os.name=='posix','requires actual /proc boot identity')
    def test_model_gate_rejects_formal_stale_and_changed_source(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory).resolve()
            for name in ('configs','evidence','scripts'):
                (root/name).mkdir()
            source=root/'scripts/fixture.py'
            source.write_text('pass\n')
            manifest=root/'configs/model-code-manifest.json'
            manifest.write_text(json.dumps([{'path':'scripts/fixture.py','sha256':hashlib.sha256(source.read_bytes()).hexdigest()}]))
            gate={'passed':True,'allowed_actions':['preflight-models'],
                  'code_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
                  'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'gpu_uuids':model_guard.UUIDS}
            approval=root/'evidence/G2_MODEL_CODE_APPROVED.json'
            approval.write_text(json.dumps(gate))
            with patch.object(model_guard,'ROOT',root):
                self.assertEqual(model_guard.model_code(),gate['code_manifest_sha256'])
                for key,value in (('allowed_actions',['formal']),('boot_id','stale-boot')):
                    rejected={**gate,key:value}
                    approval.write_text(json.dumps(rejected))
                    with self.assertRaises(RuntimeError): model_guard.model_code()
                approval.write_text(json.dumps(gate))
                source.write_text('changed\n')
                with self.assertRaisesRegex(RuntimeError,'code or bound inputs changed'):
                    model_guard.model_code()


if __name__=='__main__':
    unittest.main()
