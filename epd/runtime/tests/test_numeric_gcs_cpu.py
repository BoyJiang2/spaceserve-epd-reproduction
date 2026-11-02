"""Fake protobuf/RPC fixtures, not evidence of an actual Ray/GCS lifecycle."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from numeric_gcs import GCSActorReader


class GCSMetadataTests(unittest.TestCase):
    def setUp(self):
        self.now=1.;self.events=[]
        self.expected=dict(actor_id='a'*32,job_id='b'*8,namespace='private-r0',name='cpu-case-1',detached=True)
        self.row=SimpleNamespace(actor_id=bytes.fromhex(self.expected['actor_id']),job_id=bytes.fromhex(self.expected['job_id']),
            ray_namespace='private-r0',name='cpu-case-1',is_detached=True,state=2,pid=99,
            max_restarts=0,num_restarts=0,required_resources={'CPU':0})
        self.reply=SimpleNamespace(status=SimpleNamespace(code=0),actor_table_data=self.row,SerializeToString=lambda:b'fixture-protobuf')
        self.rpc=Mock(return_value=self.reply);self.request=Mock(side_effect=lambda **kw:kw)
        self.reader=GCSActorReader(self.rpc,self.request,self.record,lambda:None,clock=lambda:self.now)

    def record(self,event,**data):self.events.append((event,data))

    def test_only_bounded_GetActorInfo_and_raw_metadata(self):
        result=self.reader.read(self.expected,10.)
        self.request.assert_called_once_with(actor_id=bytes.fromhex(self.expected['actor_id']))
        self.assertEqual(self.rpc.call_args.kwargs,{'timeout':.25})
        self.assertEqual(result['state'],'ALIVE')
        self.assertEqual(result['scope'],'raw_GCS_metadata_not_release_or_quiescence')
        self.assertNotIn('passed',result);self.assertNotIn('released',result)
        self.assertEqual([x[0] for x in self.events],['gcs_actor_query_started','gcs_actor_query_finished'])

    def test_pending_zero_PID_is_never_quiescence(self):
        self.row.state=1;self.row.pid=0
        result=self.reader.read(self.expected,10.)
        self.assertEqual(result['state'],'PENDING_CREATION');self.assertEqual(result['pid'],0)
        self.assertNotIn('released',result)

    def test_error_or_empty_reply_cannot_be_released(self):
        self.reply.status.code=1
        with self.assertRaises(ValueError):self.reader.read(self.expected,10.)
        self.reply.status.code=0;self.row.actor_id=b''
        with self.assertRaises(ValueError):self.reader.read(self.expected,10.)
        self.assertEqual([e for e,d in self.events].count('gcs_actor_query_finished'),0)

    def test_foreign_actor_job_namespace_name_and_lifetime_rejected(self):
        for name,value in [('actor_id',b'c'*16),('job_id',b'c'*4),('ray_namespace','foreign'),('name','other'),('is_detached',False)]:
            with self.subTest(name=name):
                old=getattr(self.row,name);setattr(self.row,name,value)
                with self.assertRaises(ValueError):self.reader.read(self.expected,10.)
                setattr(self.row,name,old)

    def test_GPU_restarts_and_invalid_state_refused(self):
        for name,value in [('state',True),('state',9),('pid',-1),('max_restarts',1),('num_restarts',1),('required_resources',{'GPU':1})]:
            with self.subTest(name=name):
                old=getattr(self.row,name);setattr(self.row,name,value)
                with self.assertRaises(ValueError):self.reader.read(self.expected,10.)
                setattr(self.row,name,old)

    def test_explicit_one_gpu_mode_accepts_only_one_gpu_without_granting_release(self):
        reader=GCSActorReader(self.rpc,self.request,self.record,lambda:None,
            clock=lambda:self.now,expected_gpu_count=1)
        self.row.required_resources={'GPU':1.0}
        value=reader.read(self.expected,10.)
        self.assertEqual(value['state'],'ALIVE')
        self.assertNotIn('released',value)
        self.assertNotIn('passed',value)
        for gpu in (0,2,True,float('nan'),float('inf'),'1'):
            with self.subTest(gpu=gpu):
                self.row.required_resources={'GPU':gpu}
                with self.assertRaises(ValueError):reader.read(self.expected,10.)

    def test_actor_gpu_mode_cannot_be_boolean_fractional_or_larger(self):
        for mode in (True,1.0,-1,2,None):
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                GCSActorReader(self.rpc,self.request,self.record,lambda:None,expected_gpu_count=mode)
        self.rpc.assert_not_called()

    def test_resource_mode_selects_only_its_original_private_address(self):
        with patch('numeric_gcs.verify_sources',side_effect=OSError('CPU-MOCK stop before imports')) as pins, \
                patch('numeric_gcs.os.getuid',return_value=2147,create=True):
            for mode,address in ((0,'127.0.0.1:1234'),(1,'127.0.0.2:1234')):
                with self.subTest(mode=mode),self.assertRaises(ValueError):
                    GCSActorReader.connect(address,Path('/fixture'),Mock(),lambda:None,expected_gpu_count=mode)
            pins.assert_not_called()
            with self.assertRaises(OSError):
                GCSActorReader.connect('127.0.0.1:1234',Path('/fixture'),Mock(),lambda:None,expected_gpu_count=1)
            pins.assert_called_once()

    def test_WAL_failure_or_elapsed_budget_prevents_RPC(self):
        self.reader.record=Mock(side_effect=OSError('fsync'))
        with self.assertRaises(OSError):self.reader.read(self.expected,10.)
        self.rpc.assert_not_called()
        self.reader.record=lambda *args,**kw:setattr(self,'now',10.)
        with self.assertRaises(TimeoutError):self.reader.read(self.expected,10.)
        self.rpc.assert_not_called()

    def test_late_reply_does_not_get_finished_record(self):
        def late(*a,**kw):self.now=10.;return self.reply
        self.rpc.side_effect=late
        with self.assertRaises(TimeoutError):self.reader.read(self.expected,10.)
        self.assertEqual([e for e,d in self.events],['gcs_actor_query_started'])

    def test_malformed_intent_and_deadline_never_issue_RPC(self):
        for bad in (dict(self.expected,actor_id='bad'),dict(self.expected,job_id='bad'),dict(self.expected,namespace='http://elsewhere'),dict(self.expected,detached=1)):
            with self.assertRaises(ValueError):self.reader.read(bad,10.)
        for deadline in (True,float('nan'),float('inf'),1.):
            with self.assertRaises(TimeoutError):self.reader.read(self.expected,deadline)
        self.rpc.assert_not_called()

    def test_remaining_budget_limits_the_single_query(self):
        self.reader.read(self.expected,1.1)
        self.assertAlmostEqual(self.rpc.call_args.kwargs['timeout'],.1)

    def test_remote_endpoint_or_parent_driver_context_refused(self):
        for address in ('remote:1234','127.0.0.1:22','localhost:1234'):
            with self.assertRaises(ValueError):GCSActorReader.connect(address,Path('/fixture'),Mock(),lambda:None)
        package=Path('/fixture').absolute()
        ray=SimpleNamespace(__version__='2.10.0',__file__=str(package/'__init__.py'),is_initialized=lambda:True)
        with patch.dict(sys.modules,ray=ray),patch('numeric_gcs.verify_sources'), \
             patch('numeric_gcs.os.getuid',return_value=2147,create=True), \
             patch('numeric_gcs.importlib.import_module') as imported:
            with self.assertRaises(ValueError):GCSActorReader.connect('127.0.0.2:1234',package,Mock(),lambda:None)
            imported.assert_not_called()


if __name__=='__main__':unittest.main()
