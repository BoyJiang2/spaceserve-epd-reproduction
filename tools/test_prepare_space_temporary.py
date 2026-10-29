"""Temporary CPU-preparation configuration tests; no deployment or GPU query."""
import base64
import builtins
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import prepare_space_temporary as prepare


class PrepareTests(unittest.TestCase):
    def config(self):
        path=Path(__file__).resolve().parents[1]/'spaceserve/runtime/configs/project.temporary-idle.candidate.json'
        config=json.loads(path.read_bytes());user=(prepare.QUOTE+'\n').encode()
        config.update(state='approved_scope',run_id=prepare.RUN_ID,source_commit='a'*40,allowed_actions=['numeric','model'])
        config['temporary_gpu_use'].update(start_ms=1000000,end_ms=4600000,user_sha256=hashlib.sha256(user).hexdigest())
        return config,user

    def test_exact_config_and_changed_budget_geometry_or_origin(self):
        config,user=self.config();self.assertEqual(prepare.validate_config(json.dumps(config).encode(),'a'*40,user),config)
        for change in ({'gpu_devices':[0]},{'booking':{'not':'temporary'}},{'allowed_actions':['formal']},
                       {'source_commit':'b'*40},{'workload_numa_node':1},{'mask_off':48},{'unexpected':'field'}):
            with self.subTest(change=change),self.assertRaises(ValueError):prepare.validate_config(json.dumps(config|change).encode(),'a'*40,user)
        for change in ({'end_ms':4600001},{'start_ms':True},{'boot_id':'old'}):
            bad=copy.deepcopy(config);bad['temporary_gpu_use'].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):prepare.validate_config(json.dumps(bad).encode(),'a'*40,user)
        with self.assertRaises(ValueError):prepare.validate_config(json.dumps(config).encode(),'a'*40,b'not the original user instruction')

    def test_non_cpu_action_or_changed_helper_refused_before_processes(self):
        for payload in ({'phase':'numeric'},{'phase':'deploy','migrate_code_cpu':base64.b64encode(b'changed').decode()}):
            with self.subTest(payload=payload),patch.object(sys,'stdin',io.StringIO(json.dumps(payload))),patch('subprocess.check_output') as query:
                with self.assertRaises(ValueError):prepare.main()
                query.assert_not_called()

    def test_prepare_then_cpu_control_flow_with_mocked_helpers(self):
        repo=Path(__file__).resolve().parents[1]
        config,user=self.config()
        modules={name:base64.b64encode((repo/'tools'/f'{name}.py').read_bytes()).decode() for name in ('migrate_code_cpu','validate_space_cpu')}
        with tempfile.TemporaryDirectory(prefix='temporary-prepare-test-',dir=Path(__file__).resolve().parent) as name:
            root=Path(name);run=root/'runs'/prepare.RUN_ID
            (root/'assets/envs/space/lib/python3.10/site-packages').mkdir(parents=True)
            (root/'assets/manifest.json').write_bytes(b'[]')
            evidence=root/'staging/temporary-gpu2-preparation';evidence.mkdir(parents=True)
            (evidence/'deploy.log').write_bytes(b'CPU-MOCK deploy')
            config['project_root']=root.as_posix();raw=json.dumps(config).encode()
            sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
            prior={'exit_code':0,'runtime_commit':'a'*40,'config_sha256':hashlib.sha256(raw).hexdigest(),'log_sha256':sha(evidence/'deploy.log')}
            (evidence/'deploy.terminal.json').write_text(json.dumps(prior))
            commands=[]
            ancestry=[]
            blocked_path=None
            def check_ancestry(path):
                ancestry.append(path)
                if path==blocked_path:raise ValueError('CPU-MOCK foreign or linked temporary ancestor')
            def execute(argv,*args):
                commands.append(argv)
                if 'prepare' in argv:
                    (run/'configs').mkdir(parents=True)
                    frozen={**config,'source_manifest_sha256':'c'*64,'asset_manifest_sha256':hashlib.sha256(b'[]').hexdigest()}
                    (run/'configs/project.json').write_text(json.dumps(frozen))
            def exclusive(path,data):
                with path.open('x') as stream:json.dump(data,stream)
            real_exec=builtins.exec
            def modules_exec(code,namespace,*args):
                if getattr(code,'co_filename','')=='migrate_code_cpu':
                    namespace.update(validate_executor=lambda:None,real_ancestry=check_ancestry,sha=sha,exclusive_json=exclusive)
                elif getattr(code,'co_filename','')=='validate_space_cpu':
                    namespace.update(SITE={},ASSETS_SHA=hashlib.sha256(b'[]').hexdigest(),child_environment=lambda nonce:{'CPU-MOCK':nonce},execute=execute)
                else:return real_exec(code,namespace,*args)
            read_text=Path.read_text
            def read(path,*args,**kwargs):
                if path.as_posix()=='/proc/sys/kernel/random/boot_id':return prepare.BOOT
                return read_text(path,*args,**kwargs)
            snapshot={'origin':'gputime_read_only_api','read_only':True,'observed_ms':1100000,'resources':[{'id':'h20/qjh003','active':True}]}
            payload={**modules,'runtime_commit':'a'*40,'config':base64.b64encode(raw).decode(),'user':base64.b64encode(user).decode(),'resource_snapshot':snapshot}
            loader=SimpleNamespace(exec_module=lambda module:None)
            wrong_head=False
            def output(argv,**kwargs):
                if argv[0]=='nvidia-smi':return '' if '--query-compute-apps=pid' in argv else prepare.UUID+', 0, 0\n'
                if 'rev-parse' in argv:return ('b' if wrong_head else 'a')*40+'\n'
                if 'status' in argv:return ''
                raise AssertionError(argv)
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.dict(sys.modules))
                stack.enter_context(patch.object(prepare,'ROOT',root));stack.enter_context(patch.object(prepare,'RUN',run))
                stack.enter_context(patch.object(builtins,'exec',modules_exec))
                stack.enter_context(patch.object(prepare.time,'time',return_value=1100))
                stack.enter_context(patch.object(Path,'read_text',read))
                imported=stack.enter_context(patch.object(prepare.importlib.util,'spec_from_file_location',return_value=SimpleNamespace(loader=loader)))
                stack.enter_context(patch.object(prepare.importlib.util,'module_from_spec',return_value=SimpleNamespace(inventory=lambda path:[])))
                stack.enter_context(patch('subprocess.check_output',side_effect=output))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                for folder in ('cpu-hf','cpu-torch'):
                    blocked_path=root/'tmp'/folder
                    with patch.object(sys,'stdin',io.StringIO(json.dumps(payload|{'phase':'prepare'}))):
                        with self.assertRaisesRegex(ValueError,'temporary ancestor'):prepare.main()
                    self.assertFalse(blocked_path.exists())
                    self.assertFalse((evidence/'prepare.claim.json').exists())
                blocked_path=None
                for phase in ('prepare','cpu'):
                    with patch.object(sys,'stdin',io.StringIO(json.dumps(payload|{'phase':phase}))):prepare.main()
                wrong_head=True
                with patch.object(sys,'stdin',io.StringIO(json.dumps(payload|{'phase':'cpu'}))):
                    with self.assertRaisesRegex(ValueError,'Live repository'):prepare.main()
                self.assertEqual(imported.call_count,2)
            self.assertEqual(len(commands),2)
            for folder in ('cpu','cpu-hf','cpu-torch'):self.assertIn(root/'tmp'/folder,ancestry)
            for phase in ('prepare','cpu'):
                self.assertEqual(json.loads((evidence/(phase+'.terminal.json')).read_bytes())['exit_code'],0)
                self.assertFalse(json.loads((evidence/(phase+'.claim.json')).read_bytes())['booking_claimed'])


if __name__=='__main__':unittest.main()
