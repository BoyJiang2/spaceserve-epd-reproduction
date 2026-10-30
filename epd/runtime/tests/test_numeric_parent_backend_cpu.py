"""Parent backend ordering fixtures, not actual actors/proc/NVML release."""
import itertools
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from numeric_parent_backend import NumericParentBackend


class ParentBackendTests(unittest.TestCase):
    def setUp(self):
        self.clock=[0.0];self.events=[];self.known=[]
        self.claim=SimpleNamespace(config={'gpu_uuids':['A','B','C'],'cleanup_seconds':120},
            inputs={'run_id':'unit'},deadline=1800,check=Mock())
        self.release=SimpleNamespace(scope={'run_id':'unit'},record=self.record,register=self.register,
            known_identities=lambda:list(self.known),mapping_possible=self.mapping,close=Mock(return_value={'release':'raw'}))
        self.rpc=SimpleNamespace(request=Mock(side_effect=self.request))
        self.backend=NumericParentBackend(self.claim,self.rpc,self.release,clock=lambda:self.clock[0])

    def record(self,event,**data):self.events.append((event,data))
    def register(self,identity):self.events.append(('register',identity));self.known.append(identity)
    def mapping(self,source,target):self.events.append(('mapping_fsynced',(source,target)))
    def request(self,action,arg,deadline,check):
        self.events.append(('rpc_'+action,arg))
        if action=='create_actor':return {'gpu_uuid':['A','B','C'][arg['slot']],'pid':len(self.known)+10}
        return {'actual':'reply'}
    def group(self):return self.backend.create_group(['A','B','C'],timeout=100)
    def copy_argument(self):
        return {'transfer':self.backend.vector[0],'source':{'identity':self.backend.identities['A']}}

    def test_creation_wal_and_registration_precede_next_create(self):
        rows=self.group();self.assertEqual(len(rows),3)
        self.assertEqual([name for name,data in self.events],['actor_creating','rpc_create_actor','register']*3)
        self.assertIsNone(self.backend.creating)

    def test_all_actual_uuid_orders_register_then_return_fixed_order(self):
        for order in itertools.permutations(['A','B','C']):
            with self.subTest(order=order):
                self.setUp();replies=iter(order);original_vector=list(self.backend.vector)
                def create(action,arg,deadline,check):
                    self.events.append(('rpc_'+action,arg))
                    return {'gpu_uuid':next(replies),'pid':len(self.known)+10}
                self.rpc.request.side_effect=create
                rows=self.group()
                self.assertEqual([row['gpu_uuid'] for row in self.known],list(order))
                self.assertEqual([row['gpu_uuid'] for row in rows],['A','B','C'])
                self.assertEqual(self.backend.vector,original_vector)
                self.assertEqual([name for name,data in self.events],['actor_creating','rpc_create_actor','register']*3)
                for index,call in enumerate(self.rpc.request.call_args_list):
                    intent=call.args[1]
                    self.assertEqual(intent['slot'],index)
                    self.assertEqual(intent['allowed_gpu_uuids'],['A','B','C'])
                    self.assertNotIn('gpu_uuid',intent)

    def test_foreign_or_duplicate_reply_keeps_pending_actor_without_replacement(self):
        for second in ('A','foreign'):
            with self.subTest(second=second):
                self.setUp();replies=iter(('A',second,'C'))
                self.rpc.request.side_effect=lambda *args:{'gpu_uuid':next(replies),'pid':len(self.known)+10}
                with self.assertRaises(ValueError):self.group()
                self.assertEqual(self.rpc.request.call_count,2)
                self.assertEqual([x['gpu_uuid'] for x in self.known],['A'])
                self.assertEqual(self.backend.creating['slot'],1)
                self.assertEqual(self.backend.creating['returned_identity']['gpu_uuid'],second)
                with self.assertRaisesRegex(RuntimeError,'UNCONFIRMED'):self.backend.assert_no_unresolved_creation()

    def test_registration_rejection_keeps_returned_identity_and_sibling(self):
        original=self.register
        def reject(identity):
            if identity['gpu_uuid']=='B':raise ValueError('profile/source rejected')
            original(identity)
        self.release.register=reject
        with self.assertRaises(ValueError):self.group()
        self.assertEqual(self.rpc.request.call_count,2)
        self.assertEqual([x['gpu_uuid'] for x in self.known],['A'])
        self.assertEqual(self.backend.creating['returned_identity']['gpu_uuid'],'B')

    def test_copy_mapping_precedes_driver_submission(self):
        self.group();self.events.clear()
        self.assertEqual(self.backend.call('B','copy',self.copy_argument(),timeout=100),{'actual':'reply'})
        self.assertEqual([name for name,data in self.events],['mapping_fsynced','rpc_call'])

    def test_mapping_wal_failure_sends_no_copy(self):
        self.group();self.rpc.request.reset_mock();self.release.mapping_possible=Mock(side_effect=OSError('fsync'))
        with self.assertRaises(OSError):self.backend.call('B','copy',self.copy_argument(),timeout=100)
        self.rpc.request.assert_not_called();self.assertTrue(self.backend.failed)

    def test_deadline_after_mapping_sends_no_copy(self):
        self.group();self.rpc.request.reset_mock()
        def mapping(*args):self.clock[0]=1681
        self.release.mapping_possible=mapping
        with self.assertRaises(TimeoutError):self.backend.call('B','copy',self.copy_argument(),timeout=100)
        self.rpc.request.assert_not_called()

    def test_close_uses_parent_registry_without_driver(self):
        rows=self.group();self.rpc.request.reset_mock();self.backend.failed=True
        self.assertEqual(self.backend.close('B',rows[1],timeout=10),{'release':'raw'})
        self.release.close.assert_called_once();self.rpc.request.assert_not_called()

    def test_partial_actor_return_keeps_unknown_intent_and_registered_sibling(self):
        original=self.request
        def fail(action,arg,deadline,check):
            if arg.get('slot')==1:raise EOFError('driver died creating')
            return original(action,arg,deadline,check)
        self.rpc.request.side_effect=fail
        with self.assertRaises(EOFError):self.group()
        self.assertEqual([row['gpu_uuid'] for row in self.backend.known_identities()],['A'])
        self.assertEqual(self.backend.creating['slot'],1)
        with self.assertRaisesRegex(RuntimeError,'UNCONFIRMED'):self.backend.assert_no_unresolved_creation()
        with self.assertRaises(RuntimeError):self.backend.call('A','sync',None,timeout=10)

    def test_original_vector_and_actual_importer_required(self):
        self.group();arg=self.copy_argument();arg['transfer']=dict(arg['transfer'],ordinal=True)
        self.rpc.request.reset_mock()
        with self.assertRaises(ValueError):self.backend.call('B','copy',arg,timeout=100)
        self.rpc.request.assert_not_called()

    def test_prior_live_group_blocks_next_creation(self):
        self.group();self.rpc.request.reset_mock()
        with self.assertRaises(ValueError):self.group()
        self.rpc.request.assert_not_called()

    def test_creating_record_failure_does_not_contact_driver(self):
        self.release.record=Mock(side_effect=OSError('journal full'))
        with self.assertRaises(OSError):self.group()
        self.rpc.request.assert_not_called()

    def test_cleanup_deadline_does_not_extend(self):
        self.clock[0]=1800
        with self.assertRaises(TimeoutError):self.backend.close('A',{},timeout=10)
        self.release.close.assert_not_called()


if __name__=='__main__':unittest.main()
