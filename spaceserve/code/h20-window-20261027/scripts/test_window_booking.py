"""CPU-only new booking and formal admission checks; no model/CUDA imports."""
import copy
import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import booking_window as booking
import resource_guard
from formal_guard import record_start_budget


class WindowTests(unittest.TestCase):
    def receipt(self, now):
        return {'booking': {'id': booking.BOOKING_ID, 'resource_id': 'h20/qjh000',
                'node': 'qjh000', 'user': 'boyjiang', 'kind': 'gpu',
                'start_ms': booking.START_MS, 'end_ms': booking.LATEST_END_MS},
                'resource': {'id': 'h20/qjh000', 'active': True}, 'read_only': True,
                'verified_at_utc': datetime.datetime.fromtimestamp(now/1000, datetime.timezone.utc).isoformat()}

    def test_new_window_and_old_or_wrong_receipt(self):
        now = booking.START_MS + 1000
        receipt = self.receipt(now)
        self.assertEqual(booking.validate(receipt, now, True), 4*3600-121)
        for key, value in [('id', 'OLD'), ('user', 'OTHER'), ('kind', 'cpu'),
                           ('start_ms', 1793019600000), ('end_ms', booking.LATEST_END_MS+1)]:
            changed = copy.deepcopy(receipt); changed['booking'][key] = value
            with self.assertRaises(RuntimeError): booking.validate(changed, now, True)

    def test_before_start_expiry_cleanup_and_stale(self):
        for now in (booking.START_MS-1, booking.LATEST_END_MS-120000, booking.LATEST_END_MS):
            with self.assertRaises(RuntimeError): booking.validate(self.receipt(now), now, True)
        now = booking.START_MS+400000
        with self.assertRaises(RuntimeError): booking.validate(self.receipt(now-300001), now, True)

    def test_contiguous_extension_clamps_to_user_end_and_rejects_invalid(self):
        now = booking.LATEST_END_MS + 1000
        receipt = self.receipt(now)
        receipt['extension'] = dict(receipt['booking'], id=booking.EXTENSION_ID,
            start_ms=booking.LATEST_END_MS, end_ms=booking.AUTHORIZED_EXTENDED_END_MS+3600000)
        self.assertEqual(booking.validate(receipt, now, True), 3600-121)
        for key, value in [('id','OTHER'),('user','OTHER'),('kind','cpu'),
                           ('start_ms',booking.LATEST_END_MS+1),
                           ('end_ms',booking.AUTHORIZED_EXTENDED_END_MS-1)]:
            changed=copy.deepcopy(receipt); changed['extension'][key]=value
            with self.assertRaises(RuntimeError): booking.validate(changed,now,True)
        for end in (booking.AUTHORIZED_EXTENDED_END_MS-120000,
                    booking.AUTHORIZED_EXTENDED_END_MS,
                    booking.AUTHORIZED_EXTENDED_END_MS+3600000):
            with self.assertRaises(RuntimeError): booking.validate(self.receipt(end)|{'extension':receipt['extension']},end,True)
        del receipt['extension']
        with self.assertRaises(RuntimeError): booking.validate(receipt,now,True)

    def test_numeric_archive_preserves_original_identity_without_numeric_restart(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory)
            for name in ('configs','evidence','scripts','evidence/numeric-producer/scripts'):
                (root/name).mkdir(parents=True,exist_ok=True)
            original=root/'evidence/numeric-producer/scripts/original.py'
            original.write_text('original producer')
            (root/'scripts/original.py').write_text('changed consumer')
            manifest=root/'configs/code-manifest.json'
            manifest.write_text(json.dumps([{'path':'scripts/original.py','sha256':resource_guard.sha(original)}]))
            (root/'evidence/G2_CODE_APPROVED.json').write_text(json.dumps({'passed':True,
                'code_manifest_sha256':resource_guard.sha(manifest),'boot_id':'boot',
                'gpu_uuids':['gpu'],'allowed_actions':['numeric']}))
            proc=Mock();proc.read_text.return_value='boot'
            with patch.object(resource_guard,'ROOT',root),patch.object(resource_guard,'UUIDS',['gpu']), \
                 patch.object(resource_guard,'Path',side_effect=lambda p:proc if str(p)=='/proc/sys/kernel/random/boot_id' else Path(p)):
                self.assertEqual(resource_guard.code_identity(None),resource_guard.sha(manifest))
                with self.assertRaises(RuntimeError): resource_guard.code_identity('numeric')
                original.write_text('tampered')
                with self.assertRaises(RuntimeError): resource_guard.code_identity(None)

    def test_budget_records_estimate_and_refuses_overwrite_or_insufficient(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory); (root/'evidence').mkdir()
            record_start_budget(root, 201*60)
            self.assertTrue(json.loads((root/'evidence/formal-start-budget.json').read_text())['estimated_budget_sufficient'])
            with self.assertRaises(FileExistsError): record_start_budget(root, 202*60)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory); (root/'evidence').mkdir()
            with self.assertRaisesRegex(RuntimeError, 'insufficient estimated budget'):
                record_start_budget(root, 201*60-1)
            self.assertFalse(json.loads((root/'evidence/formal-start-budget.json').read_text())['estimated_budget_sufficient'])


if __name__ == '__main__':
    unittest.main()
