"""Small CPU checks for the temporal-union and stage-attribution rules."""
from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from trace_analysis import activity_summary, inspect_trace, merge, stage


class TraceRules(unittest.TestCase):
    def test_union_does_not_double_count_overlapping_kernels(self):
        self.assertEqual(merge([(20, 40), (0, 30), (45, 50)]), [[0, 40], [45, 50]])
        self.assertEqual(activity_summary([(0, 30), (20, 40)])['kernel_union_ms'], .00004)

    def test_nonpositive_and_empty_intervals_rejected(self):
        with self.assertRaises(RuntimeError):
            merge([(3, 3)])
        with self.assertRaises(RuntimeError):
            activity_summary([])

    def test_baseline_prefill_includes_vision_not_separate_E(self):
        self.assertEqual(stage({'name': 'baseline.execute_model', 'prompt': [True, True]}), 'baseline.prefill')
        with self.assertRaises(RuntimeError):
            stage({'name': 'baseline.execute_model', 'prompt': [False, True]})
        self.assertEqual(stage({'name': 'step_llm', 'stage': 'context'}), 'P')
        with self.assertRaises(RuntimeError):
            stage({'name': 'step_llm', 'stage': 'unknown'})

    def test_sqlite_process_identity_and_async_gpu_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'fixture.sqlite'
            connection = sqlite3.connect(path)
            connection.executescript('''
                create table StringIds(id integer,value text);
                create table NVTX_EVENTS(start integer,end integer,globalTid integer,text text,textId integer);
                create table CUPTI_ACTIVITY_KIND_RUNTIME(start integer,end integer,globalTid integer,correlationId integer);
                create table CUPTI_ACTIVITY_KIND_KERNEL(start integer,end integer,globalPid integer,correlationId integer,deviceId integer);
                create table CUPTI_ACTIVITY_KIND_MEMCPY(start integer,end integer,globalPid integer,correlationId integer,bytes integer);
            ''')
            def event(begin, end, thread, label):
                text = label if isinstance(label, str) else json.dumps({'perf_ns': begin + 1000000, **label})
                connection.execute('insert into NVTX_EVENTS values(?,?,?,?,null)', (begin, end, thread, text))
            event(0, 1000, 900 << 24, 'repro_capture')
            event(1, None, 900 << 24, {'name': 'capture.anchor', 'pid': 900})
            for pid, rid in [(101, 'selected'), (102, 'other-process')]:
                thread = (pid << 24) | 7
                for correlation, begin, prompt in [(1, 10, True), (2, 40, False)]:
                    event(begin, begin + 10, thread, {'name': 'baseline.execute_model', 'pid': pid, 'ids': [rid], 'prompt': [prompt]})
                    connection.execute('insert into CUPTI_ACTIVITY_KIND_RUNTIME values(?,?,?,?)', (begin + 2, begin + 3, thread, correlation))
                    # GPU finishes after its CPU launch range, which is valid async execution.
                    connection.execute('insert into CUPTI_ACTIVITY_KIND_KERNEL values(?,?,?,?,0)', (begin + 3, begin + 20, pid << 24, correlation))
            stamps = [1 + number / 100 for number in range(128)]
            for token, stamp in enumerate(stamps, 1):
                event(100 + token, None, 900 << 24, {'name': 'api.output', 'pid': 900, 'rid': 'selected', 'token': token, 'api_stamp': stamp})
            connection.commit()
            connection.close()
            result = inspect_trace(path, [{'index': 84, 'endpoint': 'local', 'response': {'repro_request_id': 'selected', 'timestamps': stamps}}])
            stages = result['selected_requests'][0]['stages']
            self.assertEqual(stages['baseline.prefill']['kernels'], 1)
            self.assertEqual(stages['baseline.prefill']['last_ns'], 30)
            self.assertEqual(stages['baseline.decode']['kernels'], 1)
            self.assertEqual(stages['baseline.decode']['last_ns'], 60)


if __name__ == '__main__':
    unittest.main()
