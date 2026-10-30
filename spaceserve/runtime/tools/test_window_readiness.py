"""Readiness-check tests: pure file/arithmetic checks, no /proc, no GPU."""
import hashlib
import json
import tempfile
import unittest
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


if __name__ == '__main__':
    unittest.main()
