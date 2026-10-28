"""CPU-MOCK rejection contracts for exact eight-file restoration, no remote access."""
import base64
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import restore_space_small_cpu as small


class SmallTests(unittest.TestCase):
    def fixture(self):
        rows=[];pins=[]
        for name in sorted(small.MEMBERS):
            raw=('CPU-MOCK '+name).encode();row={'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            pins.append(row);rows.append({**row,'base64':base64.b64encode(raw).decode()})
        return rows,pins

    def test_exact_members_decode_but_extra_missing_duplicate_and_escape_are_refused(self):
        rows,pins=self.fixture();self.assertEqual(len(small.decode_files(rows,pins)),8)
        for changed in (rows[:-1],rows+[rows[0]],rows[:-1]+[rows[0]],[{**rows[0],'path':'../escape'},*rows[1:]]):
            with self.assertRaises(ValueError):small.decode_files(changed,pins)

    def test_payload_size_sha_and_pin_mismatch_are_refused(self):
        rows,pins=self.fixture()
        for key,value in (('bytes',1),('sha256','0'*64),('base64',base64.b64encode(b'wrong').decode())):
            with self.assertRaises(ValueError):small.decode_files([{**rows[0],key:value},*rows[1:]],pins)
        with self.assertRaises(ValueError):small.decode_files(rows,[{**pins[0],'sha256':'0'*64},*pins[1:]])

    def test_exclusive_copy_keeps_original_when_repeated(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'child/file';small.write_one(target,b'CPU-MOCK exact bytes')
            self.assertEqual(target.read_bytes(),b'CPU-MOCK exact bytes')
            with self.assertRaises(ValueError):small.write_one(target,b'replacement')
            self.assertEqual(target.read_bytes(),b'CPU-MOCK exact bytes')

    def test_linked_parent_is_refused_before_write(self):
        with tempfile.TemporaryDirectory() as folder:
            parent=Path(folder);target=parent/'file'
            with patch.object(Path,'is_symlink',lambda path:path==parent):
                with self.assertRaises(ValueError):small.write_one(target,b'fixture')
            self.assertFalse(target.exists())


if __name__=='__main__':unittest.main(verbosity=2)
