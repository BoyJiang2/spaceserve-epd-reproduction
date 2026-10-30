"""Real local file/link ordering; directory fsync is a Linux-only mocked adapter."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numeric_cpu_receipts as receipts


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.target=self.root/'receipt.json'
        self.stack=__import__('contextlib').ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(receipts.os,'getuid',return_value=self.root.stat().st_uid,create=True))
        self.stack.enter_context(patch.object(receipts.os,'O_NOFOLLOW',0,create=True))
        self.sync=self.stack.enter_context(patch.object(receipts,'sync_directory'))

    def test_target_hidden_until_complete_file_is_fsynced_and_linked(self):
        real_fsync=os.fsync;real_link=os.link;order=[]
        def fsync(fd):
            self.assertFalse(self.target.exists());real_fsync(fd);order.append('file_fsynced')
        def link(source,target,**kwargs):
            self.assertEqual(order,['file_fsynced'])
            real_link(source,target,**kwargs)
            self.assertEqual(json.loads(self.target.read_bytes()),{'ready':'x'*50000})
            order.append('published_complete')
        with patch.object(receipts.os,'fsync',side_effect=fsync),patch.object(receipts.os,'link',side_effect=link):
            receipts.publish(self.target,{'ready':'x'*50000})
        self.assertEqual(order,['file_fsynced','published_complete']);self.assertEqual(self.sync.call_count,2)
        self.assertFalse(self.target.with_name('receipt.json.pending').exists())

    def test_existing_target_never_overwritten(self):
        self.target.write_bytes(b'original')
        with self.assertRaises(FileExistsError):receipts.publish(self.target,{'replacement':True})
        self.assertEqual(self.target.read_bytes(),b'original')

    def test_pending_collision_never_overwritten_or_published(self):
        pending=self.target.with_name('receipt.json.pending');pending.write_bytes(b'evidence')
        with self.assertRaises(FileExistsError):receipts.publish(self.target,{})
        self.assertEqual(pending.read_bytes(),b'evidence');self.assertFalse(self.target.exists())

    def test_failed_file_fsync_never_exposes_final_receipt(self):
        with patch.object(receipts.os,'fsync',side_effect=OSError('fixture fsync')),self.assertRaises(OSError):
            receipts.publish(self.target,{'ready':True})
        self.assertFalse(self.target.exists());self.sync.assert_not_called()

    def test_failed_directory_fsync_is_failure_even_after_atomic_link(self):
        self.sync.side_effect=OSError('fixture directory fsync')
        with self.assertRaises(OSError):receipts.publish(self.target,{'ready':True})
        self.assertEqual(json.loads(self.target.read_bytes()),{'ready':True})


if __name__=='__main__':unittest.main()
