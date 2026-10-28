"""Small CPU-only file-copy contracts; no Linux executor or remote calls."""
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parent))
import materialize_assets_cpu as assets


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        self.source=self.root/'source';self.source.mkdir()
        (self.source/'nested').mkdir()
        (self.source/'nested/.hidden').write_bytes(b'original fixture bytes')
        (self.source/'__pycache__').mkdir()
        (self.source/'__pycache__/fixture.pyc').write_bytes(b'not executable fixture')
        self.owner=patch.object(assets,'OWNER',self.source.stat().st_uid);self.owner.start();self.addCleanup(self.owner.stop)
        self.nofollow=patch.object(os,'O_NOFOLLOW',getattr(os,'O_NOFOLLOW',0),create=True)
        self.nofollow.start();self.addCleanup(self.nofollow.stop)
        if os.name=='nt':
            # CPython 3.13 Windows lstat/fstat expose different ctime after fsync.
            # This fixture does not certify the production Linux ctime/nofollow guard.
            original=assets.fingerprint
            self.windows_stat=patch.object(assets,'fingerprint',lambda info:original(info)[:-1])
            self.windows_stat.start();self.addCleanup(self.windows_stat.stop)

    def scan(self,path):return assets.inventory(path,lambda:None)

    def test_complete_members_copy_and_source_bytes_remain_equal(self):
        before=self.scan(self.source);target=self.root/'target'
        assets.copy_members(self.source,target,before,lambda:None)
        self.assertEqual(before,self.scan(target));self.assertEqual(before,self.scan(self.source))
        self.assertIn('__pycache__/fixture.pyc',[row['path'] for row in before])
        self.assertIn('nested/.hidden',[row['path'] for row in before])

    def test_existing_target_is_never_overwritten(self):
        target=self.root/'target';target.mkdir();(target/'keep').write_bytes(b'untouched')
        with self.assertRaises(FileExistsError):assets.copy_members(self.source,target,self.scan(self.source),lambda:None)
        self.assertEqual((target/'keep').read_bytes(),b'untouched')

    def test_changed_source_is_rejected_and_partial_is_preserved(self):
        before=self.scan(self.source);(self.source/'__pycache__/fixture.pyc').write_bytes(b'changed fixture')
        target=self.root/'target'
        with self.assertRaises(ValueError):assets.copy_members(self.source,target,before,lambda:None)
        self.assertTrue(target.exists())

    def test_external_links_and_foreign_owner_are_rejected(self):
        fake=SimpleNamespace(st_uid=assets.OWNER,st_mode=stat.S_IFLNK|0o777)
        with patch.object(Path,'lstat',return_value=fake),patch.object(os,'readlink',return_value='/outside'):
            with self.assertRaises(ValueError):assets.inventory(self.source,lambda:None,True)
        with patch.object(assets,'OWNER',self.source.stat().st_uid+1):
            with self.assertRaises(ValueError):self.scan(self.source)

    def test_byte_budget_and_deadline_fail_before_copy(self):
        with patch.object(assets,'LIMIT',1):
            with self.assertRaises(ValueError):self.scan(self.source)
        def expired():raise TimeoutError('actual CPU-MOCK deadline')
        target=self.root/'target'
        with self.assertRaises(TimeoutError):assets.copy_members(self.source,target,self.scan(self.source),expired)
        self.assertFalse(target.exists())

    def test_linked_staging_rejected_before_any_evidence_write(self):
        staging=self.root/'staging';staging.mkdir();evidence=staging/'asset-data'
        with patch.object(Path,'is_symlink',lambda path:path==staging):
            with self.assertRaises(ValueError):assets.create_evidence(evidence,b'fixture')
        self.assertEqual(list(staging.iterdir()),[])

    def test_own_process_permission_error_rejected_but_exit_is_allowed(self):
        class Process:
            name=str(os.getpid()+100000)
            def stat(self):return SimpleNamespace(st_uid=2147)
            def __truediv__(self,name):return self
            def resolve(self,strict=True):raise self.error
        process=Process();proc=SimpleNamespace(iterdir=lambda:[process])
        process.error=PermissionError('CPU-MOCK restricted own cwd')
        with self.assertRaises(ValueError):assets.guard_processes(proc)
        process.error=FileNotFoundError('CPU-MOCK process exited')
        assets.guard_processes(proc)


if __name__=='__main__':unittest.main(verbosity=2)
