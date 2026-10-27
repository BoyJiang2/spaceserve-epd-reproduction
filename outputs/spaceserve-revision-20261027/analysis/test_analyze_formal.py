"""Synthetic CPU-only aggregation fixtures; never experiment evidence or Gates."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import analyze_formal as analyzer


class WholeMatrixTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(__file__).resolve().parent
        self.temporary = tempfile.TemporaryDirectory(dir=self.parent)
        self.root = Path(self.temporary.name)
        assert self.root.resolve().is_relative_to(self.parent)
        self.addCleanup(self.temporary.cleanup)
        (self.root / 'SYNTHETIC-CPU-ONLY.txt').write_text('Never real GPU data or a valid Gate.')
        for name in ('configs', 'evidence', 'results/formal'):
            (self.root / name).mkdir(parents=True)
        self.schedule = analyzer.read(self.parent.parent / 'configs/schedule-v2.json')
        (self.root / 'configs/schedule-v2.json').write_text(json.dumps(self.schedule))
        self.start = {'controller_id': 'CPU-fixture-controller', 'pid': 123,
                      'process_created': 1793051887.29, 'started_unix': 1793051887.58}
        self.write('evidence/FORMAL_STARTED.json', self.start)
        self.write('evidence/formal-exit.json', {**self.start, 'exit_code': 0})
        self.write('evidence/formal-final-booking-state.json', {'booking': {'resource_id': 'h20/qjh000',
            'node': 'qjh000', 'user': 'boyjiang', 'kind': 'gpu',
            'start_ms': 1793019600000, 'end_ms': 1793062800000}})
        self.write('results/formal/COMPLETED.json', {'formal_code_manifest_sha256': analyzer.FORMAL,
            'schedule_sha256': analyzer.SCHEDULE, 'formal_requests': 5400, 'warmup_requests': 1080})
        for row in self.schedule['cells']:
            (self.root / 'results/formal' / self.name(row)).mkdir()

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value))

    def name(self, row):
        return f'{row["index"]:03d}-b{row["block"]}-i{row["images"]}-c{row["concurrency"]}-{row["role"]}'

    def described(self, case, row, root):
        index = row['index']
        rate = 1 if row['role'] == 'baseline-space' else 2
        return {'metrics': {'requests_per_s': rate, 'output_tokens_per_s': 128 * rate, 'failure_rate': 0,
                           'latency_s': {'p50': 2., 'p95': 3.}, 'ttft_s': {'p50': .1, 'p95': .2},
                           'tpot_s': {'p50': .01, 'p95': .02}},
                'sampled_peak_bytes': 1000, 'start': 1000 + 10 * index, 'end': 1005 + 10 * index,
                'host_before_utc_ns': 1793052000000000000 + 10**10 * index,
                'host_after_utc_ns': 1793052006000000000 + 10**10 * index,
                'service_identity': 'CPU-fixture-' + str(index), 'api_identity': [123 + index, index]}

    def analyze(self, describe=None):
        # These mocks isolate aggregation from the independently tested cell/input validators.
        with patch.object(analyzer, 'verify_inputs'), patch.object(analyzer, 'describe', side_effect=describe or self.described):
            return analyzer.analyze(self.root)

    def test_complete_matrix_all_planned_pairs_and_metrics(self):
        result = self.analyze()
        self.assertTrue(result['complete'])
        self.assertEqual((result['valid_cells'], len(result['all_planned_pairs']), len(result['intervals'])), (54, 54, 18))
        self.assertEqual(len(result['intervals'][0]['metrics']), 9)
        for interval in result['intervals']:
            self.assertAlmostEqual(interval['throughput']['geometric_mean_ratio'],
                                   1 if interval['baseline_role'] == 'space' else 2)
        self.assertEqual(sum(row['baseline_role'] == 'space' for row in result['all_planned_pairs']), 18)

    def test_partial_keeps_all_plans_and_never_intervals(self):
        last = self.schedule['cells'][-1]
        (self.root / 'results/formal' / self.name(last)).rmdir()
        result = self.analyze()
        self.assertFalse(result['complete'])
        self.assertEqual((len(result['cells']), result['valid_cells'], len(result['all_planned_pairs'])), (54, 53, 54))
        self.assertEqual(result['intervals'], [])
        self.assertTrue(any(row['throughput_ratio'] is None for row in result['all_planned_pairs']))

    def test_global_order_conflict_disables_every_ratio(self):
        def corrupt(case, row, root):
            result = self.described(case, row, root)
            if row['index'] == 1:
                result['start'] = 999
            return result
        result = self.analyze(corrupt)
        self.assertTrue(result['global_errors'])
        self.assertFalse(result['complete'])
        self.assertTrue(all(row['throughput_ratio'] is None for row in result['all_planned_pairs']))

    def test_reused_identity_disables_every_ratio(self):
        def corrupt(case, row, root):
            result = self.described(case, row, root)
            result['service_identity'] = 'CPU-fixture-reused'
            return result
        self.assertTrue(self.analyze(corrupt)['global_errors'])

    def test_wrong_terminal_or_missing_full_marker_no_intervals(self):
        self.write('evidence/formal-exit.json', {**self.start, 'controller_id': 'OTHER', 'exit_code': 0})
        self.assertEqual(self.analyze()['intervals'], [])
        self.write('evidence/formal-exit.json', {**self.start, 'exit_code': 0})
        (self.root / 'results/formal/COMPLETED.json').unlink()
        self.assertEqual(self.analyze()['intervals'], [])

    def test_analysis_uses_frozen_capture_booking_file(self):
        self.write('evidence/BOOKING_VERIFIED.json', {'booking': {'user': 'OTHER', 'end_ms': 0}})
        self.assertTrue(self.analyze()['complete'])
        path = self.root/'evidence/formal-final-booking-state.json'
        receipt = analyzer.read(path);receipt['booking']['user'] = 'OTHER'
        path.write_text(json.dumps(receipt))
        result = self.analyze()
        self.assertFalse(result['complete'])
        self.assertTrue(result['global_errors'])
        self.assertEqual(result['intervals'], [])

    def test_bindings_refuse_changed_bytes_or_escape(self):
        path = self.root / 'evidence/test.txt'
        path.write_bytes(b'CPU-fixture')
        row = {'path': 'evidence/test.txt', 'bytes': path.stat().st_size,
               'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        analyzer.verify_rows(self.root, [row])
        path.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            analyzer.verify_rows(self.root, [row])
        for name in ('../escape', '/outside', 'D:/outside', 'a\\b'):
            with self.assertRaises(ValueError):
                analyzer.member(self.root, name)

    def test_removed_consumer_bindings_are_rejected(self):
        original = analyzer.read(self.parent.parent / 'evidence/G3_MODEL_FORMAL_CONSUMER.json')
        for bindings in ([], original['bound_files'][:-1]):
            changed = {**original, 'bound_files': bindings}
            self.write('evidence/G3_MODEL_FORMAL_CONSUMER.json', changed)
            with self.assertRaisesRegex(ValueError, 'consumer original changed'):
                analyzer.verify_consumer(self.root)

    def test_MPS_identity_closure_and_wrong_server_GPU(self):
        original = {'passed': True, 'clients': [
            {'pid': 101, 'server_pid': 100, 'device_partial_uuid': 'GPU-79214c80-7778-37d9'},
            {'pid': 102, 'server_pid': 100, 'device_partial_uuid': 'GPU-79214c80-7778-37d9'}],
            'physical_gpu_processes': [{'pid': pid, 'uuid': analyzer.UUID, 'private_mps_server': pid == 100}
                                       for pid in (100, 101, 102)]}
        for suffix in ('before', 'after'):
            self.write('mps-' + suffix + '.json', original)
        self.assertEqual(analyzer.mps_identity(self.root, {101, 102}), {100, 101, 102})
        corruptions = []
        bad = copy.deepcopy(original); bad['clients'][0]['server_pid'] = 999; corruptions.append(bad)
        bad = copy.deepcopy(original); bad['clients'][0]['device_partial_uuid'] = 'GPU-WRONG'; corruptions.append(bad)
        bad = copy.deepcopy(original); bad['physical_gpu_processes'][0]['uuid'] = 'GPU-WRONG'; corruptions.append(bad)
        bad = copy.deepcopy(original); bad['physical_gpu_processes'][0]['pid'] = 999; corruptions.append(bad)
        for changed in corruptions:
            self.write('mps-after.json', changed)
            with self.assertRaises(ValueError):
                analyzer.mps_identity(self.root, {101, 102})

    def test_memory_rejects_other_cell_PID_duplicates_and_illegal_bytes(self):
        original = {'perf_counter': 10, 'gpus': [{'device': 4, 'foreign_compute_pids': [],
            'physical_used_bytes': 1000, 'owned_processes': [{'pid': 101, 'used_bytes': 100}],
            'owned_process_sum_bytes': 100}]}
        self.assertEqual(analyzer.memory_peak([original], 9, 11, {100, 101, 102}), 100)
        corruptions = []
        bad = copy.deepcopy(original); bad['gpus'][0]['owned_processes'][0]['pid'] = 999; corruptions.append(bad)
        bad = copy.deepcopy(original); bad['gpus'][0]['owned_processes'] *= 2; bad['gpus'][0]['owned_process_sum_bytes'] = 200; corruptions.append(bad)
        for value in (-1, None, True, 1.5, 1001):
            bad = copy.deepcopy(original); bad['gpus'][0]['owned_processes'][0]['used_bytes'] = value; corruptions.append(bad)
        for changed in corruptions:
            with self.assertRaises(ValueError):
                analyzer.memory_peak([changed], 9, 11, {100, 101, 102})

    def test_RGB_boundary_rejects_changed_pixels_manifest_or_API(self):
        path = 'results/preflight-models-attempt1/cold-baseline-space/rgb-before.json'
        reference = analyzer.read(self.parent.parent / path)
        (self.root / Path(path).parent).mkdir(parents=True)
        self.write(path, reference)
        (self.root / 'dataset').mkdir()
        (self.root / 'dataset/manifest.json').write_bytes((self.parent.parent / 'dataset/manifest.json').read_bytes())
        boundary = copy.deepcopy(reference)
        boundary['records'][0]['pid'] = 123
        for suffix in ('before', 'after'):
            self.write('rgb-' + suffix + '.json', boundary)
        analyzer.rgb_identity(self.root, self.root, 123)
        corruptions = []
        bad = copy.deepcopy(boundary); bad['records'][0]['images'][0]['rgb_sha256'] = '0' * 64; corruptions.append(bad)
        bad = copy.deepcopy(boundary); bad['records'][0]['pid'] = 999; corruptions.append(bad)
        bad = copy.deepcopy(boundary); bad['records'][0]['manifest_sha256'] = '0' * 64; corruptions.append(bad)
        for changed in corruptions:
            self.write('rgb-after.json', changed)
            with self.assertRaises(ValueError):
                analyzer.rgb_identity(self.root, self.root, 123)


if __name__ == '__main__':
    unittest.main()
