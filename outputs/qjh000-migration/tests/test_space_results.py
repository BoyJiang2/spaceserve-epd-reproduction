"""CPU-only statistics/identity tests; sealed2B rows test format, not7B performance."""
import json
import hashlib
import copy
from pathlib import Path
import shutil
import statistics
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'analysis'))
sys.path.insert(0, str(ROOT / 'tests'))
from space_results import REMOTE, collect, stats, validate_memory, validate_points_manifest, validate_role
import test_formal_guards as guards


class StatisticsTests(unittest.TestCase):
    def test_changed_points_and_inner_list_rejected_by_outer_digest(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parents[1] / 'work') as temporary:
            folder = Path(temporary)
            (folder / 'points').mkdir()
            payload = folder / 'points/data.json'
            payload.write_text('original')
            inner = folder / 'points.sha256'
            inner.write_text(hashlib.sha256(payload.read_bytes()).hexdigest() + '  ' + REMOTE + '/results/formal/points/data.json\n')
            outer = folder / 'points-manifest.sha256'
            outer.write_text(hashlib.sha256(inner.read_bytes()).hexdigest() + '  ' + REMOTE + '/results/formal/points.sha256\n')
            self.assertEqual(validate_points_manifest(folder, 'points')['bound_files'], 1)
            (folder / 'G4_POINTS_APPROVED').write_bytes(outer.read_bytes())
            self.assertEqual(validate_points_manifest(folder, 'all')['bound_files'], 1)
            payload.write_text('changed')
            inner.write_text(hashlib.sha256(payload.read_bytes()).hexdigest() + '  ' + REMOTE + '/results/formal/points/data.json\n')
            with self.assertRaisesRegex(RuntimeError, 'frozen outer digest'):
                validate_points_manifest(folder, 'points')

    def test_percentiles_use_inclusive_linear_interpolation(self):
        values = [1, 2, 4, 5, 9]
        reference = statistics.quantiles(values, n=100, method='inclusive')
        result = stats(values)
        self.assertAlmostEqual(result['p50'], reference[49])
        self.assertAlmostEqual(result['p95'], reference[94])
        self.assertEqual(stats([3])['sd'], 0)
        with self.assertRaises(RuntimeError):
            stats([float('nan')])

    def test_actual_cold_identity_fixture_rejects_foreign_gpu_and_library(self):
        source = ROOT / 'results/preflight-cold/space-mask'
        with tempfile.TemporaryDirectory(dir=ROOT.parents[1] / 'work') as temporary:
            folder = Path(temporary)
            shutil.copyfile(source / 'runtime.json', folder / 'runtime.json')
            shutil.copyfile(source / 'mps-identity-before.json', folder / 'mps-identity.json')
            (folder / 'device-records').mkdir()
            for path in (ROOT / 'results/runtime-devices/preflight-cold-space-mask').glob('*.json'):
                shutil.copyfile(path, folder / 'device-records' / path.name)
            (folder / 'COMPLETED').write_text('fixture')
            self.assertEqual(len(validate_role(folder, 'space-mask')['model_parameters']), 2)
            path = folder / 'runtime.json'
            original = path.read_bytes()
            runtime = json.loads(original)
            runtime['servers'][0]['environment']['CUDA_VISIBLE_DEVICES'] = 'GPU-other'
            path.write_text(json.dumps(runtime))
            with self.assertRaisesRegex(RuntimeError, 'GPU/MPS/library'):
                validate_role(folder, 'space-mask')
            path.write_bytes(original)
            path = next((folder / 'device-records').glob('worker-*.json'))
            worker = json.loads(path.read_text())
            worker['loaded_smctrl_sha256'] = {'foreign-library': 'wrong-sha'}
            path.write_text(json.dumps(worker))
            with self.assertRaisesRegex(RuntimeError, 'dtype/GPU/library'):
                validate_role(folder, 'space-mask')
            original = json.loads((ROOT / 'results/runtime-devices/preflight-cold-space-mask' / path.name).read_text())
            for field, value in [('mps_active_thread_percentage', '50'), ('mps_pipe', '/other'), ('cuda_device_uuid', 'other'), ('parameters_by_component', {'visual': 1})]:
                changed = {**original, field: value}
                path.write_text(json.dumps(changed))
                with self.subTest(field=field), self.assertRaises(RuntimeError):
                    validate_role(folder, 'space-mask')
            path.write_text(json.dumps(original))
            path = folder / 'mps-identity.json'
            boundary = json.loads(path.read_text())
            boundary['physical_gpu_processes'] = []
            path.write_text(json.dumps(boundary))
            with self.assertRaisesRegex(RuntimeError, 'NVML'):
                validate_role(folder, 'space-mask')

    def test_memory_identity_sum_and_time_rejection(self):
        identity = {'required_gpu_pids': [1, 2], 'allowed_gpu_pids': [1, 2, 99]}
        gpu = {'device': 0, 'physical_used_bytes': 100, 'owned_processes': [{'pid': 1, 'used_bytes': 10}, {'pid': 2, 'used_bytes': 20}], 'owned_process_sum_bytes': 30, 'foreign_compute_pids': []}
        original = [{'perf_counter': stamp, 'gpus': [copy.deepcopy(gpu)]} for stamp in [1, 2]]
        validate_memory(original, identity, 1000)
        for mode in ['unknown_pid', 'wrong_sum', 'negative_bytes', 'missing_bytes', 'duplicate_pid', 'physical_capacity', 'nonmonotonic']:
            samples = copy.deepcopy(original)
            current = samples[0]['gpus'][0]
            if mode == 'unknown_pid':
                current['owned_processes'][0]['pid'] = 3
            elif mode == 'wrong_sum':
                current['owned_process_sum_bytes'] = 31
            elif mode == 'negative_bytes':
                current['owned_processes'][0]['used_bytes'] = -1
            elif mode == 'missing_bytes':
                del current['owned_processes'][0]['used_bytes']
            elif mode == 'duplicate_pid':
                current['owned_processes'][0]['pid'] = 2
            elif mode == 'physical_capacity':
                current['physical_used_bytes'] = 1001
            else:
                samples[1]['perf_counter'] = 0
            with self.subTest(mode=mode), self.assertRaises(RuntimeError):
                validate_memory(samples, identity, 1000)


class CaseTests(unittest.TestCase):
    setUp = guards.GuardTests.setUp
    tearDown = guards.GuardTests.tearDown

    def test_statistics_fixture_and_rgb_change_rejection(self):
        (self.case / 'COMPLETED').write_text('fixture')
        rgb = {'passed': True, 'records': [{'pid': 123, 'manifest_sha256': 'fixture',
               'url': json.loads((self.case / 'measurement/config.json').read_text())['urls'][0],
               'images': [{'file': str(i), 'rgb_sha256': 'fixture'} for i in range(20)]}]}
        for when in ['before', 'after']:
            (self.case / f'rgb-{when}.json').write_text(json.dumps(rgb))
        memory_path = self.case / 'gpu-memory.jsonl'
        samples = [json.loads(line) for line in memory_path.read_text().splitlines()]
        for sample in samples:
            for gpu in sample['gpus']:
                gpu['device'] = 0  # Fixture metadata only: old4090 rows are not a qjh000 measurement.
        memory_path.write_text(''.join(json.dumps(sample) + '\n' for sample in samples))
        pids = sorted({row['pid'] for sample in samples for row in sample['gpus'][0]['owned_processes']})
        identity = {'api_pid': 123, 'api_url': rgb['records'][0]['url'], 'allowed_gpu_pids': pids, 'required_gpu_pids': pids}
        capacity = max(sample['gpus'][0]['physical_used_bytes'] for sample in samples) * 2
        record, rows, _, _ = collect(self.case, 'baseline-space', 1, 1, identity, capacity)
        self.assertEqual(record['formal_requests'], 300)
        self.assertEqual(len(rows), 320)
        self.assertGreater(record['requests_per_s']['mean'], 0)
        rgb['records'][0]['images'][0]['rgb_sha256'] = 'changed'
        (self.case / 'rgb-after.json').write_text(json.dumps(rgb))
        with self.assertRaisesRegex(RuntimeError, 'RGB'):
            collect(self.case, 'baseline-space', 1, 1, identity, capacity)
        rgb['records'][0]['images'][0]['rgb_sha256'] = 'fixture'
        (self.case / 'rgb-after.json').write_text(json.dumps(rgb))
        path = self.case / 'measurement/requests.jsonl'
        original = path.read_bytes()
        rows = [json.loads(line) for line in original.splitlines()]
        rows[0]['endpoint'] = 'http://wrong-endpoint'
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        with self.assertRaisesRegex(RuntimeError, 'endpoint'):
            collect(self.case, 'baseline-space', 1, 1, identity, capacity)
        path.write_bytes(original)
        rgb['records'][0]['url'] = 'http://wrong-rgb'
        (self.case / 'rgb-after.json').write_text(json.dumps(rgb))
        with self.assertRaisesRegex(RuntimeError, 'endpoint'):
            collect(self.case, 'baseline-space', 1, 1, identity, capacity)


if __name__ == '__main__':
    unittest.main()
