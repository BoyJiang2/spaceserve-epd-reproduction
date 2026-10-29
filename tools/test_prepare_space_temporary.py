"""Temporary CPU-preparation configuration tests; no deployment or GPU query."""
import base64
import builtins
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import shutil
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import prepare_space_temporary as prepare


class PrepareTests(unittest.TestCase):
    def test_recovery_requires_exact_failure_and_unchanged_window(self):
        repo=Path(__file__).resolve().parents[1]
        originals=repo/'spaceserve/validation/temporary-idle-gpu2-20261029/deploy-failure'
        with tempfile.TemporaryDirectory(prefix='recovery-test-',dir=Path(__file__).resolve().parent) as name:
            root=Path(name);evidence=root/'staging/temporary-gpu2-preparation';evidence.mkdir(parents=True)
            for filename in ('deploy.terminal.json','deploy.log'):shutil.copyfile(originals/filename,evidence/filename)
            raw=(originals/'original-config.json').read_bytes();config=json.loads(raw);config['source_commit']='c'*40
            bundle=root/'staging/temporary-gpu2-recovery.bundle';payload=b'CPU-MOCK bundle';bundle.write_bytes(payload)
            data={'prior_config':base64.b64encode(raw).decode(),'bundle':{'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}}
            with patch.object(prepare,'ROOT',root),patch.object(prepare.os,'getuid',return_value=root.stat().st_uid,create=True):
                self.assertEqual(prepare.recovery_bundle(evidence,config,data),bundle)
                scheduled,user=self.scheduled_config();scheduled['source_commit']='c'*40
                self.assertEqual(prepare.recovery_bundle(evidence,scheduled,data,True),bundle)
                with self.assertRaisesRegex(ValueError,'never extend'):
                    prepare.recovery_bundle(evidence,scheduled|{'mask_off':48},data,True)
                changed=copy.deepcopy(config);changed['temporary_gpu_use']['end_ms']+=1
                with self.assertRaisesRegex(ValueError,'never extend'):prepare.recovery_bundle(evidence,changed,data)
                with self.assertRaises(ValueError):prepare.recovery_bundle(evidence,config,data|{'bundle':{'bytes':True,'sha256':hashlib.sha256(payload).hexdigest()}})
                with self.assertRaises(ValueError):prepare.recovery_bundle(evidence,config,data|{'bundle':{'bytes':len(payload),'sha256':'0'*64}})
                (evidence/'deploy.terminal.json').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'original failed'):prepare.recovery_bundle(evidence,config,data)
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

    def scheduled_config(self):
        config,_=self.config();user=(prepare.SCHEDULED_QUOTE+'\n').encode()
        config.pop('temporary_gpu_use')
        config.update(state='candidate',run_id=prepare.SCHEDULED_RUN_ID,allowed_actions=[],
            scheduled_gpu_start_ms=prepare.SCHEDULED_START_MS,cpu_preparation_deadline_ms=prepare.SCHEDULED_CPU_END_MS,
            scheduled_user_sha256=hashlib.sha256(user).hexdigest())
        return config,user

    def test_scheduled_candidate_cannot_authorize_gpu_or_change_geometry(self):
        config,user=self.scheduled_config()
        self.assertEqual(prepare.validate_config(json.dumps(config).encode(),'a'*40,user,True),config)
        for change in ({'state':'approved_scope'},{'allowed_actions':['numeric']},{'booking':{}},
                       {'gpu_devices':[0]},{'workload_cpu_affinity':[False]+list(range(1,90))},
                       {'scheduled_gpu_start_ms':prepare.SCHEDULED_START_MS-1}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                prepare.validate_config(json.dumps(config|change).encode(),'a'*40,user,True)

    def test_scheduled_prepare_then_cpu_remains_candidate(self):
        self.test_prepare_then_cpu_control_flow_with_mocked_helpers(scheduled=True)

    def test_prepare_then_cpu_control_flow_with_mocked_helpers(self,scheduled=False):
        repo=Path(__file__).resolve().parents[1]
        config,user=self.scheduled_config() if scheduled else self.config()
        now_ms=prepare.SCHEDULED_START_MS if scheduled else 1100000
        modules={name:base64.b64encode((repo/'tools'/f'{name}.py').read_bytes()).decode() for name in ('migrate_code_cpu','validate_space_cpu')}
        with tempfile.TemporaryDirectory(prefix='temporary-prepare-test-',dir=Path(__file__).resolve().parent) as name:
            root=Path(name);run=root/'runs'/(prepare.SCHEDULED_RUN_ID if scheduled else prepare.RUN_ID)
            (root/'assets/envs/space/lib/python3.10/site-packages').mkdir(parents=True)
            (root/'assets/manifest.json').write_bytes(b'[]')
            evidence=root/('staging/space-16-preparation' if scheduled else 'staging/temporary-gpu2-preparation');evidence.mkdir(parents=True)
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
            snapshot={'origin':'gputime_read_only_api','read_only':True,'observed_ms':now_ms,'resources':[{'id':'h20/qjh003','active':True}],'bookings':[]}
            payload={**modules,'runtime_commit':'a'*40,'scheduled_cpu':scheduled,'config':base64.b64encode(raw).decode(),'user':base64.b64encode(user).decode(),'resource_snapshot':snapshot}
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
                stack.enter_context(patch.object(prepare.time,'time',return_value=now_ms/1000))
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
                if scheduled:
                    for bad_time in (prepare.SCHEDULED_START_MS-1,prepare.SCHEDULED_CPU_END_MS-360000):
                        with patch.object(prepare.time,'time',return_value=bad_time/1000),patch.object(sys,'stdin',io.StringIO(json.dumps(payload|{'phase':'prepare'}))):
                            with self.assertRaises((ValueError,TimeoutError)):prepare.main()
                    for kind in ('cpu',None):
                        conflicting=copy.deepcopy(payload)
                        conflicting['resource_snapshot']['bookings']=[{'resource_id':'h20/qjh003','kind':kind,'user':'other','start_ms':now_ms,'end_ms':now_ms+500000}]
                        with patch.object(sys,'stdin',io.StringIO(json.dumps(conflicting|{'phase':'prepare'}))):
                            with self.assertRaisesRegex(ValueError,'reservation overlaps'):prepare.main()
                    self.assertFalse((evidence/'prepare.claim.json').exists())
                for phase in ('prepare','cpu'):
                    with patch.object(sys,'stdin',io.StringIO(json.dumps(payload|{'phase':phase}))):prepare.main()
                wrong_head=True
                with patch.object(sys,'stdin',io.StringIO(json.dumps(payload|{'phase':'cpu'}))):
                    with self.assertRaisesRegex(ValueError,'Live repository'):prepare.main()
                self.assertEqual(imported.call_count,2)
                with patch.object(sys,'stdin',io.StringIO(json.dumps(payload|{'phase':'deploy-recovery'}))):
                    with self.assertRaisesRegex(ValueError,'existing run'):prepare.main()
            self.assertEqual(len(commands),2)
            if scheduled:
                frozen=json.loads((run/'configs/project.json').read_bytes())
                self.assertEqual(frozen['state'],'candidate');self.assertEqual(frozen['allowed_actions'],[])
            for folder in ('cpu','cpu-hf','cpu-torch'):self.assertIn(root/'tmp'/folder,ancestry)
            for phase in ('prepare','cpu'):
                self.assertEqual(json.loads((evidence/(phase+'.terminal.json')).read_bytes())['exit_code'],0)
                self.assertFalse(json.loads((evidence/(phase+'.claim.json')).read_bytes())['booking_claimed'])


if __name__=='__main__':unittest.main()
