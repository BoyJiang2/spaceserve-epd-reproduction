"""Bound raw-file handoff tests, with no booking API calls or credentials."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import selected_booking


class SelectedBookingTests(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ['EPD_CPU_TEST_TMP']).resolve(strict=True)
        self.temp = tempfile.TemporaryDirectory(prefix='selected-booking-cpu-', dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name).resolve()
        self.owner = self.output / 'inputs.json'
        self.raw = {'observed_ms': 1234, 'origin': 'CPU-fixture-raw-API', 'bookings': []}
        self.raw_path = self.output / 'booking.json'
        self.raw_path.write_text(json.dumps(self.raw))
        self.sha = hashlib.sha256(self.raw_path.read_bytes()).hexdigest()
        self.inputs = {'run_id': 'fixture-unit', 'booking_file': self.raw_path.name, 'booking_sha256': self.sha}
        self.claim = types.SimpleNamespace(deadline=time.perf_counter() + 1600,
            check=Mock(), reservation_receipt={'claim_sha256': 'c' * 64})
        self.config = {'cleanup_seconds': 120}
        self.event = threading.Event()

    def handoff(self, **changes):
        body = {'schema': 'epd-restart-booking-handoff-v1', 'run_id': 'fixture-unit',
                'claim_sha256': 'c' * 64, 'raw': {'path': self.raw_path.name, 'sha256': self.sha}}
        body.update(changes)
        (self.output / 'restart-booking-handoff.json').write_text(json.dumps(body))

    def read(self, name='restart'):
        return selected_booking.for_session(name, self.config, self.inputs, self.owner,
                                            self.claim, self.output, self.event)

    def test_cold_uses_original_bound_booking_without_restamping(self):
        self.assertEqual(self.read('cold'), self.raw)
        self.assertFalse((self.output / 'restart-booking-request.json').exists())

    def test_restart_keeps_original_raw_and_claim_bound_request(self):
        self.handoff()
        self.assertEqual(self.read(), self.raw)
        request = json.loads((self.output / 'restart-booking-request.json').read_bytes())
        self.assertEqual(request['claim_sha256'], 'c' * 64)
        self.assertLessEqual(request['deadline_monotonic'], self.claim.deadline - 120)
        self.assertEqual(hashlib.sha256(self.raw_path.read_bytes()).hexdigest(), self.sha)

    def test_wrong_claim_handoff_rejected(self):
        self.handoff(claim_sha256='d' * 64)
        with self.assertRaises(ValueError):
            self.read()

    def test_other_run_handoff_rejected(self):
        self.handoff(run_id='another-unit')
        with self.assertRaises(ValueError):
            self.read()

    def test_raw_hash_mismatch_rejected(self):
        self.handoff()
        self.raw_path.write_text('{}')
        with self.assertRaises(ValueError):
            self.read()

    def test_escape_path_rejected(self):
        self.handoff(raw={'path': '../outside.json', 'sha256': self.sha})
        with self.assertRaises(ValueError):
            self.read()

    def test_cancellation_stops_missing_handoff_wait(self):
        self.event.set()
        with self.assertRaises(TimeoutError):
            self.read()
        self.claim.check.assert_called_once()

    def test_missing_handoff_wait_is_bounded(self):
        with patch.object(selected_booking.time, 'perf_counter', side_effect=[1, 1, 62]):
            with self.assertRaises(TimeoutError):
                self.read()

    def test_request_is_not_reused_or_overwritten(self):
        self.handoff()
        self.read()
        with self.assertRaises(FileExistsError):
            self.read()

    def test_unknown_session_rejected(self):
        with self.assertRaises(ValueError):
            self.read('third')


if __name__ == '__main__':
    unittest.main()
