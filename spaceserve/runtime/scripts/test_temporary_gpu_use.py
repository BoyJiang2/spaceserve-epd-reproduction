"""Conditional-use CPU mocks; no actual GPU query, signal or affinity mutation."""
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import temporary_gpu_use as temporary


class TemporaryTests(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory(prefix='temporary-use-test-', dir=Path(__file__).resolve().parent) as name:
            root = Path(name)
            (root/'evidence').mkdir(); (root/'configs').mkdir()
            user = temporary.QUOTE.encode()
            config = {'project':'spaceserve', 'host':'qjh003', 'uid':2147, 'gpu_devices':[2],
                      'gpu_uuids':[temporary.UUID], 'workload_cpu_affinity':list(range(90)),
                      'workload_numa_node':0, 'source_commit':'a'*40, 'source_manifest_sha256':'b'*64,
                      'temporary_gpu_use':{'schema':'temporary-idle-single-gpu-v1', 'start_ms':1000000,
                                           'end_ms':4600000, 'boot_id':temporary.BOOT,
                                           'user_sha256':hashlib.sha256(user).hexdigest()}}
            raw = json.dumps(config).encode()
            (root/'configs/project.json').write_bytes(raw)
            approved = {'passed':True, 'scope':'temporary-idle-GPU2-preflight-only',
                        'project_config_sha256':hashlib.sha256(raw).hexdigest(),
                        'source_commit':config['source_commit'], 'source_manifest_sha256':config['source_manifest_sha256'],
                        'user_sha256':config['temporary_gpu_use']['user_sha256'], 'allowed_actions':['numeric','model']}
            (root/'evidence/TEMPORARY_GPU_USE_USER.txt').write_bytes(user)
            for gate in ('G1','G2'):
                review = ('CPU-MOCK '+gate).encode()
                (root/'evidence'/('TEMPORARY_GPU_USE_'+gate+'.md')).write_bytes(review)
                approved[gate+'_review_sha256'] = hashlib.sha256(review).hexdigest()
            (root/'evidence/TEMPORARY_GPU_USE_APPROVED.json').write_text(json.dumps(approved))
            read_text = Path.read_text
            def read(path,*args,**kwargs):
                if path.as_posix()=='/proc/sys/kernel/random/boot_id': return temporary.BOOT
                return read_text(path,*args,**kwargs)
            with patch.object(temporary,'original',side_effect=lambda directory,filename:(directory/'evidence'/filename).read_bytes()), patch.object(temporary.socket,'gethostname',return_value='qjh003'), patch.object(temporary.os,'getuid',return_value=2147,create=True), patch.object(Path,'read_text',read):
                yield config,root

    def start(self,config,root,**kwargs):
        with patch.object(temporary.subprocess,'check_output',side_effect=[temporary.UUID+', 0, 0\n','']):
            return temporary.remaining(config,root,'numeric',fresh=True,wall=lambda:1100,clock=lambda:100,**kwargs)

    def test_start_separate_receipt_and_monotonic_no_extension(self):
        with self.fixture() as (config,root):
            self.assertEqual(self.start(config,root),3380)
            self.assertFalse((root/'evidence/BOOKING_VERIFIED.json').exists())
            self.assertFalse(json.loads((root/'evidence/TEMPORARY_GPU_USE_IDLE-numeric.json').read_bytes())['booking_claimed'])
            self.assertEqual(temporary.remaining(config,root,'numeric',wall=lambda:1000,clock=lambda:3200),280)
            with self.assertRaises(TimeoutError):temporary.remaining(config,root,'numeric',wall=lambda:1000,clock=lambda:3600)

    def test_wrong_scope_and_formal_or_epd_rejected(self):
        with self.fixture() as (config,root):
            for change in ({'project':'epd'},{'host':'other'},{'gpu_uuids':['wrong']},
                           {'gpu_devices':[0]},{'workload_numa_node':1},{'workload_cpu_affinity':[50]},
                           {'booking':{'CPU-MOCK':'actual booking cannot be mixed'}}):
                with self.subTest(change=change), self.assertRaises(ValueError):temporary.scope(config|change,'numeric')
            with self.assertRaises(ValueError):temporary.scope(config,'formal')
            for change in ({'end_ms':4600001},{'start_ms':True},{'boot_id':'wrong'}):
                bad=copy.deepcopy(config);bad['temporary_gpu_use'].update(change)
                with self.assertRaises(ValueError):temporary.scope(bad,'numeric')

    def test_expired_not_started_and_changed_grant_or_review(self):
        with self.fixture() as (config,root):
            with self.assertRaises(ValueError):temporary.remaining(config,root,'numeric',wall=lambda:1100,clock=lambda:100)
            for now in (999,4480,4600):
                with self.assertRaises(TimeoutError):temporary.remaining(config,root,'numeric',fresh=True,wall=lambda:now)
            for filename in ('TEMPORARY_GPU_USE_USER.txt','TEMPORARY_GPU_USE_G1.md','TEMPORARY_GPU_USE_G2.md'):
                path=root/'evidence'/filename;before=path.read_bytes();path.write_bytes(b'changed')
                with self.subTest(filename=filename),self.assertRaises(ValueError):self.start(config,root)
                path.write_bytes(before)

    def test_approval_config_and_deadline_tamper_refused(self):
        with self.fixture() as (config,root):
            path=root/'configs/project.json';before=path.read_bytes();path.write_bytes(b'{}')
            with self.assertRaises(ValueError):self.start(config,root)
            path.write_bytes(before);self.start(config,root)
            marker=root/'evidence/TEMPORARY_GPU_USE_STARTED.json';row=json.loads(marker.read_bytes());row['deadline_monotonic']+=1;marker.write_text(json.dumps(row))
            with self.assertRaises(ValueError):temporary.remaining(config,root,'numeric',wall=lambda:1100,clock=lambda:100)

    def test_busy_card_receipt_preserved(self):
        with self.fixture() as (config,root), patch.object(temporary.subprocess,'check_output',side_effect=[temporary.UUID+', 999, 100\n','555, '+temporary.UUID+'\n']):
            with self.assertRaises(RuntimeError):temporary.remaining(config,root,'numeric',fresh=True,wall=lambda:1100,clock=lambda:100)
            raw=json.loads((root/'evidence/TEMPORARY_GPU_USE_IDLE-numeric.json').read_bytes())
            self.assertEqual(raw['processes'][0]['pid'],555)

    def test_query_error_keeps_raw(self):
        with patch.object(temporary.subprocess,'check_output',return_value='unparsed\n'):
            row=temporary.process_rows();self.assertEqual(row['raw'],'unparsed\n');self.assertIn('query_error',row)
        with patch.object(temporary.subprocess,'check_output',side_effect=subprocess.TimeoutExpired('nvidia-smi',.5,output=b'partial')):
            row=temporary.process_rows();self.assertEqual(row['raw'],'partial');self.assertIn('query_error',row)

    def test_monitor_foreign_only_signals_itself_and_preserves_trigger(self):
        with self.fixture() as (config,root):
            signalled=threading.Event()
            with patch.object(temporary,'remaining',return_value=3000), patch.object(temporary,'process_rows',return_value={'raw':'555, GPU\n','processes':[{'pid':555,'gpu_uuid':temporary.UUID}]}), patch.object(temporary,'owned_process',side_effect=RuntimeError('foreign')), patch.object(temporary.os,'kill',side_effect=lambda *a:signalled.set()) as kill:
                with self.assertRaises(RuntimeError):
                    with temporary.supervise(config,root,'numeric'):self.assertTrue(signalled.wait(1))
                kill.assert_called_once_with(os.getpid(),signal.SIGTERM)
            trigger=(root/'evidence/TEMPORARY_GPU_USE_MONITOR-numeric.jsonl').read_text()
            self.assertIn('555',trigger);self.assertIn('foreign',trigger)

    def test_monitor_query_failure_and_revoked_grant_stop(self):
        for revoked in (False,True):
            with self.subTest(revoked=revoked),self.fixture() as (config,root):
                signalled=threading.Event()
                checks=[3000,RuntimeError('authorization changed')] if revoked else [3000,3000]
                with patch.object(temporary,'remaining',side_effect=checks),patch.object(temporary,'process_rows',return_value={'raw':'partial','processes':[],'query_error':'timeout'}),patch.object(temporary.os,'kill',side_effect=lambda *a:signalled.set()) as kill:
                    with self.assertRaises(RuntimeError):
                        with temporary.supervise(config,root,'model'):self.assertTrue(signalled.wait(1))
                    kill.assert_called_once_with(os.getpid(),signal.SIGTERM)

    def test_legacy_monitor_has_no_side_effect(self):
        with patch.object(temporary,'process_rows') as query,patch.object(temporary.os,'kill') as kill:
            with temporary.supervise({},Path('unused'),'formal'):pass
            query.assert_not_called();kill.assert_not_called()

    def test_owned_identity_reuse_and_private_mps(self):
        with self.fixture() as (config,root):
            environment={'EXP_ROOT':str(root),'REPRO_RUN_ID':str(root)+':fixture'}
            process=SimpleNamespace(pid=555,create_time=lambda:10,uids=lambda:SimpleNamespace(real=2147),
                                    environ=lambda:environment,name=lambda:'python',cwd=lambda:str(root))
            api=SimpleNamespace(Process=lambda pid:process)
            with patch.dict(sys.modules,psutil=api):
                self.assertEqual(temporary.owned_process({'pid':555},root)['created_epoch'],10)
                api.Process=lambda pid:SimpleNamespace(**{**vars(process),'create_time':lambda:20})
                first=True
                def reused(pid):
                    nonlocal first
                    if first:first=False;return process
                    return SimpleNamespace(**{**vars(process),'create_time':lambda:20})
                api.Process=reused
                with self.assertRaisesRegex(RuntimeError,'identity changed'):temporary.owned_process({'pid':555},root)
                api.Process=lambda pid:process
                process.name=lambda:'nvidia-cuda-mps-server'
                environment.update(CUDA_MPS_PIPE_DIRECTORY=str(root/'tmp/mps'),REPRO_MPS_OWNER='fixture-token')
                state=root/'evidence/mps-owner.json';state.write_text(json.dumps({'state':'running','token':'fixture-token'}))
                with self.assertRaisesRegex(RuntimeError,'MPS'):temporary.owned_process({'pid':555},root)
                pipe=root/'tmp/mps';pipe.mkdir(parents=True);(pipe/'control').write_bytes(b'CPU-MOCK')
                environment['CUDA_VISIBLE_DEVICES']=temporary.UUID
                daemon=SimpleNamespace(pid=556,create_time=lambda:11,uids=process.uids,environ=process.environ,
                                       name=lambda:'nvidia-cuda-mps-control')
                process.parents=lambda:[daemon]
                api.Process=lambda pid:daemon if pid==556 else process
                bound={'state':'running','token':'fixture-token','pid':556,'created':11,
                       'pipe':str(pipe),'uuid':temporary.UUID,'control_inode':(pipe/'control').stat().st_ino}
                state.write_text(json.dumps(bound))
                temporary.owned_process({'pid':555},root)
                for change in ({'created':12},{'uuid':'other'},{'pipe':'other'},{'control_inode':-1}):
                    state.write_text(json.dumps(bound|change))
                    with self.subTest(change=change),self.assertRaisesRegex(RuntimeError,'MPS'):temporary.owned_process({'pid':555},root)
                state.write_text(json.dumps(bound));process.parents=lambda:[]
                with self.assertRaisesRegex(RuntimeError,'MPS'):temporary.owned_process({'pid':555},root)
                process.parents=lambda:[daemon]
                environment['REPRO_MPS_OWNER']='other'
                with self.assertRaisesRegex(RuntimeError,'MPS'):temporary.owned_process({'pid':555},root)

    def test_booking_dispatch_requires_explicit_temporary_config(self):
        import booking_window
        with patch.object(booking_window,'CONFIG',SimpleNamespace(config={'temporary_gpu_use':{'CPU-MOCK':True}})),patch.dict(os.environ,REPRO_PHASE='numeric'),patch.object(temporary,'remaining',return_value=123) as grant:
            self.assertEqual(booking_window.require(fresh=True),123)
            grant.assert_called_once_with(booking_window.CONFIG.config,booking_window.ROOT,'numeric',fresh=True)


if __name__=='__main__':unittest.main()
