"""Synthetic CPU receipts, never actual approval or runtime output."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import prepare_manifest as manifest


class ManifestTests(unittest.TestCase):
    def fixture(self,root):
        for name in ('scripts','configs','evidence','reviews','build'):(root/name).mkdir()
        member=root/'scripts/CPU-MOCK.py';member.write_text('# fixture only')
        rows=[{'path':'scripts/CPU-MOCK.py','bytes':member.stat().st_size,'sha256':manifest.sha(member)}]
        (root/'configs/source-files.json').write_text(json.dumps([{'path':rows[0]['path'],'source':'CPU-MOCK'}]))
        source=root/'configs/runtime-extension-source-manifest.json';source.write_text(json.dumps(rows))
        inputs=root/'configs/asset-inputs.json';inputs.write_text('[]')
        log=root/'evidence/extension-target-CPU.log';log.write_text('CPU-MOCK')
        receipt={'tests_passed':1,'test_ids':['CPU-MOCK.test_contract'],'tests_skipped':0,
            'source_manifest_sha256':manifest.sha(source),'root':str(root),
            'input_manifest_sha256':manifest.sha(inputs),'log_sha256':manifest.sha(log)}
        (root/'evidence/extension-target-CPU.json').write_text(json.dumps(receipt))
        for name in ('configs/project.json','configs/schedule-v2.json','evidence/CPU_STAGED.json',
            'evidence/GIT_DEPLOYED.json','build/libsmctrl.so','build/service_sm_probe.so',
            'reviews/G1-project.md','reviews/G2-source.md'):
            (root/name).write_text('CPU-MOCK; no actual approval')
        return receipt,source,inputs

    def test_current_reviews_and_no_duplicate_source_members(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);receipt,source,inputs=self.fixture(root)
            with patch.object(manifest,'BATCH',root),patch.object(manifest,'TARGET_ROOT',str(root)), \
                 patch.object(manifest,'SOURCE_SHA',manifest.sha(source)),patch.object(manifest,'INPUT_SHA',manifest.sha(inputs)):
                manifest.freeze('numeric')
            rows=json.loads((root/'configs/code-manifest.json').read_text());names=[row['path'] for row in rows]
            self.assertEqual(len(names),len(set(names)))
            self.assertEqual([name for name in names if name.startswith('reviews/')],['reviews/G1-project.md','reviews/G2-source.md'])

    def test_wrong_cpu_root_input_or_log_never_writes_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);good,source,inputs=self.fixture(root)
            for key in ('root','input_manifest_sha256','log_sha256'):
                (root/'evidence/extension-target-CPU.json').write_text(json.dumps({**good,key:'WRONG'}))
                with patch.object(manifest,'BATCH',root),patch.object(manifest,'TARGET_ROOT',str(root)), \
                     patch.object(manifest,'SOURCE_SHA',manifest.sha(source)),patch.object(manifest,'INPUT_SHA',manifest.sha(inputs)):
                    with self.assertRaisesRegex(RuntimeError,'CPU receipt'):manifest.freeze('numeric')
                self.assertFalse((root/'configs/code-manifest.json').exists())

    def test_missing_input_and_existing_output_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'configs').mkdir();output=root/'configs/code-manifest.json'
            with patch.object(manifest,'BATCH',root):
                with self.assertRaises(FileNotFoundError):manifest.freeze('numeric')
                output.write_bytes(b'preserve')
                with self.assertRaisesRegex(RuntimeError,'existing phase manifest'):manifest.freeze('numeric')
                self.assertEqual(output.read_bytes(),b'preserve')


if __name__=='__main__':unittest.main()
