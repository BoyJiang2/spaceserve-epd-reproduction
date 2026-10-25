"""CPU guards tested with sealed 2B request-format fixtures; no claim of a 7B run."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


audit = module('audit_formal_case').audit
parse_clients = module('capture_mps_clients').parse_clients
verify_points = module('verify_points').verify


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.case = Path(self.directory.name)
        (self.case / 'measurement').mkdir()
        source = ROOT / 'outputs/reproduction/data/raw/sapphire1/baseline-space-4090-mps'
        for name in ['requests.jsonl', 'summary.json']:
            (self.case / 'measurement' / name).write_bytes((source / 'images1-c1' / name).read_bytes())
        config = json.loads((source / 'images1-c1/config.json').read_text())
        config['model'] = '/fixture/Qwen2-VL-7B-Instruct'  # Metadata only; preserves old measured rows for format tests.
        (self.case / 'measurement/config.json').write_text(json.dumps(config))
        all_samples = [json.loads(line) for line in (source / 'gpu-memory.jsonl').read_text().splitlines()]
        summaries = json.loads((self.case / 'measurement/summary.json').read_text())
        samples = [row for row in all_samples if any(item['start_perf_counter'] <= row['perf_counter'] <= item['end_perf_counter'] for item in summaries)]
        for row in samples:
            for gpu in row['gpus']:
                gpu['foreign_compute_pids'] = []
        (self.case / 'gpu-memory.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in samples))
        (self.case / 'rgb-after.json').write_text('{"passed":true}')

    def tearDown(self):
        self.directory.cleanup()

    def test_existing_successful_request_format_is_accepted(self):
        self.assertTrue(audit(self.case)['passed'])

    def test_duplicate_warmup_is_rejected(self):
        path = self.case / 'measurement/requests.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[1]['index'] = rows[0]['index']
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        with self.assertRaisesRegex(RuntimeError, 'warmup'):
            audit(self.case)

    def test_foreign_target_gpu_process_is_rejected(self):
        path = self.case / 'gpu-memory.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]['gpus'][0]['foreign_compute_pids'] = [999999]
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        with self.assertRaisesRegex(RuntimeError, 'foreign'):
            audit(self.case)

    def test_mps_ps_parses_documented_columns_and_rejects_unrecognized_text(self):
        self.assertEqual(parse_clients('6472\nPID ID SERVER DEVICE NAMESPACE COMMAND\n9741 0 6472 GPU-cb1213a3-d6a4-be7f 4026531836 ./nbody\n')[0]['pid'], 9741)
        with self.assertRaises(RuntimeError):
            parse_clients('unknown response\n')

    def test_changed_payload_and_inner_manifest_are_rejected_by_original_approval(self):
        (self.case / 'points').mkdir()
        payload = self.case / 'points/requests.jsonl'
        payload.write_text('original\n')
        inner = self.case / 'points.sha256'
        inner.write_text(hashlib.sha256(payload.read_bytes()).hexdigest() + '  ' + str(payload) + '\n')
        outer = hashlib.sha256(inner.read_bytes()).hexdigest() + '  ' + str(inner) + '\n'
        (self.case / 'points-manifest.sha256').write_text(outer)
        (self.case / 'G4_POINTS_APPROVED').write_text(outer)
        self.assertTrue(verify_points(self.case)['passed'])
        payload.write_text('changed\n')
        inner.write_text(hashlib.sha256(payload.read_bytes()).hexdigest() + '  ' + str(payload) + '\n')
        with self.assertRaisesRegex(RuntimeError, 'G4-approved digest'):
            verify_points(self.case)


if __name__ == '__main__':
    unittest.main(verbosity=2)
