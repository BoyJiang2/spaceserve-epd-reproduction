"""Mock worker boundary tests; no Ray/CUDA imports, resources, or GPU proofs."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numeric_driver as driver
from numeric_cache import transfer_vector


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.scope = dict(host='CPU-MOCK', uid=2147, root=str(Path.cwd()), run_id='CPU-MOCK-unit',
            boot_id='CPU-MOCK-boot', source_commit='a'*40, deploy_sha256='b'*64,
            candidate_config_sha256='c'*64, engine_stage='DECODING')
        self.events = []
        self.counter = 0
        self.factory = Mock(create=self.create, call=Mock(side_effect=self.call))
        self.driver = driver.NumericDriver(self.scope, ['A', 'B', 'C'], self.factory, self.record)
        self.clock = patch.object(driver.time, 'monotonic', return_value=0)
        self.clock.start(); self.addCleanup(self.clock.stop)
        self.check = Mock()

    def record(self, event, **data): self.events.append((event, data))

    def create(self, intent, deadline, check):
        self.counter += 1
        return self.counter, dict(actor_id=f'{self.counter:032x}', job_id='00000001',
            namespace=intent['namespace'], name=intent['name'], detached=True)

    def call(self, actor, action, argument, deadline, check):
        if action == 'identity':
            self.assertEqual(self.events[-1][0], 'numeric_driver_actor_submitted')
            return dict(self.scope, gpu_uuid=['C', 'A', 'B'][(actor-1) % 3], pid=actor+100,
                proc_start_ticks=actor+200, cwd=str(Path.cwd()/'runtime'), endpoint='gcs://127.0.0.1:12345')
        return {'CPU-MOCK-response': action}

    def intent(self, index):
        group, slot = divmod(index, 3)
        return dict(namespace=self.scope['run_id'], name=f'native-g{group}-n{slot}', group=group, slot=slot,
                    allowed_gpu_uuids=['A', 'B', 'C'], scope=self.scope)

    def send(self, action, argument): return self.driver.handle(action, argument, 100, self.check)

    def test_all36_route_by_actual_uuid_across12_fresh_groups(self):
        vector = transfer_vector(['A', 'B', 'C'])
        for group in range(12):
            for slot in range(3): self.send('create_actor', self.intent(group*3+slot))
            for transfer in vector[group*3:group*3+3]:
                source, target = transfer['source_uuid'], transfer['target_uuid']
                self.send('call', dict(gpu_uuid=source, operation='prepare', argument=transfer))
                self.send('call', dict(gpu_uuid=target, operation='copy', argument=dict(
                    transfer=transfer, source={'identity':self.driver.identities[source]})))
            self.send('call', dict(gpu_uuid=target, operation='sync', argument=None))
        self.assertEqual(self.driver.created, 36)
        self.assertEqual(len(self.driver.history), 36)
        self.assertIsNone(self.driver.pending)
        with self.assertRaises(ValueError): self.send('create_actor', self.intent(36))

    def test_identity_timeout_keeps_original_submission_and_refuses_retry(self):
        self.factory.call.side_effect = TimeoutError('constructor unresolved')
        with self.assertRaises(TimeoutError): self.send('create_actor', self.intent(0))
        self.assertEqual(self.driver.pending['submitted']['actor_id'], f'{1:032x}')
        self.assertEqual(self.driver.created, 0)
        with self.assertRaises(RuntimeError): self.send('create_actor', self.intent(0))
        self.assertEqual(self.counter, 1)

    def test_wal_failure_before_create_does_not_contact_factory(self):
        self.driver.record = Mock(side_effect=OSError('journal unavailable'))
        with self.assertRaises(OSError): self.send('create_actor', self.intent(0))
        self.assertEqual(self.counter, 0)
        self.assertIsNotNone(self.driver.pending)

    def test_wrong_intent_or_expired_deadline_starts_no_actor(self):
        intent=self.intent(0);intent['namespace']='foreign'
        with self.assertRaises(ValueError): self.send('create_actor', intent)
        self.assertEqual(self.counter, 0)
        with self.assertRaises(TimeoutError): driver.remaining(-1, self.check)

    def test_stale_group_transfer_is_not_sent_to_new_lifetime(self):
        for index in range(6): self.send('create_actor', self.intent(index))
        self.factory.call.reset_mock()
        with self.assertRaises(ValueError):
            self.send('call', dict(gpu_uuid='A', operation='prepare', argument=transfer_vector(['A','B','C'])[0]))
        self.factory.call.assert_not_called()

    def test_authorization_refusal_precedes_hardware_library_import(self):
        authorize=Mock(side_effect=ValueError('no original GPU permission'))
        with patch('builtins.__import__') as imports:
            try: driver.load_factory(None, None, None, authorize)
            except ValueError: pass
            else: self.fail('Missing authorization accepted')
            imports.assert_not_called()

    def test_boolean_creation_index_is_rejected_before_actor_start(self):
        intent=self.intent(0);intent['slot']=False
        with self.assertRaises(ValueError): self.send('create_actor', intent)
        self.assertEqual(self.counter, 0)

    def test_production_factory_uses_official_remote_probe_without_model_init(self):
        ray, worker, actor = Mock(), Mock(), Mock()
        actor._actor_id.hex.return_value='a'*32
        worker.options.return_value.remote.return_value=actor
        ray.get_runtime_context.return_value.get_job_id.return_value='00000001'
        actor.reproduction_numeric_cache.remote.return_value='CPU-MOCK-object-ref'
        ray.get.return_value={'CPU-MOCK-actual-identity':True}
        verify_head=Mock()
        factory=driver.RayNumericFactory(ray,worker,'CPU-MOCK-DECODING','model','cache','parallel',verify_head)
        handle,submitted=factory.create(self.intent(0),100,self.check)
        self.assertIs(handle,actor)
        self.assertEqual(submitted['actor_id'],'a'*32)
        worker.options.assert_called_once_with(name='native-g0-n0',namespace='CPU-MOCK-unit',lifetime='detached',
            max_restarts=0,max_task_retries=0)
        worker.options.return_value.remote.assert_called_once_with(worker_id=0,stage='CPU-MOCK-DECODING',
            model_config='model',cache_config='cache',parallel_config='parallel')
        self.assertEqual(factory.call(actor,'identity',None,100,self.check),{'CPU-MOCK-actual-identity':True})
        actor.reproduction_numeric_cache.remote.assert_called_once_with('identity',None)
        ray.get.assert_called_once_with('CPU-MOCK-object-ref',timeout=100)
        actor.init_model.remote.assert_not_called()
        self.assertEqual(verify_head.call_count,2)

    def test_wrong_model_configuration_does_not_import_hardware(self):
        from types import SimpleNamespace
        with patch('builtins.__import__') as imports:
            try: driver.load_factory(SimpleNamespace(model='/CPU-MOCK/unsupported'), None, None, lambda:None)
            except ValueError: pass
            else: self.fail('Unsupported model accepted')
            imports.assert_not_called()

    def private_head_fixture(self, *, bad_session=False, pin_error=None):
        from types import SimpleNamespace
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base=Path(temporary.name).resolve();session=base/'session_CPU-MOCK';session.mkdir()
        package=base/'ray';package.mkdir()
        parameters=dict(temp_dir=str(base),gcs_server_port=12345)
        ray=Mock();ray.__version__='2.10.0';ray.__file__=str(package/'__init__.py')
        ray.get_runtime_context.return_value.namespace='CPU-MOCK-unit'
        node=Mock();node.is_head.return_value=False;node.all_processes={};node.address='127.0.0.1:12345'
        node.get_session_dir_path.return_value=str(base/'foreign' if bad_session else session)
        events=[];ray.init.side_effect=lambda **kwargs:events.append('connect')
        utils=Mock();utils.check_dashboard_dependencies_installed.return_value=False
        modules={'ray':ray,'ray._private.utils':utils,'ray._private.worker':SimpleNamespace(_global_node=node)}
        distribution=SimpleNamespace(version='2.10.0',locate_file=lambda name:package)
        def verify(*args):
            events.append('pins')
            if pin_error:raise pin_error
            return [{'path':'CPU-MOCK-source'}]
        patches=[patch('numeric_head.node_parameters',return_value=parameters),
            patch('numeric_cpu_ray.verify_sources',side_effect=verify),
            patch.object(driver.os,'getuid',return_value=base.stat().st_uid,create=True),
            patch.object(driver.importlib.metadata,'distribution',return_value=distribution),
            patch.object(driver.importlib,'import_module',side_effect=lambda name:modules[name])]
        return parameters,session,package,ray,node,events,patches

    def test_private_head_sources_precede_connect_and_wrong_session_refuses(self):
        from contextlib import ExitStack
        for bad in (False,True):
            parameters,session,package,ray,node,events,patches=self.private_head_fixture(bad_session=bad)
            with self.subTest(bad_session=bad),ExitStack() as stack:
                for item in patches:stack.enter_context(item)
                record=Mock()
                if bad:
                    with self.assertRaises(ValueError):
                        driver.connect_private_head(parameters,session,'CPU-MOCK-unit',package,self.check,record)
                    record.assert_not_called()
                else:
                    connected,verify=driver.connect_private_head(parameters,session,'CPU-MOCK-unit',package,self.check,record)
                    self.assertIs(connected,ray)
                    node.all_processes={'CPU-MOCK-unexpected-owned-child':object()}
                    with self.assertRaises(ValueError):verify()
                self.assertEqual(events,['pins','connect'])

    def test_changed_ray_source_refuses_before_import_and_connection(self):
        from contextlib import ExitStack
        parameters,session,package,ray,node,events,patches=self.private_head_fixture(pin_error=ValueError('source changed'))
        with ExitStack() as stack:
            for item in patches:stack.enter_context(item)
            with self.assertRaises(ValueError):
                driver.connect_private_head(parameters,session,'CPU-MOCK-unit',package,self.check,Mock())
            ray.init.assert_not_called()
            self.assertEqual(events,['pins'])


if __name__ == '__main__': unittest.main()
