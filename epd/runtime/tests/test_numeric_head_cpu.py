"""Fake Popen/Node/signal masks only; never imports or starts actual Ray."""
from pathlib import Path
import hashlib
import signal
import sys
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numeric_head as head


class NumericHeadTests(unittest.TestCase):
    def setUp(self):
        self.parameters=head.node_parameters(str(Path('/CPU-MOCK-n36').absolute()),45127)
        self.mask=set(); self.children=[]; self.registered=[]; self.created=[]
        self.failing_registration=None; self.failing_constructor=False
        self.deliver_signal=False
        self.TERM,self.INT,self.ALRM,self.BLOCK,self.SET=15,2,14,0,2
        def original_handler(number,frame): raise RuntimeError('CPU-MOCK original raising handler')
        self.original_handler=original_handler
        self.handlers={n:original_handler for n in (self.TERM,self.INT,self.ALRM)}
        owner=self
        class FakePopen:
            def __init__(self,*args,**kwargs):
                self.pid=100+len(owner.created); owner.created.append(self)
                if owner.deliver_signal: owner.handlers[owner.TERM](owner.TERM,None)
                parent=set(owner.mask)
                kwargs['preexec_fn']()
                owner.children.append(set(owner.mask))
                owner.mask=parent
        self.Popen=FakePopen
        self.services=SimpleNamespace(ConsolePopen=FakePopen)
        class FakeNode:
            kill_all_processes=Mock()
            def __init__(self,params,**kwargs):
                owner.node_kwargs=kwargs; owner.param_kwargs=params
                self.address=params['node_ip_address']+':45127'; self.kernel_fate_share=False
                for index in range(3):
                    def official_preexec(): owner.mask.add(owner.INT)
                    owner.services.ConsolePopen(['CPU-MOCK-Ray-child',str(index)],preexec_fn=official_preexec)
                    if owner.failing_constructor: raise RuntimeError('CPU-MOCK Node partial startup')
        self.Node=FakeNode

    def sigmask(self,how,values):
        previous=set(self.mask)
        if how==self.BLOCK:self.mask.update(values)
        elif how==self.SET:self.mask=set(values)
        else:raise AssertionError(how)
        return previous

    def register(self,process):
        self.assertEqual(self.mask,set())
        self.registered.append(process)
        if self.failing_registration==len(self.registered): raise OSError('CPU-MOCK durable registry failure')

    def set_handler(self,number,handler):
        old=self.handlers[number];self.handlers[number]=handler;return old

    def run_construct(self,processes,check=None):
        with patch.object(head.sys,'platform','linux'),patch.object(head.subprocess,'Popen',self.Popen), \
             patch.object(signal,'SIGTERM',self.TERM),patch.object(signal,'SIGINT',self.INT), \
             patch.object(signal,'SIGALRM',self.ALRM,create=True), \
             patch.object(signal,'SIG_BLOCK',self.BLOCK,create=True),patch.object(signal,'SIG_SETMASK',self.SET,create=True), \
             patch.object(signal,'pthread_sigmask',side_effect=self.sigmask,create=True), \
             patch.object(signal,'signal',side_effect=self.set_handler), \
             patch.object(signal,'getsignal',side_effect=lambda number:self.handlers[number]), \
             patch.object(head,'load_runtime',return_value=(self.Node,lambda **kwargs:kwargs,self.services)):
            return head.construct_node(self.parameters,check or (lambda:None),self.register,processes)

    def test_node_disables_reaper_and_exit_hooks_and_preserves_child_signal_policy(self):
        processes=[]; node=self.run_construct(processes)
        self.assertEqual(self.node_kwargs,dict(head=True,shutdown_at_exit=False,spawn_reaper=False))
        self.assertEqual(self.param_kwargs,self.parameters)
        self.assertEqual(len(processes),3);self.assertEqual(processes,self.registered)
        self.assertEqual(self.children,[{self.INT}]*3)  # Official Ray SIGINT block; no inherited TERM/ALRM block.
        self.assertEqual(self.mask,set());self.assertIs(self.services.ConsolePopen,self.Popen)
        node.kill_all_processes.assert_not_called()

    def test_CPU_head_uses_nonrewritten_loopback(self):
        params=head.node_parameters(str(Path('/CPU-MOCK-n36').absolute()),45127,gpu_count=0)
        self.assertEqual(params['node_ip_address'],'127.0.0.2')
        self.assertEqual(params['raylet_ip_address'],'127.0.0.2')

    def test_three_GPU_head_keeps_original_parameters(self):
        self.assertEqual(self.parameters,dict(temp_dir=str(Path('/CPU-MOCK-n36').absolute()),
            gcs_server_port=45127,node_ip_address='127.0.0.1',raylet_ip_address='127.0.0.1',
            num_cpus=3,num_gpus=3,object_store_memory=128<<20,memory=512<<20,
            include_dashboard=False,no_monitor=True,include_log_monitor=False,_system_config={}))

    def test_CPU_construct_checks_actual_nonrewritten_address(self):
        self.parameters=head.node_parameters(str(Path('/CPU-MOCK-n36').absolute()),45127,gpu_count=0)
        node=self.run_construct([])
        self.assertEqual(node.address,'127.0.0.2:45127');self.assertEqual(self.param_kwargs,self.parameters)

    def test_partial_constructor_failure_preserves_real_popen_registry(self):
        self.failing_constructor=True;processes=[]
        with self.assertRaisesRegex(RuntimeError,'partial startup'):self.run_construct(processes)
        self.assertEqual(len(processes),1);self.assertEqual(processes,self.registered)
        self.assertIs(self.services.ConsolePopen,self.Popen);self.assertEqual(self.mask,set())
        self.Node.kill_all_processes.assert_not_called()

    def test_registration_failure_keeps_process_for_controlled_cleanup(self):
        self.failing_registration=2;processes=[]
        with self.assertRaises(OSError):self.run_construct(processes)
        self.assertEqual(len(processes),2);self.assertEqual(len(self.created),2)
        self.assertEqual(self.mask,set());self.assertIs(self.services.ConsolePopen,self.Popen)

    def test_refuses_already_blocked_term_mask_without_spawning(self):
        self.mask={self.TERM}
        with self.assertRaisesRegex(RuntimeError,'already masks'):self.run_construct([])
        self.assertEqual(self.created,[]);self.assertEqual(self.mask,{self.TERM})
        self.assertIs(self.services.ConsolePopen,self.Popen)

    def test_claim_check_failure_does_not_spawn_or_import_runtime(self):
        with patch.object(head,'load_runtime') as imported:
            with self.assertRaises(TimeoutError):
                head.construct_node(self.parameters,Mock(side_effect=TimeoutError('CPU-MOCK deadline')),self.register,[])
            imported.assert_not_called()
        self.assertEqual(self.created,[])

    def test_changed_parameters_rejected_before_runtime_import(self):
        for change in ({'num_gpus':1},{'num_cpus':9},{'node_ip_address':'remote'}, {'_system_config':{'x':1}}):
            with self.subTest(change=change),patch.object(head,'load_runtime') as imported:
                with self.assertRaises(ValueError):head.construct_node(self.parameters|change,lambda:None,self.register,[])
                imported.assert_not_called()

    def test_actual_address_or_fate_share_mismatch_rejected(self):
        original=self.Node
        class WrongNode(original):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs);self.address='remote:45127'
        self.Node=WrongNode
        with self.assertRaisesRegex(ValueError,'Actual Node'):self.run_construct([])
        self.assertEqual(len(self.created),3)

    def test_invalid_short_path_port_or_gpu_count(self):
        for port,count in ((True,3),(0,3),(70000,3),(45127,1),(45127,True)):
            with self.subTest(port=port,count=count),self.assertRaises(ValueError):
                head.node_parameters(self.parameters['temp_dir'],port,gpu_count=count)
        self.assertEqual(head.node_parameters(self.parameters['temp_dir'],45127,gpu_count=0)['num_gpus'],0)

    def test_runtime_loader_checks_exact_version_and_all_three_source_bytes(self):
        ray=ModuleType('ray'); ray.__version__='2.10.0'
        private=ModuleType('ray._private'); ray._private=private
        payloads={name+'.py':('CPU-MOCK '+name).encode() for name in head.SOURCE_SHA256}
        for name in head.SOURCE_SHA256:
            setattr(private,name,SimpleNamespace(__file__=name+'.py',Node=self.Node,RayParams=object))
        pins={name:hashlib.sha256(payloads[name+'.py']).hexdigest() for name in head.SOURCE_SHA256}
        with patch.dict(sys.modules,{'ray':ray,'ray._private':private}), \
             patch.dict(head.SOURCE_SHA256,pins,clear=True), \
             patch.object(Path,'read_bytes',lambda path:payloads[path.name]):
            actual=head.load_runtime();self.assertIs(actual[0],self.Node)
            for name in pins:
                with self.subTest(name=name):
                    original=payloads[name+'.py'];payloads[name+'.py']=b'CPU-MOCK changed'
                    with self.assertRaisesRegex(ValueError,'Installed Ray source'):head.load_runtime()
                    payloads[name+'.py']=original
            ray.__version__='2.11.0'
            with self.assertRaisesRegex(ValueError,'Exact reviewed'):head.load_runtime()

    def test_background_signal_during_popen_keeps_child_owned(self):
        self.deliver_signal=True;processes=[]
        with self.assertRaises(RuntimeError): self.run_construct(processes)
        self.assertEqual(len(self.created),1)
        self.assertEqual(processes,self.created)
        self.assertEqual(self.registered,self.created)
        self.assertIs(self.services.ConsolePopen,self.Popen)
        self.assertTrue(all(handler is self.original_handler for handler in self.handlers.values()))


if __name__=='__main__':unittest.main()
