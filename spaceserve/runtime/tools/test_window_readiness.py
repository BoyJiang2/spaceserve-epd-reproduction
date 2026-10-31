"""Readiness-check tests: pure file/arithmetic checks, no /proc, no GPU."""
import hashlib
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path
import os
import shutil
import uuid
_TMPROOT = Path(__file__).resolve().parent / '_test_tmp'


class _Temp:
    """Workspace-local temp dir: the host temp area is not deletable under the sandbox."""

    def __enter__(self):
        _TMPROOT.mkdir(exist_ok=True)
        self._path = str(_TMPROOT / ('t-' + uuid.uuid4().hex[:8]))
        os.makedirs(self._path)
        return self._path

    def __exit__(self, *exc):
        shutil.rmtree(self._path, ignore_errors=True)
        return False


import window_readiness


def write_gate(root, name, **state):
    evidence = Path(root) / 'evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    payload = dict(passed=True, code_manifest_sha256='a' * 64, boot_id='boot-1',
                   gpu_uuids=['GPU-1'], bound_files=[])
    payload.update(state)
    (evidence / name).write_text(json.dumps(payload))


class BookingTests(unittest.TestCase):
    def test_missing_booking_is_blocked(self):
        result = window_readiness.check_booking({'booking': None}, 1000, 5.5, 54)
        self.assertFalse(result['ok'])

    def test_expired_booking_is_blocked(self):
        project = {'booking': {'start_ms': 0, 'end_ms': 1000}}
        self.assertFalse(window_readiness.check_booking(project, 1000, 5.5, 54)['ok'])

    def test_window_shorter_than_estimate_is_blocked(self):
        project = {'booking': {'start_ms': 0, 'end_ms': 3_600_000}}
        result = window_readiness.check_booking(project, 0, 5.5, 54)
        self.assertFalse(result['ok'])
        self.assertIn('shorter', result['detail'])

    def test_window_covering_estimate_is_ready(self):
        project = {'booking': {'start_ms': 0, 'end_ms': 20_000_000}}
        result = window_readiness.check_booking(project, 0, 5.5, 54)
        self.assertTrue(result['ok'])
        self.assertGreater(result['remaining_s'], result['estimate_s'])


class GateTests(unittest.TestCase):
    def test_missing_gate(self):
        with _Temp() as root:
            self.assertFalse(window_readiness.check_gate(root, 'G2_CODE_APPROVED.json', 'a' * 64, 'boot-1', ['GPU-1'])['ok'])

    def test_gate_bound_to_other_manifest(self):
        with _Temp() as root:
            write_gate(root, 'G2_CODE_APPROVED.json', code_manifest_sha256='b' * 64)
            result = window_readiness.check_gate(root, 'G2_CODE_APPROVED.json', 'a' * 64, 'boot-1', ['GPU-1'])
            self.assertFalse(result['ok'])
            self.assertIn('manifest', result['detail'])

    def test_gate_with_changed_bound_file(self):
        with _Temp() as root:
            target = Path(root) / 'scripts/run_formal.py'
            target.parent.mkdir(parents=True)
            target.write_text('v1')
            write_gate(root, 'G2_FORMAL_CODE_APPROVED.json', bound_files=[
                dict(path='scripts/run_formal.py', sha256='0' * 64)])
            result = window_readiness.check_gate(root, 'G2_FORMAL_CODE_APPROVED.json', 'a' * 64, 'boot-1', ['GPU-1'])
            self.assertFalse(result['ok'])
            self.assertIn('bound file changed', result['detail'])

    def test_gate_with_matching_binding(self):
        with _Temp() as root:
            target = Path(root) / 'scripts/run_formal.py'
            target.parent.mkdir(parents=True)
            target.write_text('v1')
            digest = hashlib.sha256(b'v1').hexdigest()
            write_gate(root, 'G2_FORMAL_CODE_APPROVED.json', bound_files=[
                dict(path='scripts/run_formal.py', sha256=digest)])
            result = window_readiness.check_gate(root, 'G2_FORMAL_CODE_APPROVED.json', 'a' * 64, 'boot-1', ['GPU-1'])
            self.assertTrue(result['ok'], result)

    def test_formal_consumer_must_not_approve_formal_data(self):
        with _Temp() as root:
            evidence = Path(root) / 'evidence'
            evidence.mkdir(parents=True)
            (evidence / 'G3_MODEL_FORMAL_CONSUMER.json').write_text(json.dumps(
                {'scope': 'Space-model-preflight-for-formal', 'formal_data_approved': True}))
            self.assertFalse(window_readiness.check_model_consumer(root, 'a' * 64)['ok'])
            (evidence / 'G3_MODEL_FORMAL_CONSUMER.json').write_text(json.dumps(
                {'scope': 'Space-model-preflight-for-formal', 'formal_data_approved': False}))
            self.assertTrue(window_readiness.check_model_consumer(root, 'a' * 64)['ok'])


class ProducerBindingTests(unittest.TestCase):
    def fixture(self, root):
        root = Path(root)
        for name in ('configs', 'evidence/numeric-producer/scripts', 'scripts', 'build'):
            (root / name).mkdir(parents=True, exist_ok=True)
        (root / 'configs/project.json').write_text(json.dumps(dict(
            state='approved_scope', gpu_uuids=['GPU-1'],
            booking=dict(start_ms=0, end_ms=20_000_000))))
        (root / 'configs/schedule-v2.json').write_text(json.dumps(dict(
            cells=[dict(requests=100, warmup=20) for _ in range(54)])))
        for name in ('scripts/start_server.sh', 'scripts/benchmark.py', 'build/libsmctrl.so'):
            (root / name).write_bytes(b'fixture only')
        for stage, name, action in (
                ('code', 'G2_CODE_APPROVED.json', None),
                ('model-code', 'G2_MODEL_CODE_APPROVED.json', ['preflight-models']),
                ('formal-code', 'G2_FORMAL_CODE_APPROVED.json', ['formal'])):
            relative = 'scripts/' + stage + '.py'
            base = root / 'evidence/numeric-producer' if stage == 'code' else root
            (base / relative).write_bytes(stage.encode())
            rows = [dict(path=relative, sha256=window_readiness.sha(base / relative))]
            manifest = root / ('configs/' + stage + '-manifest.json')
            manifest.write_text(json.dumps(rows))
            write_gate(root, name, code_manifest_sha256=window_readiness.sha(manifest),
                       allowed_actions=action)
        target = 'scripts/model-code.py'
        write_gate(root, 'G3_MODEL_FORMAL_CONSUMER.json',
                   code_manifest_sha256=window_readiness.sha(root / 'configs/model-code-manifest.json'),
                   bound_files=[dict(path=target, sha256=window_readiness.sha(root / target))],
                   scope='Space-model-preflight-for-formal', formal_data_approved=False)
        return root

    def evaluate(self, root):
        with mock.patch.object(window_readiness.Path, 'read_text', return_value='boot-1'):
            return window_readiness.evaluate(root, now_ms=0)

    def change(self, root, relative, **values):
        path = root / relative
        state = json.loads(path.read_bytes())
        state.update(values)
        path.write_text(json.dumps(state))

    def test_distinct_producers_and_g2_without_bound_files_are_ready(self):
        with _Temp() as directory:
            root = self.fixture(directory)
            report = self.evaluate(root)
            self.assertTrue(report['ready'], report)

    def test_cross_stage_sha_is_rejected(self):
        with _Temp() as directory:
            root = self.fixture(directory)
            self.change(root, 'evidence/G2_MODEL_CODE_APPROVED.json',
                        code_manifest_sha256=window_readiness.sha(root / 'configs/formal-code-manifest.json'))
            self.assertFalse(self.evaluate(root)['ready'])

    def test_changed_numeric_archive_is_rejected(self):
        with _Temp() as directory:
            root = self.fixture(directory)
            (root / 'evidence/numeric-producer/scripts/code.py').write_bytes(b'changed')
            self.assertFalse(self.evaluate(root)['ready'])

    def test_missing_and_malformed_producer_manifest_are_findings(self):
        with _Temp() as directory:
            root = self.fixture(directory)
            path = root / 'configs/model-code-manifest.json'
            path.unlink()
            self.assertFalse(self.evaluate(root)['ready'])
            path.write_text('{')
            self.assertFalse(self.evaluate(root)['ready'])

    def test_wrong_model_and_formal_actions_are_rejected(self):
        for name in ('G2_MODEL_CODE_APPROVED.json', 'G2_FORMAL_CODE_APPROVED.json'):
            with self.subTest(name=name), _Temp() as directory:
                root = self.fixture(directory)
                self.change(root, 'evidence/' + name, allowed_actions=['numeric'])
                self.assertFalse(self.evaluate(root)['ready'])

    def test_wrong_consumer_scope_and_identity_are_rejected(self):
        for values in (dict(scope='other'), dict(boot_id='other'), dict(gpu_uuids=['GPU-other'])):
            with self.subTest(values=values), _Temp() as directory:
                root = self.fixture(directory)
                self.change(root, 'evidence/G3_MODEL_FORMAL_CONSUMER.json', **values)
                self.assertFalse(self.evaluate(root)['ready'])

    def test_bound_path_outside_root_is_rejected(self):
        with _Temp() as directory:
            root = self.fixture(directory)
            outside = Path(__file__).resolve()
            self.change(root, 'evidence/G3_MODEL_FORMAL_CONSUMER.json',
                        bound_files=[dict(path=str(outside), sha256=window_readiness.sha(outside))])
            self.assertFalse(self.evaluate(root)['ready'])

    def test_approval_and_manifest_symlinks_outside_root_are_rejected(self):
        for relative in ('evidence/G2_MODEL_CODE_APPROVED.json',
                         'configs/model-code-manifest.json'):
            with self.subTest(relative=relative), _Temp() as directory:
                root = self.fixture(Path(directory) / 'run')
                target = root / relative
                outside = Path(directory) / 'outside.json'
                outside.write_bytes(target.read_bytes())
                target.unlink()
                target.symlink_to(outside.resolve())
                self.assertFalse(self.evaluate(root)['ready'])

    def test_invalid_approval_json_and_changed_current_member_are_rejected(self):
        with _Temp() as directory:
            root = self.fixture(directory)
            (root / 'evidence/G2_FORMAL_CODE_APPROVED.json').write_text('{')
            self.assertFalse(self.evaluate(root)['ready'])
        with _Temp() as directory:
            root = self.fixture(directory)
            (root / 'scripts/formal-code.py').write_bytes(b'changed')
            self.assertFalse(self.evaluate(root)['ready'])

    def test_numeric_member_cannot_escape_archive_or_use_absolute_path(self):
        for relative in ('../../scripts/model-code.py', 'absolute', 'symlink'):
            with self.subTest(relative=relative), _Temp() as directory:
                root = self.fixture(directory)
                target = root / 'scripts/model-code.py'
                if relative == 'absolute':
                    target = root / 'evidence/numeric-producer/scripts/code.py'
                    relative = str(target.resolve())
                elif relative == 'symlink':
                    link = root / 'evidence/numeric-producer/scripts/code.py'
                    link.unlink()
                    link.symlink_to(target.resolve())
                    relative = 'scripts/code.py'
                path = root / 'configs/code-manifest.json'
                path.write_text(json.dumps([dict(path=relative, sha256=window_readiness.sha(target))]))
                self.change(root, 'evidence/G2_CODE_APPROVED.json',
                            code_manifest_sha256=window_readiness.sha(path))
                self.assertFalse(self.evaluate(root)['ready'])

    def test_project_and_schedule_symlinks_outside_root_are_rejected(self):
        for relative in ('configs/project.json', 'configs/schedule-v2.json'):
            with self.subTest(relative=relative), _Temp() as directory:
                root = self.fixture(Path(directory) / 'run')
                target = root / relative
                outside = Path(directory) / 'outside.json'
                outside.write_bytes(target.read_bytes())
                target.unlink()
                target.symlink_to(outside.resolve())
                self.assertFalse(self.evaluate(root)['ready'])

    def test_invalid_project_and_schedule_are_blocked_findings(self):
        for relative, contents in (
                ('configs/project.json', '{'), ('configs/project.json', '[]'),
                ('configs/schedule-v2.json', '{'), ('configs/schedule-v2.json', '[]'),
                ('configs/schedule-v2.json', '{"cells": null}'),
                ('configs/schedule-v2.json', '{"cells": [1]}'),
                ('configs/schedule-v2.json', '{"cells": [{"requests": "100"}]}')):
            with self.subTest(relative=relative, contents=contents), _Temp() as directory:
                root = self.fixture(directory)
                (root / relative).write_text(contents)
                report = self.evaluate(root)
                self.assertFalse(report['ready'])
                self.assertTrue(any(not item['ok'] for item in report['findings']))


if __name__ == '__main__':
    unittest.main()
