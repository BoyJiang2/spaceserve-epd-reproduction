"""CPU-only rejection and byte-preservation checks; no remote/GPU actions."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import types
import unittest
from unittest.mock import patch

import stage_cpu as stage


class StageTests(unittest.TestCase):
    def test_link_target_must_be_in_actual_copied_members(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory).resolve()
            (root/'input').mkdir()
            (root/'uncopied').mkdir()
            (root/'input/__pycache__').mkdir()
            with patch.object(stage,'MEMBERS',('input',)):
                self.assertTrue(stage.copied_target(root, root/'input/valid.txt'))
                self.assertFalse(stage.copied_target(root, root/'uncopied/file.txt'))
                self.assertFalse(stage.copied_target(root, root/'input/__pycache__/cache.pyc'))
                self.assertFalse(stage.copied_target(root, root.parent/'outside.txt'))

    def test_real_internal_link_retained_and_dangling_refused(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory).resolve()
            (root/'input').mkdir()
            (root/'input/data.txt').write_text('unchanged')
            try:
                (root/'input/link').symlink_to('data.txt')
            except OSError as error:
                self.skipTest('platform symlink permission: '+type(error).__name__)
            with patch.object(stage,'MEMBERS',('input',)):
                self.assertIn({'path':'input/link','link':'data.txt','target_member':'input/data.txt'},stage.inventory(root))
                (root/'input/data.txt').unlink()
                with self.assertRaises(FileNotFoundError):
                    stage.inventory(root)

    def test_absolute_internal_link_relocates_without_changing_source(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            base=Path(directory).resolve()
            source=base/'source'
            (source/'input').mkdir(parents=True)
            (source/'input/data.txt').write_text('unchanged')
            try:
                (source/'input/link').symlink_to(source/'input/data.txt')
            except OSError as error:
                self.skipTest('platform symlink permission: '+type(error).__name__)
            approval=base/'gate.json'
            approval.write_text(json.dumps({'scope':'Space-CPU-stage-only','passed':True,
                'stage_sha256':hashlib.sha256(Path(stage.__file__).read_bytes()).hexdigest()}))
            def copy(command,**kwargs):
                shutil.copy2(command[-2],command[-1])
            with patch.object(stage,'SOURCE',source),patch.object(stage,'TARGET',base/'target'), \
                 patch.object(stage,'MEMBERS',('input',)), \
                 patch.object(stage.os,'uname',return_value=types.SimpleNamespace(nodename='qjh000'),create=True), \
                 patch.object(stage.os,'getuid',return_value=2147,create=True), \
                 patch.object(stage.shutil,'disk_usage',return_value=types.SimpleNamespace(free=100*1024**3)), \
                 patch.object(stage.subprocess,'run',side_effect=copy):
                stage.stage(approval)
                self.assertEqual((source/'input/link').readlink(),source/'input/data.txt')
                self.assertEqual((base/'target/input/link').readlink(),Path('data.txt'))
                self.assertEqual((base/'target/input/link').resolve(strict=True),base/'target/input/data.txt')

    def test_bad_gate_never_creates_destination(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            base=Path(directory)
            approval=base/'gate.json'
            approval.write_text('{}')
            with patch.object(stage,'TARGET',base/'target'), \
                 patch.object(stage.os,'uname',return_value=types.SimpleNamespace(nodename='qjh000'),create=True), \
                 patch.object(stage.os,'getuid',return_value=2147,create=True):
                with self.assertRaisesRegex(RuntimeError,'G2 stage approval'):
                    stage.stage(approval)
                self.assertFalse((base/'target').exists())

    def test_independent_copy_and_refuse_second_stage(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            base=Path(directory)
            source=base/'source'
            source.mkdir()
            (source/'input').mkdir()
            (source/'input/data.txt').write_bytes(b'preserve\r\n')
            approval=base/'gate.json'
            approval.write_text(json.dumps({'scope':'Space-CPU-stage-only','passed':True,
                'stage_sha256':hashlib.sha256(Path(stage.__file__).read_bytes()).hexdigest()}))
            def copy(command, **kwargs):
                shutil.copy2(command[-2],command[-1])
            with patch.object(stage,'SOURCE',source),patch.object(stage,'TARGET',base/'target'), \
                 patch.object(stage,'MEMBERS',('input',)), \
                 patch.object(stage.os,'uname',return_value=types.SimpleNamespace(nodename='qjh000'),create=True), \
                 patch.object(stage.os,'getuid',return_value=2147,create=True), \
                 patch.object(stage.shutil,'disk_usage',return_value=types.SimpleNamespace(free=100*1024**3)), \
                 patch.object(stage.subprocess,'run',side_effect=copy):
                stage.stage(approval)
                self.assertEqual((base/'target/input/data.txt').read_bytes(),b'preserve\r\n')
                self.assertEqual((source/'input/data.txt').read_bytes(),b'preserve\r\n')
                with self.assertRaisesRegex(RuntimeError,'existing destination'):
                    stage.stage(approval)


if __name__ == '__main__':
    unittest.main()
