"""CPU-MOCK supervisor control tests; never original GPU admission/evidence."""
import copy
import hashlib
import json
import os
from pathlib import Path
import queue
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import MagicMock, Mock, patch

import numeric_controller as controller
from numeric_parent_backend import NumericParentBackend


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.c = object.__new__(controller.NativeController)
        self.c.output = self.root; self.c.config = dict(uid=os.getuid(),gpu_uuids=['A','B','C'],max_idle_bytes=1024)
        self.c.claim = NS(deadline=1800, resources={'gpus':{u:{'capacity_bytes':10000} for u in ['A','B','C']}})
        self.c.record = Mock(); self.c.proc = Mock(exists=Mock(return_value=False))
        self.c.driver = Mock(pid=100, poll=Mock(return_value=-15), returncode=-15)
        self.c.driver_identity = None; self.c.check = Mock(); self.c.poll = Mock(); self.c.reap = Mock()
        self.original = dict(pid=123, uid=os.getuid(), proc_start_ticks=20, boot_id='CPU-MOCK-boot',
            cwd=str(self.root), ppid=99, exe='/CPU-MOCK-python', argv=['CPU-MOCK-worker'],
            environment={'EXP_ROOT':str(self.root),'REPRO_RUN_ID':'CPU-MOCK-run'})
        self.submitted = dict(actor_id='a'*32,job_id='b'*8,namespace='CPU-MOCK-run',name='native-g0-n0',detached=True)
        self.c.submissions = {'native-g0-n0':self.submitted}
        self.c.actor_processes = {'native-g0-n0':copy.deepcopy(self.original)}
        self.c.backend = NS(creating={'name':'native-g0-n0'})
        self.c.reader = Mock(read=Mock(return_value=dict(state='DEAD',pid=123)))
        self.c.idle = Mock(return_value={'CPU-MOCK-raw-idle':True})
        self.c.release = Mock(known_identities=Mock(return_value=[]),known={})
        self.c.collector = Mock(known={123:copy.deepcopy(self.original)},
            same_identity=controller.HeadDescendants.same_identity)
        self.c.channel = None; self.c.processes = []; self.c.cleaning = False
        self.c.bootstrap = {}; self.c.samples = queue.Queue(); self.c.root = self.root
        self.c.run_id = 'CPU-MOCK-run'

    def test_original_creation_quiescence_before_pending_is_cleared(self):
        pending = self.c.backend.creating
        self.c.resolve_pending()
        self.assertIsNone(self.c.backend.creating)
        event = self.c.record.call_args
        self.assertEqual(event.args[0],'creation_quiescence_confirmed')
        self.assertEqual(event.kwargs['pending'],pending)
        self.assertEqual(event.kwargs['original'],self.original)
        self.assertTrue(event.kwargs['original_PID_absent'])

    def test_pending_retained_on_every_missing_original_quiescence_fact(self):
        for mutate in [lambda:self.c.actor_processes.clear(), lambda:self.c.submissions.clear(),
                       lambda:self.c.driver.poll.configure_mock(return_value=None),
                       lambda:self.c.proc.exists.configure_mock(return_value=True),
                       lambda:self.c.reader.read.configure_mock(return_value=dict(state='DEAD',pid=0)),
                       lambda:self.c.reader.read.configure_mock(return_value=dict(state='ALIVE',pid=123)),
                       lambda:self.c.idle.configure_mock(side_effect=RuntimeError('CPU-MOCK context retained'))]:
            self.setUp(); mutate()
            with self.assertRaises(RuntimeError): self.c.resolve_pending()
            self.assertIsNotNone(self.c.backend.creating)
            self.assertFalse(any(c.args[0]=='creation_quiescence_confirmed' for c in self.c.record.call_args_list))

    def test_pending_or_unreleased_actor_prevents_head_signals(self):
        for pending in (True,False):
            self.setUp()
            if pending:self.c.actor_processes.clear()
            else:
                self.c.backend.creating=None
                self.c.release.known_identities.return_value=[{'CPU-MOCK-unconfirmed-importer':True}]
            with patch.object(controller,'terminate') as stop:
                with self.assertRaises(RuntimeError): self.c.cleanup()
                stop.assert_not_called()

    def test_gcs_dead_without_original_process_never_authorizes_head_stop(self):
        self.c.backend.creating=None; self.c.actor_processes.clear()
        with patch.object(controller,'terminate') as stop:
            with self.assertRaisesRegex(RuntimeError,'never observed'): self.c.cleanup()
            stop.assert_not_called()

    def test_original_driver_exit_required_before_head_cleanup(self):
        self.c.driver_identity=copy.deepcopy(self.original)
        self.c.proc.exists.return_value=True
        with patch.object(controller,'terminate') as stop:
            with self.assertRaisesRegex(RuntimeError,'driver still present'): self.c.cleanup()
            self.assertEqual(stop.call_count,1)
            self.assertEqual(stop.call_args.args[0],self.original)

    def sample(self, *, pid=123, uuid='A', identity=None):
        raw = {u:dict(capacity_bytes=10000, used_bytes=0, processes=[]) for u in ['A','B','C']}
        raw[uuid]['processes']=[{'pid':pid}]
        observations = {u:{} for u in raw}; observations[uuid][str(pid)]={'identity':identity or copy.deepcopy(self.original)}
        return dict(gpus=raw,process_observations=observations)

    def test_sample_binds_original_identity_even_after_original_process_exited(self):
        self.c.backend.creating=None
        self.c.release.known={(123,20):dict(pid=123,proc_start_ticks=20,gpu_uuid='A')}
        self.c.samples.put(self.sample()); self.c.consume_samples()
        self.assertEqual(self.c.bootstrap[123]['gpu_uuid'],'A')
        self.c.collector.stable.assert_not_called()

    def test_unknown_extra_driver_or_reused_pid_refused_without_signal(self):
        for sample in [self.sample(pid=999),self.sample(pid=100),
                       self.sample(identity={**self.original,'proc_start_ticks':999})]:
            self.c.samples.put(sample)
            with self.assertRaises(ValueError): self.c.consume_samples()

    def test_same_process_cannot_change_actual_gpu_uuid(self):
        self.c.samples.put(self.sample()); self.c.consume_samples()
        self.c.samples.put(self.sample(uuid='B'))
        with self.assertRaisesRegex(ValueError,'UUID changed'):self.c.consume_samples()

    def test_unbound_bootstrap_worker_refused_before_business_rpc(self):
        self.c.samples.put(self.sample()); self.c.consume_samples()
        self.c.backend.creating=None
        self.c.samples.put(dict(gpus={u:dict(capacity_bytes=10000,used_bytes=0,processes=[]) for u in ['A','B','C']},
                                process_observations={u:{} for u in ['A','B','C']}))
        with self.assertRaisesRegex(ValueError,'never bound'):self.c.consume_samples()

    def test_empty_owned_driver_journal_is_not_a_broken_claim(self):
        (self.root/'driver-events.jsonl').write_bytes(b'')
        self.c.events_seen=0; self.c.driver_events()
        self.c.record.assert_not_called()

    def test_original_submission_is_durably_transcribed_and_not_duplicated(self):
        self.c.submissions.clear(); self.c.events_seen=0; self.c.release.scope={'CPU-MOCK':True}
        intent=dict(namespace=self.c.run_id,name='native-g0-n0',group=0,slot=0,allowed_gpu_uuids=['A','B','C'],scope=self.c.release.scope)
        line=json.dumps(dict(event='numeric_driver_actor_submitted',intent=intent,submitted=self.submitted))+'\n'
        path=self.root/'driver-events.jsonl'; path.write_text(line,encoding='utf8')
        self.c.driver_events(); self.assertEqual(self.c.events_seen,1)
        self.assertEqual(self.c.submissions['native-g0-n0'],self.submitted)
        self.c.driver_events(); self.assertEqual(self.c.record.call_count,1)
        path.write_text(line+line,encoding='utf8')
        with self.assertRaises(ValueError):self.c.driver_events()

    def test_sampler_exit_race_keeps_original_binding_without_granting_context_release(self):
        registered={**self.original,'gpu_uuid':'A'}
        self.c.release.known={(123,20):registered}
        self.c.proc.snapshot.side_effect=FileNotFoundError('CPU-MOCK PID gone after NVML')
        self.c.proc.boot.return_value='CPU-MOCK-boot'
        receipt=self.c.sample_process(123,'A')
        self.assertFalse(receipt['release_or_context_quiescence_granted'])
        self.assertFalse(receipt['proc_observation']['exists'])
        self.assertEqual(self.c.proc.exists.call_count,2)
        sample=self.sample();sample['process_observations']['A']['123']=receipt
        self.c.samples.put(sample);self.c.backend.creating=None
        self.c.consume_samples()
        self.assertEqual(self.c.bootstrap[123]['identity'],self.original)

    def test_sampler_exit_race_rejects_unknown_reused_foreign_or_changed_boot(self):
        self.c.proc.snapshot.side_effect=FileNotFoundError('CPU-MOCK vanished')
        with self.assertRaises(FileNotFoundError):self.c.sample_process(123,'A')
        self.c.release.known={(123,20):{**self.original,'gpu_uuid':'A'}}
        self.c.proc.exists.return_value=True
        with self.assertRaises(FileNotFoundError):self.c.sample_process(123,'A')
        self.c.proc.exists.return_value=False;self.c.proc.boot.return_value='CPU-MOCK-other-boot'
        with self.assertRaises(FileNotFoundError):self.c.sample_process(123,'A')
        self.c.proc.snapshot.side_effect=PermissionError('CPU-MOCK cannot inspect')
        with self.assertRaises(PermissionError):self.c.sample_process(123,'A')

    def test_final_inventory_allows_only_pinned_control_service_permission_exception(self):
        candidate=MagicMock();candidate.name=str(os.getpid()+1000)
        candidate.stat.return_value=NS(st_uid=self.c.config['uid'])
        candidate.__truediv__.return_value.resolve.side_effect=PermissionError('CPU-MOCK protected cwd')
        procroot=NS(iterdir=lambda:[candidate])
        with patch.object(controller,'Path',return_value=procroot), \
                patch.object(controller,'control_service_exception',return_value={'CPU-MOCK-verified':True}) as proof:
            self.assertEqual(self.c.scope_inventory(),[])
            proof.assert_called_once_with(procroot,int(candidate.name))
            self.assertEqual(self.c.record.call_args.args[0],'numeric_verified_control_service_exception')
            self.assertIn('no signalling',self.c.record.call_args.kwargs['scope'])
        with patch.object(controller,'Path',return_value=procroot), \
                patch.object(controller,'control_service_exception',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'cwd unconfirmed'):self.c.scope_inventory()

    def test_actual_source_census_before_after_preserves_changed_file_as_failure(self):
        checkout=self.root/'repo';checkout.mkdir();source=checkout/'CPU-MOCK.py';source.write_bytes(b'CPU-MOCK-original')
        manifest={'files':[{'path':'CPU-MOCK.py','git_path':'CPU-MOCK.py',
            'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}]}
        raw=json.dumps(manifest).encode();(self.root/'manifest.json').write_bytes(raw)
        self.c.layout=NS(checkout=checkout)
        self.c.inputs={'source_manifest_file':'manifest.json','source_manifest_sha256':hashlib.sha256(raw).hexdigest()}
        self.c.claim.owner=self.root/'inputs.json';self.c.claim.deployed={'CPU-MOCK-commit':'original'}
        with patch.object(controller,'verify_checkout',return_value=self.c.claim.deployed):
            self.c.source_snapshot('before')
            source.write_bytes(b'CPU-MOCK-edited')
            with self.assertRaisesRegex(ValueError,'source closure verification failed'):self.c.source_snapshot('after')
        before=json.loads((self.root/'source-before.json').read_text(encoding='utf8'))
        after=json.loads((self.root/'source-after.json').read_text(encoding='utf8'))
        self.assertEqual(before['errors'],[]);self.assertIn('changed:CPU-MOCK.py',after['errors'])
        self.assertNotEqual(after['files'][0]['sha256'],after['files'][0]['expected_sha256'])


class AdmissionAndObservationTests(unittest.TestCase):
    def test_original_authorization_failure_precedes_nvml_and_spawn(self):
        with patch.object(controller,'authorize',side_effect=ValueError('CPU-MOCK candidate')), \
                patch.object(controller,'NvmlBackend') as nvml, patch.object(controller.subprocess,'Popen') as spawn:
            with self.assertRaises(ValueError):controller.run({}, {}, '/CPU-MOCK/inputs.json','/CPU-MOCK/template')
            nvml.assert_not_called(); spawn.assert_not_called()

    def test_parent_observer_cannot_replace_original_claim_checks(self):
        claim=NS(config={'gpu_uuids':['A','B','C'],'cleanup_seconds':120},inputs={'run_id':'CPU-MOCK'},
                 deadline=1800,check=Mock())
        observer=Mock(); backend=NumericParentBackend(claim,Mock(),Mock(),clock=lambda:1,observe=observer)
        backend.check(); claim.check.assert_called_once(); observer.assert_called_once()
        claim.check.side_effect=TimeoutError('CPU-MOCK original deadline')
        with self.assertRaises(TimeoutError):backend.check()
        self.assertEqual(observer.call_count,1)

    def test_sampler_keeps_raw_before_identity_error_and_never_hides_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            c=object.__new__(controller.NativeController); c.output=Path(temp)
            c.config={'gpu_uuids':['A'],'uid':os.getuid()}; c.cleaning=False
            c.stop=Mock(is_set=Mock(return_value=False)); c.sample_errors=[]; c.samples=queue.Queue()
            c.nvml=Mock(version={'provider':'CPU-MOCK'},read=Mock(return_value={
                'capacity_bytes':100,'used_bytes':1,'processes':[{'pid':123}]}))
            c.proc=Mock(snapshot=Mock(side_effect=ValueError('CPU-MOCK foreign UID')))
            c.sampling()
            lines=(c.output/'nvml-raw.jsonl').read_text(encoding='utf8').splitlines()
            self.assertEqual(len(lines),1);self.assertEqual(json.loads(lines[0])['gpus']['A']['processes'],[{'pid':123}])
            self.assertEqual(len(c.sample_errors),1);self.assertTrue(c.samples.empty())

    def test_sampler_before_backend_persists_idle_raw_without_filling_rpc_queue(self):
        with tempfile.TemporaryDirectory() as temp:
            c=object.__new__(controller.NativeController); c.output=Path(temp)
            c.config={'gpu_uuids':['A'],'uid':os.getuid()}; c.cleaning=False; c.backend=None
            c.claim=NS(resources={'gpus':{'A':{'capacity_bytes':100}}})
            c.stop=Mock(is_set=Mock(side_effect=[False,True])); c.sample_ready=Mock()
            c.sample_errors=[]; c.samples=queue.Queue()
            c.nvml=Mock(version={'provider':'CPU-MOCK'},read=Mock(return_value={
                'capacity_bytes':100,'used_bytes':1,'processes':[]})); c.proc=Mock()
            c.sampling()
            self.assertEqual(c.sample_errors,[]);self.assertTrue(c.samples.empty())
            c.sample_ready.set.assert_called_once()
            self.assertEqual(len((c.output/'nvml-raw.jsonl').read_text(encoding='utf8').splitlines()),2)

    def test_sampling_survives_registered_actor_exit_without_claiming_context_release(self):
        with tempfile.TemporaryDirectory() as temp:
            c=object.__new__(controller.NativeController);c.output=Path(temp)
            c.config={'gpu_uuids':['A'],'uid':os.getuid()};c.cleaning=False;c.backend=Mock()
            c.claim=NS(resources={'gpus':{'A':{'capacity_bytes':100}}})
            c.stop=Mock(is_set=Mock(side_effect=[False,True]));c.sample_ready=Mock()
            c.sample_errors=[];c.samples=queue.Queue()
            c.nvml=Mock(version={'provider':'CPU-MOCK'},read=Mock(return_value={
                'capacity_bytes':100,'used_bytes':1,'processes':[{'pid':123}]}))
            c.release=NS(known={(123,20):dict(pid=123,proc_start_ticks=20,gpu_uuid='A',boot_id='CPU-MOCK-boot')})
            c.proc=Mock(snapshot=Mock(side_effect=FileNotFoundError('CPU-MOCK exit')),
                exists=Mock(return_value=False),boot=Mock(return_value='CPU-MOCK-boot'))
            c.sampling()
            self.assertEqual(c.sample_errors,[]);self.assertEqual(c.samples.qsize(),1)
            lines=(c.output/'nvml-raw.jsonl').read_text(encoding='utf8').splitlines()
            observation=json.loads(lines[1])['process_observations']['A']['123']
            self.assertEqual(observation['state'],'original_registered_PID_absent_after_NVML')
            self.assertFalse(observation['release_or_context_quiescence_granted'])


if __name__=='__main__':unittest.main()
