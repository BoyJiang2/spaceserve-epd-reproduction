import datetime
import unittest
from booking_window import START_MS, validate


def receipt():
    return {'verified_at_utc': datetime.datetime.fromtimestamp(START_MS / 1000, datetime.timezone.utc).isoformat(),
            'resource': {'id': 'h20/qjh000', 'active': True}, 'read_only': True,
            'booking': {'id': 'example', 'resource_id': 'h20/qjh000', 'node': 'qjh000', 'user': 'boyjiang', 'kind': 'gpu',
                        'start_ms': START_MS, 'end_ms': START_MS + 11 * 3600000}}


class BookingWindowTests(unittest.TestCase):
    def test_no_early_use_and_current_api_end(self):
        with self.assertRaises(RuntimeError): validate(receipt(), START_MS - 1, True)
        self.assertEqual(validate(receipt(), START_MS, True), 11 * 3600 - 120)

    def test_stale_phase_entry_needs_refresh_but_running_phase_keeps_deadline(self):
        with self.assertRaises(RuntimeError): validate(receipt(), START_MS + 301000, True)
        self.assertGreater(validate(receipt(), START_MS + 301000, False), 0)

    def test_cleanup_reserve_and_wrong_identity(self):
        with self.assertRaises(RuntimeError): validate(receipt(), START_MS + 11 * 3600000 - 120000, False)
        for key, value in [('kind', 'cpu'), ('user', 'other'), ('node', 'qjh003')]:
            changed = receipt()
            changed['booking'][key] = value
            with self.assertRaises(RuntimeError): validate(changed, START_MS, True)

    def test_pre_start_snapshot_is_not_runtime_authorization(self):
        changed = receipt()
        changed['verified_at_utc'] = datetime.datetime.fromtimestamp((START_MS - 1000) / 1000, datetime.timezone.utc).isoformat()
        with self.assertRaises(RuntimeError): validate(changed, START_MS, True)


if __name__ == '__main__':
    unittest.main()
