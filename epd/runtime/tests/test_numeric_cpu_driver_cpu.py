"""Driver fixtures; no Ray runtime, process lifecycle or GPU evidence."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numeric_cpu_driver as driver


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.events=[]
        self.spec=dict(root=str(self.root),folder=str(self.root),session=str(self.root),
            run_id='cpu-test',address='127.0.0.1:18765',namespace='test-ns',name='test-actor',detached=True,delay_seconds=0)
        self.expected=dict(actor_id='a'*32,job_id='b'*8,namespace='test-ns',name='test-actor',detached=True)
        self.ready=Mock(return_value=object());self.ref=SimpleNamespace(_actor_id=SimpleNamespace(hex=lambda:'a'*32),ready=SimpleNamespace(remote=self.ready))
        self.factory=Mock();self.factory.options.return_value.remote=Mock(return_value=self.ref)
        self.ray=SimpleNamespace(__file__=str(self.root/'__init__.py'),
            get_runtime_context=lambda:SimpleNamespace(get_job_id=lambda:'b'*8,namespace='test-ns'),
            remote=Mock(return_value=lambda actor:self.factory),get=Mock(side_effect=self.result))
        self.stack=__import__('contextlib').ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ,CUDA_VISIBLE_DEVICES='',EXP_ROOT=str(self.root),REPRO_RUN_ID='cpu-test'))
        self.stack.enter_context(patch.object(driver.os,'getuid',return_value=self.root.stat().st_uid,create=True))
        self.stack.enter_context(patch.object(driver.Path,'cwd',return_value=self.root))
        self.written=self.stack.enter_context(patch.object(driver,'durable'))

    def result(self,*args,**kwargs):
        self.assertEqual([r[0] for r in self.events],['before_actor_create','actor_submitted'])
        self.assertEqual(kwargs,{'timeout':20})
        return dict(self.expected,process={'pid':123})

    def record(self,event,**data):self.events.append((event,data))

    def test_submission_is_durable_before_wait_and_single_create(self):
        self.assertEqual(driver.scenario(self.ray,self.spec,self.record),self.expected)
        self.assertEqual([r[0] for r in self.events],['before_actor_create','actor_submitted','actor_ready'])
        self.ray.remote.assert_called_once_with(num_cpus=0,num_gpus=0,max_restarts=0,max_task_retries=0)
        self.factory.options.assert_called_once_with(name='test-actor',namespace='test-ns',lifetime='detached')
        self.factory.options.return_value.remote.assert_called_once()
        self.written.assert_called_once_with(self.root/'actor-submitted.json',self.expected)

    def test_non_detached_is_explicit(self):
        self.spec['detached']=False;self.expected['detached']=False
        driver.scenario(self.ray,self.spec,self.record)
        self.assertEqual(self.factory.options.call_args.kwargs['lifetime'],'non_detached')

    def test_preidentity_failure_retains_submitted_without_retry(self):
        self.ray.get.side_effect=TimeoutError('fixture timeout')
        with self.assertRaises(TimeoutError):driver.scenario(self.ray,self.spec,self.record)
        self.assertEqual([r[0] for r in self.events],['before_actor_create','actor_submitted'])
        self.factory.options.return_value.remote.assert_called_once()

    def test_parent_wal_failure_prevents_creation(self):
        with self.assertRaises(OSError):driver.scenario(self.ray,self.spec,Mock(side_effect=OSError('fsync')))
        self.ray.remote.assert_not_called()

    def test_ready_cannot_substitute_another_actor(self):
        self.expected['actor_id']='c'*32
        with self.assertRaisesRegex(ValueError,'response identity'):driver.scenario(self.ray,self.spec,self.record)
        self.assertNotIn('actor_ready',[r[0] for r in self.events])

    def test_bad_scope_prevents_creation(self):
        for key,value in [('address','1.2.3.4:18765'),('delay_seconds',False),('delay_seconds',True),('delay_seconds',16),('name','../actor'),('detached','yes')]:
            with self.subTest(key=key),patch.dict(self.spec,{key:value}),self.assertRaises(ValueError):
                driver.scenario(self.ray,self.spec,self.record)
        self.ray.remote.assert_not_called()

    def test_constructor_reports_real_context_before_delay_without_model(self):
        fake=SimpleNamespace(get_runtime_context=lambda:SimpleNamespace(get_actor_id=lambda:'a'*32,get_job_id=lambda:'b'*8,namespace='test-ns'),get_gpu_ids=lambda:[])
        proc=SimpleNamespace(snapshot=Mock(return_value={'identity':{'pid':123}}))
        ordered=[]
        with patch.dict(driver.sys.modules,ray=fake),patch.object(driver,'verify_sources') as checked, \
             patch.object(driver,'HeadProc',return_value=proc),patch.object(driver,'durable',side_effect=lambda *a:ordered.append('receipt')), \
             patch.object(driver.time,'sleep',side_effect=lambda *a:ordered.append('delay')):
            actor=driver.CPUActor(self.spec,self.root)
        self.assertEqual(ordered,['receipt','delay']);self.assertEqual(actor.ready()['actor_id'],'a'*32)
        self.assertEqual(checked.call_args.args[1]['runtime_context.py'],driver.CONTEXT_SHA)

    def test_constructor_gpu_allocation_refused_before_receipt(self):
        fake=SimpleNamespace(get_runtime_context=lambda:SimpleNamespace(get_actor_id=lambda:'a'*32,get_job_id=lambda:'b'*8,namespace='test-ns'),get_gpu_ids=lambda:[0])
        with patch.dict(driver.sys.modules,ray=fake),patch.object(driver,'verify_sources'), \
             patch.object(driver,'HeadProc',return_value=SimpleNamespace(snapshot=Mock(return_value={}))), \
             patch.object(driver,'durable') as written,self.assertRaises(ValueError):
            driver.CPUActor(self.spec,self.root)
        written.assert_not_called()


if __name__=='__main__':unittest.main()
