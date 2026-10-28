import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import deploy_commit_cpu as deploy


class DeployTests(unittest.TestCase):
    def fixture(self,base):
        checkout=base/'checkout';root=base/'runtime'
        checkout.mkdir();(root/'evidence').mkdir(parents=True);(root/'scripts').mkdir()
        source=checkout/deploy.PREFIX;(source/'scripts').mkdir(parents=True);(source/'configs').mkdir()
        (root/'configs').mkdir()
        rows=[]
        for i in range(56):
            name='scripts/example.py' if i==0 else f'scripts/example-{i}.py'
            p=source/name;p.write_text('frozen code');(root/name).write_bytes(p.read_bytes())
            rows.append({'path':name,'bytes':p.stat().st_size,'sha256':deploy.sha(p)})
        manifest=source/'configs/runtime-extension-source-manifest.json'
        manifest.write_text(json.dumps(rows))
        for name in sorted(deploy.STATIC_CONFIGS):
            p=source/name
            if p!=manifest:p.write_text('{}')
            (root/name).write_bytes(p.read_bytes())
            rows.append({'path':name,'bytes':p.stat().st_size,'sha256':deploy.sha(p)})
        (source/'configs/deployment-files.json').write_text(json.dumps(rows))
        def git(*args):return subprocess.check_output(['git','-C',str(checkout),*args],stderr=subprocess.STDOUT).decode().strip()
        git('init');git('config','user.name','CPU Test');git('config','user.email','cpu@example.invalid')
        git('add','.');git('commit','-m','fixture')
        return checkout,root,git('rev-parse','HEAD'),deploy.sha(manifest)

    def test_exact_commit_deploys_and_refuses_repeat(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            checkout,root,commit,sha=self.fixture(Path(directory))
            with patch.object(deploy,'SOURCE_SHA',sha),patch.object(deploy,'DEPLOYMENT_SHA',deploy.sha(checkout/deploy.PREFIX/'configs/deployment-files.json')):
                state=deploy.deploy(checkout,commit,root)
                self.assertEqual(state['commit'],commit)
                self.assertEqual((root/'scripts/example.py').read_text(),'frozen code')
                with self.assertRaises(RuntimeError):deploy.deploy(checkout,commit,root)

    def test_dirty_wrong_commit_or_runtime_refuse_before_write(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            checkout,root,commit,sha=self.fixture(Path(directory))
            with patch.object(deploy,'SOURCE_SHA',sha),patch.object(deploy,'DEPLOYMENT_SHA',deploy.sha(checkout/deploy.PREFIX/'configs/deployment-files.json')):
                with self.assertRaises(RuntimeError):deploy.deploy(checkout,'0'*40,root)
                p=root/'scripts/example.py';p.write_text('different runtime')
                with self.assertRaises(RuntimeError):deploy.deploy(checkout,commit,root)
                self.assertEqual(p.read_text(),'different runtime')
                (checkout/'unreviewed').write_text('dirty')
                with self.assertRaises(RuntimeError):deploy.deploy(checkout,commit,root)
                self.assertFalse((root/'evidence/GIT_DEPLOYED.json').exists())

    def test_empty_missing_extra_members_and_receipt_ancestor_refuse_without_copy(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            checkout,root,commit,sha=self.fixture(Path(directory))
            inventory=checkout/deploy.PREFIX/'configs/deployment-files.json'
            rows=json.loads(inventory.read_text())
            for changed in ([],rows[:-1],rows+[{'path':'historical','bytes':0,'sha256':'0'*64}]):
                inventory.write_text(json.dumps(changed))
                subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
                subprocess.run(['git','-C',str(checkout),'commit','-m','invalid membership'],check=True,capture_output=True)
                revision=subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD']).decode().strip()
                with patch.object(deploy,'SOURCE_SHA',sha),patch.object(deploy,'shutil') as copy:
                    with self.assertRaises(RuntimeError):deploy.deploy(checkout,revision,root)
                    copy.copyfile.assert_not_called()
            inventory.write_text(json.dumps(rows))
            subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
            subprocess.run(['git','-C',str(checkout),'commit','-m','restore'],check=True,capture_output=True)
            revision=subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD']).decode().strip()
            original=Path.is_symlink
            with patch.object(deploy,'SOURCE_SHA',sha),patch.object(deploy,'DEPLOYMENT_SHA',deploy.sha(inventory)), \
                 patch.object(Path,'is_symlink',lambda p:p==root/'evidence' or original(p)), \
                 patch.object(deploy,'shutil') as copy:
                with self.assertRaises(RuntimeError):deploy.deploy(checkout,revision,root)
                copy.copyfile.assert_not_called()
