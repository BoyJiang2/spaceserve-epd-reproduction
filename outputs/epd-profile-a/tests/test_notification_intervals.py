"""CPU regression checks for additive time partitions and same-step alignment."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from notification_intervals import match_request, partition


class IntervalRules(unittest.TestCase):
    def test_overlap_partition_is_additive_without_double_counting(self):
        parts = partition(0, 100, [(10, 60), (30, 70)], [(50, 90)])
        self.assertEqual(parts['recorded_cuda_union_ms'], 60 / 1e6)
        self.assertEqual(parts['api_disconnect_union_ms'], 40 / 1e6)
        self.assertEqual(parts['api_disconnect_outside_cuda_ms'], 20 / 1e6)
        self.assertEqual(parts['unexplained_ms'], 20 / 1e6)
        self.assertAlmostEqual(parts['duration_ms'], sum(parts[key] for key in
                              ['recorded_cuda_union_ms', 'api_disconnect_outside_cuda_ms', 'unexplained_ms']))

    def fixture(self):
        steps, events = [], []
        for token in range(1, 129):
            begin = token * 1000
            events.append({'time': begin + 800, 'token': token, 'api_stamp': (begin + 790) / 1e9})
            steps.append({'begin': begin, 'end': begin + 600, 'gpu': [[begin + 100, begin + 500]],
                          'kernel_count': 1, 'stage': 'P' if token == 1 else 'D',
                          'label': {'pid': 7, 'request_ids': ['a']}})
        trace = {'outputs': {'a': events}, 'workers': steps, 'capture': [0, 200000],
                 'all_gpu': [interval for step in steps for interval in step['gpu']],
                 'disconnect': {'a': []}, 'copies': []}
        row = {'index': 84, 'response': {'repro_request_id': 'a', 'timestamps': [event['api_stamp'] for event in events]}}
        return row, trace

    def test_full_request_order_and_handoff_coverage(self):
        row, trace = self.fixture()
        records, reason = match_request(row, trace, True)
        self.assertIsNone(reason)
        self.assertEqual(len(records), 127)
        self.assertEqual(records[0]['categories'], ['first_to_second_notification'])
        self.assertEqual(records[1]['categories'], ['steady_decode'])
        self.assertEqual(records[-1]['to_token'], 128)

    def test_handoff_includes_copy_before_first_notification(self):
        row, trace = self.fixture()
        copy = {'interval': [1550, 1650], 'stage': 'migrate_blocks_context', 'bytes': 8}
        trace['copies'].append(copy)
        records, reason = match_request(row, trace, True)
        self.assertIsNone(reason)
        self.assertEqual(records[0]['window_ns'][0], 1800)
        self.assertEqual(records[0]['P_to_first_D']['migration_copies'], [copy])

    def test_cpu_prefill_overlap_without_cuda_not_counted(self):
        row, trace = self.fixture()
        for number, worker in enumerate(trace['workers']):
            worker['stage'] = 'baseline.prefill' if number == 0 else 'baseline.decode'
            worker['label'] = {'pid': 7, 'ids': ['a']}
        other = {'begin': 1600, 'end': 2900, 'gpu': [[1650, 1750]], 'kernel_count': 1,
                 'stage': 'baseline.prefill', 'label': {'pid': 7, 'ids': ['other']}}
        trace['workers'].append(other)
        records, reason = match_request(row, trace, False)
        self.assertIsNone(reason)
        self.assertEqual(records[0]['cpu_prefill_candidate_batch_ids'], [['other']])
        self.assertNotIn('baseline_other_request_prefill', records[0]['categories'])
        other['gpu'] = [[2100, 2200]]
        records, _ = match_request(row, trace, False)
        self.assertIn('baseline_other_request_prefill', records[0]['categories'])
        other['end'] = 1750
        records, _ = match_request(row, trace, False)
        self.assertEqual(records[0]['cpu_prefill_candidate_batch_ids'], [])
        self.assertIn('baseline_other_request_prefill', records[0]['categories'])

    def test_wrong_stage_and_late_gpu_not_silently_matched(self):
        row, trace = self.fixture()
        trace['workers'][1]['stage'] = 'P'
        self.assertEqual(match_request(row, trace, True)[1], 'worker stage sequence differs')
        row, trace = self.fixture()
        trace['workers'][1]['gpu'][0][1] = trace['outputs']['a'][1]['time'] + 1
        self.assertEqual(match_request(row, trace, True)[1], 'worker/GPU completion after output marker')


if __name__ == '__main__':
    unittest.main()
