"""CPU-only OS mocks: never change the test runner's real affinity."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cpu_placement as placement


class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.config = {'workload_cpu_affinity': [0, 1, 2, 3], 'workload_numa_node': 0,
                       'gpu_uuids': ['GPU-test']}

    def test_legacy_and_cpu_actions_do_not_set(self):
        with patch.object(placement.os, 'sched_setaffinity', create=True) as setting:
            self.assertFalse(placement.apply({}, 'formal'))
            for action in ('cpu', 'prepare', 'plan', 'analyze'):
                self.assertFalse(placement.apply(self.config, action))
            setting.assert_not_called()

    def test_bad_config_before_os_mutation(self):
        for cpus in ([], [True], [-1], [0, 0], [1, 0], [65536], '0-3', None):
            with self.subTest(cpus=cpus), patch.object(placement.os, 'sched_setaffinity', create=True) as setting:
                with self.assertRaises(ValueError):
                    placement.apply({**self.config, 'workload_cpu_affinity': cpus}, 'formal')
                setting.assert_not_called()
        for node in (True, -1, None, '0'):
            with self.assertRaises(ValueError):
                placement.expected({**self.config, 'workload_numa_node': node})

    def apply_mock(self, *, node='0', node_cpus='0-3', online='0-3', actual=None):
        def read(path):
            if path.name == 'cpulist': return node_cpus
            if path.name == 'online': return online
            if path.name == 'numa_node': return node
            raise AssertionError(path)
        with patch.object(Path, 'read_text', read), patch.object(placement.subprocess, 'check_output', return_value='GPU-test, 00000000:01:00.0\n'), patch.object(placement.os, 'sched_setaffinity', create=True) as setting, patch.object(placement.os, 'sched_getaffinity', return_value={0, 1, 2, 3} if actual is None else actual, create=True):
            result = placement.apply(self.config, 'formal')
            setting.assert_called_once_with(0, {0, 1, 2, 3})
            return result

    def test_apply_exact_same_node_and_readback(self):
        self.assertTrue(self.apply_mock())

    def test_wrong_node_or_cpu_or_readback_refused(self):
        for kwargs in ({'node': '1'}, {'node': '-1'}, {'node_cpus': '0-7'}, {'online': '0-2'}, {'actual': {0}}):
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, RuntimeError)):
                self.apply_mock(**kwargs)

    def test_cpu_list_parser(self):
        self.assertEqual(placement.cpu_list('0-2,4'), {0, 1, 2, 4})
        for value in ('', '-1', '2-1', '0,0', '0-2,2-3', 'True', '0-99999999'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                placement.cpu_list(value)

    def test_actual_main_exact_threads_subset(self):
        record = {'main_affinity': [0, 1, 2, 3], 'thread_count': 2,
                  'thread_affinity': {'10': [0, 1, 2, 3], '11': [1]}}
        placement.validate(record, self.config)
        placement.validate(None, {})
        for change in ({'main_affinity': [0]}, {'thread_count': 3},
                       {'thread_affinity': {}}, {'thread_affinity': {'10': [4], '11': [1]}},
                       {'thread_affinity': {'10': [], '11': [1]}}):
            bad = copy.deepcopy(record)
            bad.update(change)
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                placement.validate(bad, self.config)

    def test_snapshot_identity_and_threads(self):
        fields = ['S'] + ['0'] * 49
        fields[16], fields[19] = '10', '1234'
        stat = '42 (worker name) ' + ' '.join(fields)
        with patch.object(Path, 'read_text', return_value=stat), patch.object(Path, 'read_bytes', return_value=b'OMP_NUM_THREADS=4\0SECRET=hidden\0'), patch.object(Path, 'iterdir', return_value=iter([Path('/proc/42/task/42'), Path('/proc/42/task/43')])), patch.object(Path, 'stat') as info, patch.object(placement.os, 'sched_getaffinity', return_value={0, 1, 2, 3}, create=True):
            info.return_value.st_uid = 2147
            record = placement.snapshot(42)
            self.assertEqual((record['start_ticks'], record['nice'], record['uid']), (1234, 10, 2147))
            self.assertEqual(record['thread_count'], 2)
            self.assertEqual(record['environment']['OMP_NUM_THREADS'], '4')
            self.assertNotIn('SECRET', record['environment'])
            placement.validate(record, self.config)

    def test_snapshot_pid_reuse_refused(self):
        before = ['S'] + ['0'] * 49
        after = before.copy()
        after[19] = '1'
        with patch.object(Path, 'read_text', side_effect=['42 (w) ' + ' '.join(before), '42 (w) ' + ' '.join(after)]), patch.object(Path, 'read_bytes', return_value=b''), patch.object(Path, 'iterdir', return_value=iter([Path('/proc/42/task/42')])), patch.object(Path, 'stat') as info, patch.object(placement.os, 'sched_getaffinity', return_value={0}, create=True):
            info.return_value.st_uid = 2147
            with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                placement.snapshot(42)

    def test_entry_frozen_helper_and_tamper_refusal(self):
        entry_path = Path(__file__).resolve().parents[1]/'entry.py'
        if not entry_path.exists():
            entry_path = Path(__file__).with_name('project_entry.py')
        spec = importlib.util.spec_from_file_location('cpu_placement_entry_test', entry_path)
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        for tamper in (None, 'helper', 'manifest'):
            with self.subTest(tamper=tamper), tempfile.TemporaryDirectory(prefix='cpu-placement-test-', dir=Path(__file__).resolve().parent) as directory:
                root = Path(directory)
                for name in ('configs', 'evidence', 'scripts'):
                    (root/name).mkdir()
                config = {**self.config, 'source_commit': 'a'*40}
                helper = root/'scripts/cpu_placement.py'
                helper.write_bytes(b"def apply(config, action):\n    raise RuntimeError('reviewed_profile_called')\n")
                manifest = root/'configs/runtime-extension-source-manifest.json'
                manifest.write_text(json.dumps([{'path': 'scripts/cpu_placement.py', 'sha256': hashlib.sha256(helper.read_bytes()).hexdigest()}]))
                config['source_manifest_sha256'] = hashlib.sha256(manifest.read_bytes()).hexdigest()
                (root/'evidence/GIT_DEPLOYED.json').write_text(json.dumps({'commit': config['source_commit'], 'source_manifest_sha256': config['source_manifest_sha256']}))
                frozen = root/'configs/project.json'
                frozen.write_text(json.dumps(config))
                if tamper == 'helper': helper.write_bytes(b"raise AssertionError('unreviewed code executed')\n")
                if tamper == 'manifest': manifest.write_bytes(b'[]')
                layout = SimpleNamespace(config=config, run_root=root, require_scope=lambda action: None)
                with patch.dict(entry.os.environ), patch.object(entry.ProjectLayout, 'read', return_value=layout), patch.object(sys, 'argv', ['entry', 'formal', '--config', str(frozen)]), patch.object(entry.os, 'execve') as execute, patch.object(entry.os, 'chdir') as change:
                    if tamper:
                        with self.assertRaises(ValueError): entry.main()
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'reviewed_profile_called'): entry.main()
                    execute.assert_not_called()
                    change.assert_not_called()


if __name__ == '__main__':
    unittest.main()
