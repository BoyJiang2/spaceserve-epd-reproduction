import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import audit_cell

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('frozen_cell_fixture', SCRIPTS / 'test_formal_cell.py')
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)


class OfflineAuditTests(unittest.TestCase):
    def test_linux_serialized_paths_on_local_filesystem_and_corruption(self):
        temporary_parent = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=temporary_parent) as directory:
            source = Path(directory)
            self.assertTrue(source.resolve().is_relative_to(temporary_parent))
            case, rows, samples = fixture_module.fixture(source)
            config_path = case / 'measurement/config.json'
            config = json.loads(config_path.read_text())
            config['model'] = str(audit_cell.ROOT / 'models/Qwen2-VL-7B-Instruct')
            config['dataset'] = str(audit_cell.ROOT / 'dataset')
            config_path.write_text(json.dumps(config))
            for row in rows:
                row['images'] = [str(audit_cell.ROOT / 'dataset' / Path(name).name) for name in row['images']]
            requests = case / 'measurement/requests.jsonl'
            requests.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            receipt = {'formal_manifest_sha256': 'a1f79489ec38e14b76f2ae53b6ac6ba9e1f9ac14d33dbb397dbcfa05efca92eb',
                       'tests_passed': 26, 'tests_skipped': 0, 'actual_image_token_id': 99}
            cpu = source / 'evidence/formal-target-CPU.json'
            cpu.write_text(json.dumps(receipt))
            planned = {'images': 4, 'concurrency': 4, 'role': 'baseline-space', 'block': 0}
            self.assertTrue(audit_cell.audit(case, planned, source)['passed'])
            receipt['tests_skipped'] = 1
            cpu.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(RuntimeError, 'CPU receipt'):
                audit_cell.audit(case, planned, source)
            receipt['tests_skipped'] = 0
            cpu.write_text(json.dumps(receipt))
            rows[-1]['images'].reverse()
            requests.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            with self.assertRaisesRegex(RuntimeError, 'image sequence'):
                audit_cell.audit(case, planned, source)


if __name__ == '__main__':
    unittest.main()
