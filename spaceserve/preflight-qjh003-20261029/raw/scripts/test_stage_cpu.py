"""Linux CPU contracts for shared assets; no models, GPU, network or real project writes."""
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import stage_cpu as stage


class StageTests(unittest.TestCase):
    def test_link_target_must_be_in_actual_copied_members(self):
        root=Path('/CPU-MOCK/assets')
        with patch.object(stage,'MEMBERS',('input',)):
            self.assertTrue(stage.copied_target(root,root/'input/a'))
            for target in (root/'uncopied/a',root/'input/__pycache__/a',root.parent/'outside'):
                self.assertFalse(stage.copied_target(root,target))

    def test_inventory_preserves_internal_links_and_rejects_dangling(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();(root/'input').mkdir()
            (root/'input/data').write_bytes(b'preserve\r\n')
            (root/'input/link').symlink_to('data')
            with patch.object(stage,'MEMBERS',('input',)):
                before=stage.inventory(root)
                self.assertIn({'path':'input/link','link':'data','target_member':'input/data'},before)
                self.assertEqual((root/'input/data').read_bytes(),b'preserve\r\n')
                (root/'input/data').unlink()
                with self.assertRaises(FileNotFoundError):stage.inventory(root)

    def test_uncopied_link_and_foreign_owner_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();(root/'input').mkdir();(root/'outside').write_text('x')
            (root/'input/link').symlink_to('../outside')
            with patch.object(stage,'MEMBERS',('input',)):
                with self.assertRaises(ValueError):stage.inventory(root)
                (root/'input/link').unlink();(root/'input/data').write_text('x')
                with patch.object(stage.os,'getuid',return_value=-1):
                    with self.assertRaises(ValueError):stage.inventory(root)

    def layout(self,base):
        project=base/'project'
        return types.SimpleNamespace(project_root=project,run_root=project/'runs/new',
            assets_root=project/'assets',config={'host':'CPU-MOCK','uid':123,'run_id':'new'})

    def test_wrong_executor_and_existing_run_refuse_without_asset_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            layout=self.layout(Path(directory));layout.run_root.mkdir(parents=True)
            with patch.object(stage.socket,'gethostname',return_value='WRONG'):
                with self.assertRaises(ValueError):stage.prepare(layout,'a'*40,'unused')
            with patch.object(stage.socket,'gethostname',return_value='CPU-MOCK'),patch.object(stage.os,'getuid',return_value=123):
                # Existing project is deliberately foreign to the mock UID as well.
                with self.assertRaises(ValueError):stage.prepare(layout,'a'*40,'unused')
            self.assertFalse((layout.run_root/'evidence').exists())

    def test_intermediate_run_symlink_refused_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory).resolve();layout=self.layout(base)
            layout.project_root.mkdir();outside=base/'outside';outside.mkdir()
            (layout.project_root/'runs').symlink_to(outside,target_is_directory=True)
            with patch.object(stage.socket,'gethostname',return_value='CPU-MOCK'),patch.dict(layout.config,{'uid':stage.os.getuid()}):
                with self.assertRaisesRegex(ValueError,'Linked'):stage.prepare(layout,'a'*40,'unused')
            self.assertEqual(list(outside.iterdir()),[])


if __name__=='__main__':unittest.main()
