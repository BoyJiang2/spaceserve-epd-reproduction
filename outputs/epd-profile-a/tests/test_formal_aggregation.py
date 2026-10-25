"""Reject wrong timing, GPU budget and capture state using actual archived formal records."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('aggregate', root / 'analysis/aggregate.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class AggregationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        case = root / 'results/formal/on-epd-images4-c8'
        cls.rows = [json.loads(line) for line in (case / 'measurement/requests.jsonl').read_text().splitlines()]
        cls.summaries = json.loads((case / 'measurement/summary.json').read_text())
        cls.runtime = json.loads((case / 'runtime.json').read_text())
        cls.controls = json.loads((case / 'measurement/capture-control.json').read_text())
        cls.api = {item['url']: item['pid'] for item in json.loads((case / 'rgb-before.json').read_text())['records']}
        cls.selected = [row for row in cls.rows if not row['warmup'] and row['repetition'] == 2 and row['index'] >= 84]

    def test_actual_timing_runtime_control_id_records_pass(self):
        analysis.validate_runtime(self.runtime)
        for repetition in range(3):
            analysis.validate_interval(self.summaries[repetition], [row for row in self.rows if not row['warmup'] and row['repetition'] == repetition], repetition)
        analysis.validate_request_ids(self.rows, set(self.api))
        analysis.validate_controls(self.controls, list(self.api), self.api, self.summaries, self.selected)

    def test_self_consistent_but_shifted_summary_is_rejected(self):
        summary = copy.deepcopy(self.summaries[0])
        summary['start_perf_counter'] += 5
        summary['end_perf_counter'] += 5
        with self.assertRaisesRegex(RuntimeError, 'outside repetition'):
            analysis.validate_interval(summary, [row for row in self.rows if not row['warmup'] and row['repetition'] == 0], 0)

    def test_duplicate_physical_gpu_is_rejected(self):
        runtime = copy.deepcopy(self.runtime)
        runtime['workers'][1]['gpu_uuid'] = runtime['workers'][0]['gpu_uuid']
        with self.assertRaisesRegex(RuntimeError, 'unique physical'):
            analysis.validate_runtime(runtime)

    def test_inactive_capture_success_response_is_rejected(self):
        controls = copy.deepcopy(self.controls)
        controls[0]['state']['capturing'] = False
        with self.assertRaisesRegex(RuntimeError, 'state/time/PID'):
            analysis.validate_controls(controls, list(self.api), self.api, self.summaries, self.selected)

    def test_duplicate_endpoint_request_identity_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[1]['response']['repro_request_id'] = rows[0]['response']['repro_request_id']
        with self.assertRaisesRegex(RuntimeError, 'duplicate response'):
            analysis.validate_request_ids(rows, set(self.api))


if __name__ == '__main__':
    unittest.main(verbosity=2)
