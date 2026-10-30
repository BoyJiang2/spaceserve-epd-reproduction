"""Temporary Git repositories only. No deployment to real project directories."""
import ast
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import deploy_commit_cpu as deploy


class DeployTests(unittest.TestCase):
    def test_formal_local_imports_are_in_real_deployment_index(self):
        runtime=Path(__file__).resolve().parents[1]
        members=json.loads((runtime/'configs/source-files.json').read_text())
        deployed={row['path'] for row in members}
        tree=ast.parse((runtime/'scripts/run_formal.py').read_text())
        for node in ast.walk(tree):
            names=([alias.name for alias in node.names] if isinstance(node,ast.Import)
                   else [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for name in names:
                local='scripts/'+name.split('.')[0]+'.py'
                if (runtime/local).is_file():
                    self.assertIn(local,deployed,'formal import omitted from deployment/freeze index')

    def fixture(self,base):
        checkout=base/'checkout';root=base/'run';checkout.mkdir()
        (root/'evidence').mkdir(parents=True);(root/'configs').mkdir()
        index=checkout/deploy.PREFIX/'configs/source-files.json';index.parent.mkdir(parents=True)
        members=[]
        for name in sorted(deploy.REQUIRED):
            source='reproduction_paths.py' if name=='scripts/reproduction_paths.py' else deploy.PREFIX+'/'+name
            path=checkout/source;path.parent.mkdir(parents=True,exist_ok=True)
            if path!=index:path.write_text('# CPU-MOCK source\n' if path.suffix=='.py' else '{}')
            members.append({'source':source,'path':name})
        index.write_text(json.dumps(members))
        self.git(checkout,'init');self.git(checkout,'config','user.name','CPU Test')
        self.git(checkout,'config','user.email','cpu@example.invalid')
        return checkout,root,self.commit(checkout)

    def git(self,checkout,*args):
        return subprocess.check_output(['git','-C',str(checkout),*args],stderr=subprocess.STDOUT).decode().strip()

    def commit(self,checkout):
        self.git(checkout,'add','.');self.git(checkout,'commit','-m','CPU-MOCK fixture')
        return self.git(checkout,'rev-parse','HEAD')

    def test_exact_commit_freezes_bytes_and_refuses_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout,root,commit=self.fixture(Path(directory))
            with patch.object(deploy,'validate_destination'):
                result=deploy.deploy(checkout,commit,root)
                self.assertEqual(result['commit'],commit);self.assertTrue(result['grants_no_GPU'])
                for row in result['files']:
                    self.assertEqual((root/row['path']).read_bytes(),(checkout/row['git_path']).read_bytes())
                with self.assertRaises(ValueError):deploy.deploy(checkout,commit,root)

    def test_wrong_commit_dirty_source_and_existing_member_never_write_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout,root,commit=self.fixture(Path(directory))
            with patch.object(deploy,'validate_destination'):
                with self.assertRaises(ValueError):deploy.deploy(checkout,'0'*40,root)
                (checkout/'unreviewed').write_text('dirty')
                with self.assertRaises(ValueError):deploy.deploy(checkout,commit,root)
                (checkout/'unreviewed').unlink()
                (root/'scripts').mkdir();member=root/'scripts/resource_guard.py';member.write_text('preserve')
                with self.assertRaises(ValueError):deploy.deploy(checkout,commit,root)
                self.assertEqual(member.read_text(),'preserve')
                self.assertFalse((root/'evidence/GIT_DEPLOYED.json').exists())

    def test_unsafe_or_missing_source_index_refuses_all_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout,root,commit=self.fixture(Path(directory))
            index=checkout/deploy.PREFIX/'configs/source-files.json';members=json.loads(index.read_text())
            for altered in ([],members+[members[0]],members+[{'source':'../outside','path':'scripts/outside.py'}]):
                index.write_text(json.dumps(altered));revision=self.commit(checkout)
                with patch.object(deploy,'validate_destination'):
                    with self.assertRaises(ValueError):deploy.deploy(checkout,revision,root)
                self.assertFalse((root/'scripts').exists())

    def test_linked_ancestor_refused_and_real_scope_is_not_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory).resolve();checkout,root,commit=self.fixture(base)
            alias=base/'alias';alias.symlink_to(root,target_is_directory=True)
            with patch.object(deploy,'validate_destination') as scope:
                with self.assertRaises(ValueError):deploy.deploy(checkout,commit,alias)
                scope.assert_not_called()
            with patch.object(deploy.socket,'gethostname',return_value='WRONG'):
                with self.assertRaises(ValueError):deploy.validate_destination(root)


if __name__=='__main__':unittest.main()
