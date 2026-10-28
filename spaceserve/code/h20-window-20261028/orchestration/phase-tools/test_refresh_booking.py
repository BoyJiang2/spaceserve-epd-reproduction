"""Synthetic booking state only; no network or local live receipt writes."""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import refresh_booking as refresh


class BookingTests(unittest.TestCase):
    def test_atomic_local_refresh_and_link_ancestor_refused(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory); (root/'evidence').mkdir()
            target = root/'evidence/BOOKING_VERIFIED.json'
            target.write_text('previous local status')
            response = types.SimpleNamespace(stdout=json.dumps(self.snapshot()))
            with patch.object(refresh, 'BATCH', root), patch.object(refresh.subprocess, 'run', return_value=response), \
                 patch.object(refresh.time, 'time', return_value=(refresh.START+1000)/1000), \
                 contextlib.redirect_stdout(io.StringIO()):
                refresh.main()
                self.assertEqual(json.loads(target.read_text())['booking']['id'], refresh.BOOKING_ID)
                before = target.read_bytes()
                with patch.object(Path, 'is_symlink', lambda p: p == root/'evidence'):
                    with self.assertRaisesRegex(RuntimeError, 'symlink/junction'):
                        refresh.main()
                self.assertEqual(target.read_bytes(), before)
                self.assertFalse((root/'evidence/.booking-update.tmp').exists())

    def snapshot(self):
        return {'bookings': [{'id': refresh.BOOKING_ID, 'resource_id': 'h20/qjh000',
                'node': 'qjh000', 'user': 'boyjiang', 'kind': 'gpu',
                'start_ms': refresh.START, 'end_ms': refresh.END, 'purpose': 'not needed'}],
                'resources': [{'id': 'h20/qjh000', 'node': 'qjh000', 'active': True, 'gpu_count': 8}]}

    def test_active_exact_and_unneeded_fields_omitted(self):
        result = refresh.select_booking(self.snapshot(), refresh.START+1000)
        self.assertEqual(result['booking']['id'], refresh.BOOKING_ID)
        self.assertNotIn('purpose', result['booking'])
        self.assertTrue(result['read_only'])

    def test_before_expired_foreign_duplicate_and_inactive_refused(self):
        for now in (refresh.START-1, refresh.END):
            with self.assertRaises(RuntimeError): refresh.select_booking(self.snapshot(), now)
        for key, value in [('id', 'OLD'), ('kind', 'cpu'), ('user', 'OTHER'),
                           ('start_ms', refresh.START-1), ('end_ms', refresh.END+1)]:
            state = self.snapshot();state['bookings'][0][key] = value
            with self.assertRaises(RuntimeError): refresh.select_booking(state, refresh.START+1000)
        state = self.snapshot();state['bookings'].append(copy.deepcopy(state['bookings'][0]))
        with self.assertRaises(RuntimeError): refresh.select_booking(state, refresh.START+1000)

    def test_window_without_extension_ignores_other_records_and_fails_closed(self):
        state=self.snapshot()
        other=dict(state['bookings'][0],id='bk-20261028T0000-ffffffff',
                   start_ms=refresh.END,end_ms=refresh.END+3600000)
        state['bookings'].append(other)
        result=refresh.select_booking(state,refresh.START+1000)
        self.assertNotIn('extension',result)
        self.assertEqual(result['authorized_effective_end_ms'],refresh.END)
        with self.assertRaises(RuntimeError): refresh.select_booking(state,refresh.END+1000)
        state = self.snapshot();state['resources'][0]['active'] = False
        with self.assertRaises(RuntimeError): refresh.select_booking(state, refresh.START+1000)


if __name__ == '__main__':
    unittest.main()
