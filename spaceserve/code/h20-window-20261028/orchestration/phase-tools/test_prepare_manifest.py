"""CPU-only failure preservation; no real phase receipt or deployment is fabricated."""
from pathlib import Path
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

import prepare_manifest as manifest


class ManifestTests(unittest.TestCase):
    def test_numeric_uses_current_window_reviews_without_historical_approvals(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory)
            rows = []
            for index in range(56):
                path = root/'scripts'/('CPU-MOCK-' + str(index) + '.py')
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(b'# CPU-MOCK source only\n')
                rows.append({'path': path.relative_to(root).as_posix(),
                             'bytes': path.stat().st_size, 'sha256': manifest.sha(path)})
            for name in ('configs', 'evidence', 'reviews', 'build'):
                (root/name).mkdir()
            source = root/'configs/runtime-extension-source-manifest.json'
            source.write_text(json.dumps(rows))
            inputs = root/'configs/relocated-inputs.json'; inputs.write_text('[]')
            log = root/'evidence/extension-target-CPU.log'; log.write_text('CPU-MOCK log')
            receipt = {'tests_passed':31,'tests_skipped':0,'source_manifest_sha256':manifest.sha(source),
                'root':manifest.TARGET_ROOT,'input_manifest_sha256':manifest.sha(inputs),
                'log_sha256':manifest.sha(log)}
            (root/'evidence/extension-target-CPU.json').write_text(json.dumps(receipt))
            for name in ('configs/schedule-v2.json', 'evidence/CPU_STAGED.json',
                         'build/libsmctrl.so', 'build/service_sm_probe.so',
                         'reviews/g1g2-final-codex.md', 'reviews/CPU-stage-G2.json'):
                (root/name).write_text('CPU-MOCK fixture; no actual approval')
            with patch.object(manifest, 'BATCH', root), \
                 patch.object(manifest, 'SOURCE_SHA', manifest.sha(source)), \
                 patch.object(manifest, 'INPUT_SHA', manifest.sha(inputs)):
                manifest.freeze('numeric')
            names = [row['path'] for row in json.loads((root/'configs/code-manifest.json').read_text())]
            self.assertEqual([name for name in names if name.startswith('reviews/')],
                             ['reviews/g1g2-final-codex.md', 'reviews/CPU-stage-G2.json'])

    def test_wrong_actual_CPU_root_input_or_log_refuses_before_output(self):
        actual = manifest.BATCH
        previous = actual.parent/'spaceserve-revision-20261027'
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory); (root/'configs').mkdir(); (root/'evidence').mkdir()
            shutil.copyfile(actual/'configs/runtime-extension-source-manifest.json', root/'configs/runtime-extension-source-manifest.json')
            shutil.copyfile(previous/'configs/relocated-inputs.json', root/'configs/relocated-inputs.json')
            log = root/'evidence/extension-target-CPU.log';log.write_text('SYNTHETIC CPU LOG')
            good = {'tests_passed':31,'tests_skipped':0,'source_manifest_sha256':manifest.SOURCE_SHA,
                    'root':manifest.TARGET_ROOT,'input_manifest_sha256':manifest.INPUT_SHA,'log_sha256':manifest.sha(log)}
            for key in ('root','input_manifest_sha256','log_sha256'):
                changed = {**good,key:'WRONG'}
                (root/'evidence/extension-target-CPU.json').write_text(json.dumps(changed))
                with patch.object(manifest,'BATCH',root):
                    with self.assertRaisesRegex(RuntimeError,'CPU receipt'):
                        manifest.freeze('numeric')
                self.assertFalse((root/'configs/code-manifest.json').exists())

    def test_missing_input_never_writes_and_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory); (root/'configs').mkdir()
            output = root/'configs/code-manifest.json'
            with patch.object(manifest, 'BATCH', root):
                with self.assertRaises(FileNotFoundError): manifest.freeze('numeric')
                self.assertFalse(output.exists())
                output.write_bytes(b'preserve original candidate')
                with self.assertRaisesRegex(RuntimeError, 'existing phase manifest'):
                    manifest.freeze('numeric')
                self.assertEqual(output.read_bytes(), b'preserve original candidate')


if __name__ == '__main__':
    unittest.main()
