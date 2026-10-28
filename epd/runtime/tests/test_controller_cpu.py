"""v12 controller test SOURCE ONLY, UNEXECUTED. CPU mocks never authorize hardware."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiment_plan import candidate_id, config_sha256, qualification_schedule
import fixed_unit
import preflight_controller as controller
import production_identity as identity
from test_preflight_v5 import Fixture


class FixedVectorCPU(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(os.environ["EPD_CPU_TEST_TMP"]).resolve(strict=True))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = {"root": str(self.root), "gpu_uuids": ["CPU-MOCK-uuid0", "CPU-MOCK-uuid1", "CPU-MOCK-uuid2"]}
        manifest = self.root / 'manifest.json'; manifest.write_text('{"CPU-MOCK":true}')
        self.candidate = ('replicas', 0, 0, 4)
        self.spec = {"schema": "epd-fixed-unit-v1", "source_manifest_sha256": 'a'*64,
            "phase": "qualification", "unit": candidate_id(self.candidate), "candidate": candidate_id(self.candidate),
            "candidate_config_sha256": config_sha256(self.candidate), "max_requests": 15, "wall_seconds": 300,
            "request_diagnostics": True, "runtime_binding_sha256": 'b'*64, "model": '/CPU-MOCK/MiniCPM-V-2_6',
            "dataset": str(self.root), "rgb_manifest": str(manifest),
            "rgb_manifest_sha256": fixed_unit.hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "urls": ['http://127.0.0.1:' + str(port) for port in (17780,17781,17782)], "batches": []}
        dispatch = 0
        for case in qualification_schedule():
            if case['candidate'] != self.spec['candidate']: continue
            requests = []
            for index in range(case['requests']):
                requests.append({"fixture_id": 'CPU-MOCK-' + str(dispatch), "dispatch_index": dispatch,
                    "input": {"prompt": 'CPU-MOCK-prompt', "images": [{"path": str(self.root/'CPU-MOCK-image.png'),
                    "rgb_sha256": 'c'*64}] * case['images']}})
                dispatch += 1
            self.spec['batches'].append({"case":case['case'],"images":case['images'],"tokens":case['tokens'],
                "concurrency":case['concurrency'],"warmup":False,"requests":requests})
        self.spec['servers'] = fixed_unit.official_servers(self.spec, self.config)

    def test_exact_fifteen_vector_and_three_official_single_uuid_servers(self):
        self.assertEqual(fixed_unit.validate_spec(self.spec, self.config, 'a'*64), 15)
        self.assertEqual([server['CUDA_VISIBLE_DEVICES'] for server in self.spec['servers']], self.config['gpu_uuids'])
        self.assertTrue(all('baseline_server.py' in server['argv'][1] for server in self.spec['servers']))

    def test_argv_extra_request_wrong_profile_or_dispatch_rejected(self):
        for mode in ('argv','extra','profile','dispatch','diagnostic'):
            spec = copy.deepcopy(self.spec)
            if mode == 'argv': spec['servers'][0]['argv'].append('--unapproved')
            elif mode == 'extra': spec['batches'][0]['requests'].append(copy.deepcopy(spec['batches'][0]['requests'][0]))
            elif mode == 'profile': spec['candidate_config_sha256'] = 'f'*64
            elif mode == 'dispatch': spec['batches'][0]['requests'][0]['dispatch_index'] = 1
            else: spec['request_diagnostics'] = False
            with self.subTest(mode=mode), self.assertRaises(ValueError): fixed_unit.validate_spec(spec,self.config,'a'*64)

    def test_unimplemented_numeric_and_restart_stop_before_claim(self):
        for phase in ('numeric','selected_g3'):
            spec = copy.deepcopy(self.spec)
            spec.update(phase=phase, unit='numeric' if phase=='numeric' else 'replicas')
            with self.assertRaises(NotImplementedError): fixed_unit.validate_spec(spec,self.config,'a'*64)

    def test_candidate_gpu_scope_refused_before_nvml_or_popen(self):
        with patch.object(controller, 'NvmlBackend') as nvml, patch.object(controller.subprocess, 'Popen') as spawn:
            with self.assertRaises(ValueError): controller.authorize({'schema':'epd-preflight-static-v1','state':'candidate'}, {}, None)
            nvml.assert_not_called(); spawn.assert_not_called()

    def test_startup_registration_independent_of_request_diagnostics(self):
        with patch.dict(os.environ, {'REPRO_IDENTITY':'1','REPRO_REQUEST_IDENTITY':'0'}):
            self.assertTrue(identity.enabled()); self.assertFalse(identity.requests_enabled())
        with patch.dict(os.environ, {'REPRO_IDENTITY':'0','REPRO_REQUEST_IDENTITY':'1'}):
            with self.assertRaises(ValueError): identity.requests_enabled()

    def test_unknown_identity_refused_without_signal(self):
        from types import SimpleNamespace
        proc = SimpleNamespace(identity=lambda *args: (_ for _ in ()).throw(ValueError('CPU-MOCK-unknown')))
        with patch.object(controller.os,'kill') as kill:
            result = controller.stop_owned({'pid':123}, {}, 'CPU-MOCK-run', proc, controller.time.perf_counter()+1)
            self.assertEqual(result['state'],'identity_unknown_refused'); kill.assert_not_called()


class BoundClaimCPU(Fixture):
    def controller_layout(self):
        template=self.root/'CPU-MOCK-template.json';template.write_text(json.dumps({'phase':'qualification'}))
        layout=types.SimpleNamespace(host_lock=self.root/'CPU-MOCK-host.lock',require_scope=lambda phase:None)
        return layout,template

    def test_expired_future_wrong_or_short_booking_never_constructs_nvml(self):
        layout,template=self.controller_layout()
        for mode in ('expired','future','wrong_ticket','wrong_owner','short','before_window'):
            config,inputs=copy.deepcopy(self.config),copy.deepcopy(self.inputs)
            raw=self.booking(self.now)
            if mode=='expired':config['authorized_end_ms']=self.now-1
            elif mode=='future':raw['observed_ms']=self.now+1
            elif mode=='wrong_ticket':raw['bookings'][0]['id']='CPU-MOCK-wrong'
            elif mode=='wrong_owner':raw['bookings'][0]['user']='CPU-MOCK-other'
            elif mode=='short':config['authorized_end_ms']=self.now+300000
            else:config['authorized_start_ms']=self.now+1
            desc=self.write('booking-'+mode+'.json',raw)
            inputs.update(booking_file=desc['path'],booking_sha256=desc['sha256'])
            with self.subTest(mode=mode),patch.object(controller,'authorize',return_value={}), \
                 patch.object(controller,'paths_for',return_value=layout), \
                 patch.object(controller,'load_execution',return_value={'wall_seconds':300}), \
                 patch.object(controller,'booking_for_unit',wraps=controller.booking_for_unit) as booking, \
                 patch.object(controller,'NvmlBackend') as backend,patch.object(controller,'Claim') as claim, \
                 patch.object(controller.time,'time',return_value=self.now/1000):
                with self.assertRaises(ValueError):controller.run(config,inputs,self.owner,template)
                booking.assert_called_once();backend.assert_not_called();claim.assert_not_called()

    def test_valid_booking_reaches_mock_backend_only_after_booking_check(self):
        layout,template=self.controller_layout()
        with patch.object(controller,'authorize',return_value={}),patch.object(controller,'paths_for',return_value=layout), \
             patch.object(controller,'load_execution',return_value={'wall_seconds':300}), \
             patch.object(controller,'booking_for_unit',wraps=controller.booking_for_unit) as booking, \
             patch.object(controller,'NvmlBackend',side_effect=RuntimeError('CPU-MOCK stop before hardware')) as backend, \
             patch.object(controller,'Claim') as claim,patch.object(controller.time,'time',return_value=self.now/1000):
            with self.assertRaisesRegex(RuntimeError,'CPU-MOCK stop before hardware'):
                controller.run(self.config,self.inputs,self.owner,template)
            booking.assert_called_once();backend.assert_called_once();claim.assert_not_called()

    def test_actual_posix_claim_binds_execution_and_rejects_tampering(self):
        claim = self.claim()
        execution = {"schema":"epd-fixed-unit-v1","phase":"numeric","unit":"numeric","candidate":None,
                     "source_manifest_sha256":self.source_sha,"argv":["CPU-MOCK-never-spawn"],"vector":[]}
        with patch('preflight_guard.time.time',return_value=self.now/1000):
            claim.reserve(self.data/'CPU-MOCK-ledger.json', execution)
            claim.verify_reservation()
            path = Path(claim.reservation_receipt['claim'])
            raw = json.loads(path.read_bytes()); raw['execution']['argv']=['CPU-MOCK-tampered']
            path.write_text(json.dumps(raw))
            with self.assertRaises(ValueError): claim.verify_reservation()

    def test_missing_or_wrong_execution_scope_never_claims(self):
        claim=self.claim()
        with patch('preflight_guard.time.time',return_value=self.now/1000), self.assertRaises(ValueError):
            claim.reserve(self.data/'CPU-MOCK-ledger.json', {"schema":"CPU-MOCK-wrong"})
        self.assertFalse((self.data/'CPU-MOCK-ledger.json').exists())


async def journal_fixture(directory, cancel_locally=False):
    """Fake HTTP transport only; actual async cancellation/signals, no sockets or GPU."""
    import asyncio
    import hashlib
    from types import SimpleNamespace as NS
    directory = Path(directory)
    image = str(directory / 'CPU-MOCK-image.png')
    item = lambda index: {'fixture_id':str(index),'dispatch_index':index,
        'input':{'prompt':'CPU-MOCK', 'images':[{'path':image,'rgb_sha256':'c'*64}]}}
    spec = {'phase':'qualification','candidate':'CPU-MOCK','max_requests':2,'request_diagnostics':False,
        'urls':['http://127.0.0.1:1'],'batches':[{'case':'CPU-MOCK','images':1,'tokens':1,
        'concurrency':1,'warmup':False,'requests':[item(0),item(1)]}]}
    claim = {'execution':spec,'execution_sha256':fixed_unit.digest(spec),
             'timing':{'deadline_monotonic':fixed_unit.time.perf_counter()+30}}
    path=directory/'CPU-MOCK-claim.json';path.write_text(json.dumps(claim))
    runtime={'claim':{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},
        'stop_file':str(directory/'STOP'),'unit_id':'CPU-MOCK-unit','run_id':'CPU-MOCK-run','uid':0,
        'rgb_by_path':{image:'c'*64},'clock_scope':{'host':'CPU-MOCK','boot_id':'CPU-MOCK','run_id':'CPU-MOCK-run'}}
    waiting=asyncio.Event()
    class Response:
        status=200
        async def read(self):
            return json.dumps({'processed_prompt_token_ids':[1],'output_token_ids':[2],
                'timestamps':[fixed_unit.time.perf_counter()]}).encode()
    class Context:
        def __init__(self,index):self.index=index
        async def __aenter__(self):
            if self.index==1:
                waiting.set();(directory/'waiting-HTTP').write_text('CPU-MOCK waiting inside POST')
                await asyncio.Future()
            return Response()
        async def __aexit__(self,*args):pass
    class Session:
        def __init__(self,*args,**kwargs):self.index=0
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        def post(self,*args,**kwargs):
            context=Context(self.index);self.index+=1;return context
    transport=NS(ClientSession=Session,TCPConnector=lambda **kwargs:None,ClientTimeout=lambda **kwargs:None)
    with patch.dict(sys.modules,{'aiohttp':transport}):
        task=asyncio.create_task(fixed_unit.run_client(spec,runtime,directory))
        if cancel_locally:
            await waiting.wait();task.cancel()
        return await task


class SubmittedJournalCPU(unittest.TestCase):
    def assert_journal(self,directory):
        events=[json.loads(line) for line in (directory/'request-events.jsonl').read_text().splitlines()]
        self.assertEqual([e['event'] for e in events if e['request_id']=='0'],['submitted','http_body','complete'])
        self.assertEqual([e['event'] for e in events if e['request_id']=='1'],['submitted','cancelled'])
        first=next(e for e in events if e['event']=='http_body')
        import base64
        self.assertEqual(json.loads(base64.b64decode(first['body_base64']))['output_token_ids'],[2])
        rows=[json.loads(line) for line in (directory/'requests.jsonl').read_text().splitlines()]
        self.assertEqual([r['status'] for r in rows],['complete','cancelled'])

    def test_first_success_then_second_cancel_is_preserved_and_propagated(self):
        import asyncio
        with tempfile.TemporaryDirectory(dir=os.environ['EPD_CPU_TEST_TMP']) as folder:
            directory=Path(folder)
            with self.assertRaises(asyncio.CancelledError):asyncio.run(journal_fixture(directory,cancel_locally=True))
            self.assert_journal(directory)

    def test_real_TERM_while_waiting_HTTP_preserves_submission_and_cancellation(self):
        import signal,subprocess,time
        with tempfile.TemporaryDirectory(dir=os.environ['EPD_CPU_TEST_TMP']) as folder:
            directory=Path(folder).resolve()
            command=[sys.executable,'-I','-S','-B','-c',
                'import asyncio,sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2]);from test_controller_cpu import journal_fixture;asyncio.run(journal_fixture(Path(sys.argv[3])))',
                str(ROOT),str(ROOT/'tests'),str(directory)]
            process=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                deadline=time.monotonic()+10
                while not (directory/'waiting-HTTP').exists() and time.monotonic()<deadline:
                    if process.poll() is not None:self.fail('CPU HTTP fixture exited before POST wait')
                    time.sleep(.01)
                self.assertTrue((directory/'waiting-HTTP').exists())
                process.send_signal(signal.SIGTERM)
                self.assertNotEqual(process.wait(timeout=10),0)
                self.assert_journal(directory)
            finally:
                if process.poll() is None:
                    process.terminate();process.wait(timeout=10)


class CleanupIsolationCPU(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ['EPD_CPU_TEST_TMP'])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {'root': str(self.root), 'gpu_uuids': ['CPU-MOCK-uuid']}
        self.owned = {pid: {'pid': pid, 'proc_start_ticks': pid + 100} for pid in (1, 2)}
        from unittest.mock import Mock
        self.backend = Mock()
        self.backend.read.return_value = {'processes': []}

    def cleanup(self):
        return controller.cleanup_owned(self.owned, self.config, 'CPU-MOCK-run', None,
                                        1000, {}, self.backend, {})

    def test_discovery_failure_still_cleans_known_siblings_and_stays_unconfirmed(self):
        with patch.object(controller, 'descendants', side_effect=ValueError('identity changed')), \
             patch.object(controller, 'stop_owned', side_effect=lambda saved, *args: {'identity': saved, 'state': 'gone'}) as stop:
            rows = self.cleanup()
        self.assertEqual([call.args[0]['pid'] for call in stop.call_args_list], [2, 1])
        self.assertEqual([row['state'] for row in rows], ['descendants_unconfirmed', 'gone', 'gone'])

    def test_one_stop_error_does_not_abandon_next_verified_sibling(self):
        with patch.object(controller, 'descendants'), \
             patch.object(controller, 'stop_owned', side_effect=[PermissionError('fixture refusal'), {'state': 'gone'}]) as stop:
            rows = self.cleanup()
        self.assertEqual([call.args[0]['pid'] for call in stop.call_args_list], [2, 1])
        self.assertEqual([row['state'] for row in rows], ['cleanup_unknown_unconfirmed', 'gone'])

    def test_missing_gpu_sidecar_does_not_signal_unknown_pid_or_skip_other_sibling(self):
        self.backend.read.return_value = {'processes': [{'pid': 2}]}
        with patch.object(controller, 'descendants'), \
             patch.object(controller, 'stop_owned', return_value={'state': 'gone'}) as stop:
            rows = controller.cleanup_owned(self.owned, self.config, 'CPU-MOCK-run', None,
                1000, {}, self.backend, {2: {'gpu_uuid': 'CPU-MOCK-uuid'}})
        self.assertEqual([call.args[0]['pid'] for call in stop.call_args_list], [1])
        self.assertEqual([row['state'] for row in rows], ['cleanup_unknown_unconfirmed', 'gone'])


if __name__ == '__main__': unittest.main()
