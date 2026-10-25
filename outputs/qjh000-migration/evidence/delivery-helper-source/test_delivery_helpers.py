"""CPU regressions for the three G2 delivery-helper findings."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

WORK = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, WORK / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package = load('package_space_7b')
unpack = load('unpack_space_phase')


class DeliveryRegression(unittest.TestCase):
    def test_sealed_directory_is_bound_to_fixed_archive(self):
        for prefix in ['', 'sealed/']:
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory(dir=WORK) as temporary:
                folder = Path(temporary) / 'sealed'
                folder.mkdir()
                payload = folder / 'payload.txt'
                payload.write_bytes(b'original')
                manifest = folder / 'SHA256SUMS'
                manifest.write_text(hashlib.sha256(b'original').hexdigest() + '  payload.txt\n')
                archive = Path(temporary) / 'fixed.zip'
                with zipfile.ZipFile(archive, 'x') as output:
                    output.write(payload, prefix + payload.name)
                    output.write(manifest, prefix + manifest.name)
                fixed_sha = package.sha(archive)
                package.verify_sealed_batch(folder, archive, 1, fixed_sha)
                payload.write_bytes(b'changed')
                manifest.write_text(hashlib.sha256(b'changed').hexdigest() + '  payload.txt\n')
                with self.assertRaises(AssertionError):
                    package.verify_sealed_batch(folder, archive, 1, fixed_sha)

    def test_windows_paths_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=WORK) as temporary:
            target = Path(temporary) / 'target'
            target.mkdir()
            self.assertEqual(unpack.destination_for(target, 'results/safe.txt'), target / 'results/safe.txt')
            for name in ['../escape', '/absolute', 'results/../../escape', 'results/..\\..\\escape',
                         'results/C:escape', 'C:/escape', 'results//noncanonical', 'results/./noncanonical', 'results/zero\x00']:
                with self.subTest(name=repr(name)), self.assertRaises(RuntimeError):
                    unpack.destination_for(target, name)

    def test_existing_junction_cannot_escape(self):
        with tempfile.TemporaryDirectory(dir=WORK) as temporary:
            base = Path(temporary)
            target, outside = base / 'target', base / 'outside'
            target.mkdir()
            outside.mkdir()
            link = target / 'results'
            if sys.platform == 'win32':
                subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)], check=True, capture_output=True)
            else:
                link.symlink_to(outside, target_is_directory=True)
            try:
                with self.assertRaises(RuntimeError):
                    unpack.destination_for(target, 'results/escape.txt')
                self.assertEqual(list(outside.iterdir()), [])
            finally:
                if sys.platform == 'win32':
                    link.rmdir()
                else:
                    link.unlink()

    def test_optimized_python_is_rejected_before_work(self):
        for name in ['capture_space_final_metadata.py', 'pack_space_phase.py', 'unpack_space_phase.py', 'package_space_7b.py']:
            with self.subTest(name=name):
                result = subprocess.run([sys.executable, '-O', str(WORK / name)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('verification requires Python without -O', result.stderr)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DeliveryRegression)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    record = {'passed': result.wasSuccessful(), 'tests_run': result.testsRun, 'failures': len(result.failures),
              'errors': len(result.errors), 'scope': 'local CPU fixtures only;no GPU or measured payload changed'}
    (WORK.parent / 'outputs/qjh000-migration/evidence/delivery-helper-regression.json').write_text(json.dumps(record, indent=2) + '\n')
    sys.exit(0 if result.wasSuccessful() else 1)
