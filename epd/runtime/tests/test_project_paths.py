"""CPU path/identity contracts; no real project writes, network or GPU imports."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import hashlib
import shutil
import types
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import project_config
import preflight_guard as guard
from test_preflight_v5 import Fixture


class ProjectPaths(unittest.TestCase):
    def fixture(self,base):
        project=base/'epd';code=project/'repo/epd/runtime';code.mkdir(parents=True)
        cohort=project/'runs/CPU-MOCK';cohort.mkdir(parents=True)
        config={'run_id':'CPU-MOCK','host':'qjh003','uid':os.getuid()}
        layout=types.SimpleNamespace(config=config,project_root=project,checkout=project/'repo',code_root=code,
            assets_root=project/'assets',run_root=cohort)
        (cohort/'project.json').write_text(json.dumps(config))
        static={'root':str(cohort),'host':'qjh003','uid':os.getuid()}
        return layout,static

    def test_cohort_code_checkout_and_assets_remain_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            layout,static=self.fixture(Path(directory).resolve())
            with patch.object(project_config,'context',return_value=layout), \
                 patch.object(project_config,'__file__',str(layout.code_root/'project_config.py')):
                actual=project_config.paths_for(static)
                self.assertEqual(actual.run_root,Path(static['root']))
                self.assertNotEqual(actual.code_root,actual.run_root)
                self.assertFalse(actual.assets_root.is_relative_to(actual.run_root))

    def test_other_root_or_changed_external_scope_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            layout,static=self.fixture(Path(directory).resolve())
            with patch.object(project_config,'context',return_value=layout), \
                 patch.object(project_config,'__file__',str(layout.code_root/'project_config.py')):
                for root in (layout.code_root,layout.assets_root,layout.run_root.parent/'other'):
                    with self.assertRaises(ValueError):project_config.paths_for({**static,'root':str(root)})
                layout.config['run_id']='changed'
                with self.assertRaises(ValueError):project_config.paths_for(static)

    def test_symlink_ancestor_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            layout,static=self.fixture(Path(directory).resolve())
            outside=Path(directory)/'outside';outside.mkdir()
            layout.assets_root.symlink_to(outside,target_is_directory=True)
            with patch.object(project_config,'context',return_value=layout), \
                 patch.object(project_config,'__file__',str(layout.code_root/'project_config.py')):
                with self.assertRaises(ValueError):project_config.paths_for(static)

    def test_only_deployment_hashes_are_excluded_from_static_scope(self):
        data={'state':'candidate','booking':{'id':'CPU-MOCK'},'source_commit':None,
              'source_manifest_sha256':None,'asset_manifest_sha256':None,'cpu_scope':None}
        self.assertEqual(project_config.static_scope(data),{'state':'candidate','booking':{'id':'CPU-MOCK'},'cpu_scope':None})


class SourceBindings(Fixture):
    def test_wrong_checkout_code_assets_or_cohort_deployment_is_rejected(self):
        for key in ('checkout_root','code_root','assets_root','cohort_root'):
            descriptor=self.write('deploy.json',{**self.deployment,key:'/CPU-MOCK/wrong'})
            inputs={**self.inputs,'deploy_sha256':descriptor['sha256']}
            with self.assertRaises(ValueError):guard.verify_checkout(self.config,inputs,self.owner,self.command)

    def test_changed_shared_path_module_is_rejected(self):
        (self.root/'reproduction_paths.py').write_text('# changed shared admission code')
        with self.assertRaisesRegex(ValueError,'file SHA'):
            guard.verify_checkout(self.config,self.inputs,self.owner,self.command)


class CPUClosure(unittest.TestCase):
    def fixture(self,base):
        import cpu_target_runner as runner
        checkout=base/'checkout';code=checkout/'epd/runtime';code.mkdir(parents=True)
        rows=[]
        for original in sorted(ROOT.rglob('*')):
            if not original.is_file() or '__pycache__' in original.parts:continue
            logical=original.relative_to(ROOT).as_posix();destination=code/logical
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,destination)
            rows.append({'path':logical,'git_path':'epd/runtime/'+logical,'sha256':runner.sha(destination)})
        shared=checkout/'reproduction_paths.py';shutil.copyfile(ROOT.parents[1]/'reproduction_paths.py',shared)
        rows.append({'path':'common/reproduction_paths.py','git_path':'reproduction_paths.py','sha256':runner.sha(shared)})
        return runner,checkout,rows

    def test_complete_cpu_source_and_omitted_shared_or_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            runner,checkout,rows=self.fixture(Path(directory))
            tracked='\n'.join(row['git_path'] for row in rows)
            with patch.object(runner,'CONFIG',types.SimpleNamespace(checkout=checkout)), \
                 patch.object(runner.subprocess,'check_output',return_value=tracked):
                self.assertEqual(len(runner.source_hashes(ROOT,{'files':rows})),len(rows))
                for omitted in ('common/reproduction_paths.py','project_config.py','experiment_plan.py'):
                    with self.assertRaises(ValueError):
                        runner.source_hashes(ROOT,{'files':[row for row in rows if row['path']!=omitted]})

    def test_changed_loaded_shared_module_cannot_be_hidden_by_new_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            runner,checkout,rows=self.fixture(Path(directory))
            shared=checkout/'reproduction_paths.py';shared.write_text('# substituted admission module')
            for row in rows:
                if row['path']=='common/reproduction_paths.py':row['sha256']=runner.sha(shared)
            with patch.object(runner,'CONFIG',types.SimpleNamespace(checkout=checkout)), \
                 patch.object(runner.subprocess,'check_output',return_value='\n'.join(row['git_path'] for row in rows)):
                with self.assertRaisesRegex(ValueError,'Actually loaded'):
                    runner.source_hashes(ROOT,{'files':rows})


if __name__=='__main__':unittest.main()
