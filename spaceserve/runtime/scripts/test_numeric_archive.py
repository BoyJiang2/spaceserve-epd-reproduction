import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from archive_numeric_producer import freeze


class ArchiveTests(unittest.TestCase):
    def test_exact_mapping_and_refuse_changed_original(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory).resolve()
            (root/'evidence').mkdir()
            source=root/'evidence/source.json'
            payload=b'{"preserved":true}\r\n'
            source.write_bytes(payload)
            gate={'producer_sha256':'fixture-only','bound_files':[{'path':'evidence/source.json',
                'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}]}
            (root/'evidence/G3_NUMERICAL_APPROVED.json').write_text(json.dumps(gate))
            result=freeze(root)
            self.assertEqual(len(result['mapping']),2)
            self.assertEqual((root/'evidence/numeric-producer/evidence/source.json').read_bytes(),payload)
            self.assertEqual(source.read_bytes(),payload)
            with self.assertRaises(FileExistsError): freeze(root)
            gate['bound_files'][0]['path']=str(source)
            (root/'evidence/G3_NUMERICAL_APPROVED.json').write_text(json.dumps(gate))
            with self.assertRaisesRegex(RuntimeError,'unsafe original'): freeze(root)
            gate['bound_files'][0]['path']='evidence/source.json'
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory).resolve()
            (root/'evidence').mkdir()
            (root/'evidence/source.json').write_bytes(b'changed')
            (root/'evidence/G3_NUMERICAL_APPROVED.json').write_text(json.dumps(gate))
            with self.assertRaisesRegex(RuntimeError,'no longer matches'): freeze(root)
            self.assertFalse((root/'evidence/numeric-producer').exists())


if __name__=='__main__':
    unittest.main()
