import ast
import collections
import copy
import enum
import hashlib
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from analyze import measure, output_overlap, stats
import analyze


def fixture():
    events = [('issued', 1), ('preprocessed', 2), ('encoding_begin', 3), ('encoding_end', 4),
              ('encoding_migration_begin', 5), ('encoding_migration_end', 6), ('context_begin', 7), ('context_end', 8),
              ('migration_begin', 10.5), ('migration_end', 11), ('decoding_begin', 137.5), ('decoding_end', 138)]
    return {'success': True, 'output_tokens': 128, 'submission_perf_counter': 0,
            'latency_s': 140, 'ttft_s': 10, 'tpot_s': 128 / 127,
            'response': {'timestamps': [10] + list(range(12, 139)),
                         'lifetime_events': [{'event_type': name, 'timestamp': stamp} for name, stamp in events]}}


class AnalysisTests(unittest.TestCase):
    def test_first_gap_partition_and_observation_windows(self):
        values, gaps, _ = measure(fixture())
        self.assertEqual(len(gaps), 127)
        self.assertEqual(values['first_gap_ms'], 2000)
        self.assertEqual(values['later_gap_mean_ms'], 1000)
        self.assertEqual(values['decode_window_ms'], 128000)
        self.assertEqual(sum(values[f'ttft_part_{i}_ms'] for i in range(9)), 10000)
        self.assertEqual(values['reported_decode_ms'], 500)
        self.assertEqual(values['decode_begin_minus_last_api_stamp_ms'], -500)

    def test_invalid_timestamps_rejected(self):
        for value in (float('nan'), 9):
            row = fixture()
            row['response']['timestamps'][1] = value
            with self.assertRaises(AssertionError):
                measure(row)

    def test_nonmonotone_stage_partition_not_fabricated(self):
        row = fixture()
        row['response']['lifetime_events'][0]['timestamp'] = 2.5
        values, _, _ = measure(row)
        self.assertFalse(values['ttft_partition_valid'])
        self.assertNotIn('ttft_part_0_ms', values)

    def test_baseline_without_events_and_quantiles(self):
        row = fixture()
        row['response']['lifetime_events'] = []
        values, _, _ = measure(row)
        self.assertNotIn('reported_decode_ms', values)
        self.assertEqual(stats([0, 10, 20])['p95'], 19)

    def test_coalesced_edge_and_half_open_overlap(self):
        self.assertEqual(output_overlap([10, 15], [20, 25], 16, 18), 2)
        self.assertEqual(output_overlap([10, 15], [20, 25], 21, 23), 1)
        self.assertEqual(output_overlap([10], [20], 20, 20), 0)

    def test_boolean_counts_and_optimized_execution_guard(self):
        self.assertEqual(stats([True, False, True]), {'n': 3, 'n_true': 2, 'fraction_true': 2 / 3})
        result = subprocess.run([sys.executable, '-O', str(ROOT / 'scripts/analyze.py'), 'unused-source', 'unused-output'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Run without -O', result.stderr)

    def test_output_ancestor_guard_before_reading_source(self):
        with self.assertRaisesRegex(AssertionError, 'cannot contain frozen source'):
            analyze.run(ROOT / 'not-a-source', ROOT)

    def test_rehashed_directory_is_rejected_against_pinned_zip(self):
        scratch = ROOT.parents[1] / 'work'
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            parent = pathlib.Path(temporary)
            frozen = parent / 'reproduction'
            frozen.mkdir()
            empty = hashlib.sha256(b'').hexdigest()
            entries = []
            for index in range(969):
                name = f'f{index:04d}.txt'
                (frozen / name).write_bytes(b'')
                entries.append(empty + '  ' + name)
            manifest = '\n'.join(entries) + '\n'
            (frozen / 'SHA256SUMS').write_text(manifest, encoding='utf-8')
            archive = parent / 'reproduction-h20.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr('reproduction/SHA256SUMS', (frozen / 'SHA256SUMS').read_bytes())
            with mock.patch.object(analyze, 'ARCHIVE_SHA256', analyze.digest(archive)):
                self.assertEqual(analyze.freeze_snapshot(frozen)['files_verified'], 969)
                (frozen / 'f0000.txt').write_bytes(b'changed')
                entries[0] = hashlib.sha256(b'changed').hexdigest() + '  f0000.txt'
                (frozen / 'SHA256SUMS').write_text('\n'.join(entries) + '\n', encoding='utf-8')
                with self.assertRaisesRegex(AssertionError, 'manifest differs from pinned archive'):
                    analyze.freeze_snapshot(frozen)

    def test_actual_source_enum_string_guard_overwrites(self):
        tree = ast.parse((ROOT / 'source/epdserve/orchestrator.py').read_text(encoding='utf-8'))
        owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and any(getattr(item, 'name', '') == '_on_new_lifetime_event_callback' for item in node.body))
        node = copy.deepcopy(next(item for item in owner.body if getattr(item, 'name', '') == '_on_new_lifetime_event_callback'))
        for argument in node.args.args:
            argument.annotation = None
        node.returns = None
        module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
        namespace = {}
        exec(compile(module, '<isolated_actual_event_callback>', 'exec'), namespace)
        state = types.SimpleNamespace(request_lifetime_events=collections.defaultdict(dict))
        event_type = enum.Enum('EventType', {'DecodingBegin': 'decoding_begin'})
        callback = namespace['_on_new_lifetime_event_callback']
        for stamp in (1, 2):
            callback(state, 0, types.SimpleNamespace(event_type=event_type.DecodingBegin, timestamp=stamp), True)
        self.assertEqual(len(state.request_lifetime_events[0]), 1)
        self.assertEqual(state.request_lifetime_events[0]['decoding_begin'].timestamp, 2)


if __name__ == '__main__':
    unittest.main()
