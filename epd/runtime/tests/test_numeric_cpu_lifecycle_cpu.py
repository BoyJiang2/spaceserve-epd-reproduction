"""CPU fixtures for stable cleanup/pending refusal; no actual Ray or signals."""
import json
import os
from pathlib import Path
import signal
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, MagicMock, patch

import numeric_cpu_lifecycle as lifecycle
import numeric_cpu_receipts


class Proc:
    def __init__(self):
        self.row=dict(pid=123,uid=2147,proc_start_ticks=12,boot_id='boot',cwd='/owned',environment={'EXP_ROOT':'/owned','REPRO_RUN_ID':'cpu'})
        self.alive=True;self.signals=[];self.closed=[];self.after_open=lambda:None
    def snapshot(self,pid,uid):
        if not self.alive:raise FileNotFoundError(pid)
        return dict(identity=dict(self.row))
    def exists(self,pid):return self.alive
    def open_pidfd(self,pid):self.after_open();return 9
    def signal_pidfd(self,fd,number):self.signals.append((fd,number));self.alive=False
    def close_pidfd(self,fd):self.closed.append(fd)


class CleanupTests(unittest.TestCase):
    def setUp(self):self.proc=Proc();self.identity=dict(self.proc.row);self.events=[]
    def record(self,event,**data):self.events.append(event)
    def test_term_uses_stable_handle_then_closes(self):
        outcome=lifecycle.terminate(self.identity,self.proc,self.record,lambda:None)
        self.assertEqual(self.proc.signals,[(9,signal.SIGTERM)]);self.assertEqual(self.proc.closed,[9])
        self.assertEqual(self.events,['CPU_TERM_intent','CPU_TERM_sent']);self.assertTrue(outcome['controlled_signal_sent'])
    def test_absence_never_opens_or_signals(self):
        self.proc.alive=False
        outcome=lifecycle.terminate(self.identity,self.proc,self.record,lambda:None)
        self.assertEqual(self.proc.signals,[]);self.assertEqual(self.proc.closed,[])
        self.assertFalse(outcome['controlled_signal_sent']);self.assertTrue(outcome['already_absent'])
    def test_pid_reuse_after_open_refuses_signal_and_closes(self):
        self.proc.after_open=lambda:self.proc.row.update(proc_start_ticks=13)
        with self.assertRaisesRegex(ValueError,'identity changed'):
            lifecycle.terminate(self.identity,self.proc,self.record,lambda:None)
        self.assertEqual(self.proc.signals,[]);self.assertEqual(self.proc.closed,[9])
    def test_fsync_failure_refuses_signal(self):
        with self.assertRaises(OSError):lifecycle.terminate(self.identity,self.proc,Mock(side_effect=OSError('fsync')),lambda:None)
        self.assertEqual(self.proc.signals,[]);self.assertEqual(self.proc.closed,[9])
    def test_missing_cwd_with_existing_PID_is_not_absence(self):
        self.proc.snapshot=Mock(side_effect=FileNotFoundError('cwd'))
        with self.assertRaises(FileNotFoundError):lifecycle.terminate(self.identity,self.proc,self.record,lambda:None)
        self.assertEqual(self.proc.signals,[])
    def test_reap_direct_child_before_absence_observation(self):
        self.proc.signal_pidfd=lambda fd,n:self.proc.signals.append((fd,n))
        def reap():
            if self.proc.signals:self.proc.alive=False
        lifecycle.terminate(self.identity,self.proc,self.record,lambda:None,reap=reap)
        self.assertEqual(self.proc.signals,[(9,signal.SIGTERM)]);self.assertFalse(self.proc.alive)


class ParentFixture:
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.folder=self.root/'unit';self.folder.mkdir();self.session=self.root/'session';self.session.mkdir()
        self.uid=self.root.stat().st_uid
        self.patches=__import__('contextlib').ExitStack();self.addCleanup(self.patches.close)
        self.patches.enter_context(patch.object(lifecycle.os,'getuid',return_value=self.uid,create=True))
        self.patches.enter_context(patch.object(lifecycle.os,'O_NOFOLLOW',0,create=True))
        self.patches.enter_context(patch.object(lifecycle.HeadProc,'boot',return_value='fixture-boot'))
        self.patches.enter_context(patch.object(lifecycle.signal,'SIGALRM',14,create=True))
        self.patches.enter_context(patch.object(lifecycle.signal,'getsignal',return_value=None))
        self.patches.enter_context(patch.object(lifecycle.signal,'signal'))
        self.patches.enter_context(patch.object(numeric_cpu_receipts,'sync_directory'))
        self.d=lifecycle.Diagnostic(self.root,'cpu',self.folder,self.root,18765,self.root/'ray')
        self.d.leftovers=Mock(return_value=[])
        self.reader=SimpleNamespace(read=Mock(return_value=dict(state='DEAD')),close=Mock())
        self.patches.enter_context(patch.object(lifecycle,'load_cpu_ray',return_value=(None,{})))
        self.patches.enter_context(patch.object(lifecycle,'construct_node',side_effect=self.construct))
        self.patches.enter_context(patch.object(lifecycle.GCSActorReader,'connect',return_value=self.reader))
        self.term=self.patches.enter_context(patch.object(lifecycle,'terminate'))
    def construct(self,*args):
        self.d.collector=SimpleNamespace(session=self.session,known={},collect=Mock())
        return SimpleNamespace(get_session_dir_path=lambda:str(self.session),address='127.0.0.2:18765')
    def terminal(self):return json.loads((self.folder/'terminal.json').read_bytes())


class ParentTests(ParentFixture,unittest.TestCase):
    def test_pending_even_without_returnedActorID_retains_head(self):
        def fail(*args):self.d.pending_scenarios.add(0);raise RuntimeError('driver died before ActorID')
        self.d.scenario=fail
        with self.assertRaisesRegex(RuntimeError,'creation/scenario pending'):self.d.run()
        self.term.assert_not_called();self.assertEqual(self.terminal()['exit_code'],1)
        self.reader.read.assert_not_called()
    def test_GCS_DEAD_with_existingPID_never_grants_head_cleanup(self):
        def fail(*args):
            self.d.expected.append(dict(expected={'actor_id':'a'*32},identity=dict(pid=os.getpid())))
            raise RuntimeError('fixture')
        self.d.scenario=fail
        with patch.object(self.d.proc,'exists',return_value=True),self.assertRaisesRegex(RuntimeError,'actor; retain head'):self.d.run()
        self.term.assert_not_called();self.assertEqual(self.terminal()['exit_code'],1)
    def test_missing_identity_prevents_head_cleanup(self):
        def fail(*args):self.d.expected.append(dict(expected={},identity=None));raise RuntimeError('fixture')
        self.d.scenario=fail
        with self.assertRaisesRegex(RuntimeError,'pending CPU actor'):self.d.run()
        self.term.assert_not_called()
    def test_four_distinct_scenarios_no_business_retry(self):
        self.d.scenario=Mock()
        self.d.run()
        self.assertEqual([c.args for c in self.d.scenario.call_args_list],[(False,False,0),(True,False,1),(False,True,2),(True,True,3)])
        self.assertEqual(self.terminal()['exit_code'],0)
        self.assertIn('no GPU/backend approval',self.terminal()['scope'])

    def test_late_unregistered_scope_process_prevents_success(self):
        self.d.scenario=Mock();self.d.leftovers.return_value=[{'identity':{'pid':999}}]
        with self.assertRaisesRegex(RuntimeError,'late CPU scope process'):self.d.run()
        self.term.assert_not_called();self.assertEqual(self.terminal()['exit_code'],1)


class ScopeTests(ParentFixture,unittest.TestCase):
    def prepare_scope(self,error,proof,exists):
        directory=MagicMock();directory.name='999999';directory.stat.return_value=SimpleNamespace(st_uid=self.uid)
        child=SimpleNamespace(resolve=Mock(side_effect=error));directory.__truediv__.return_value=child
        proc=SimpleNamespace(iterdir=lambda:iter([directory]));real_path=Path
        self.patches.enter_context(patch.object(lifecycle,'Path',side_effect=lambda value:proc if str(value)=='/proc' else real_path(value)))
        self.service=self.patches.enter_context(patch.object(lifecycle,'control_service_exception',return_value=proof))
        self.d.proc.exists=Mock(return_value=exists)

    def test_only_verified_service_proof_allows_cwd_exception(self):
        self.prepare_scope(PermissionError('fixture'),{'verified':'exact chain'},True)
        self.assertEqual(lifecycle.Diagnostic.leftovers(self.d),[]);self.service.assert_called_once()
        self.assertIn('CPU_verified_control_service_exception',(self.folder/'lifecycle.jsonl').read_text())

    def test_unknown_permission_denied_is_never_skipped_by_name(self):
        self.prepare_scope(PermissionError('fixture'),None,True)
        with self.assertRaisesRegex(RuntimeError,'cwd unconfirmed'):lifecycle.Diagnostic.leftovers(self.d)

    def test_missing_cwd_while_PID_exists_is_not_empty_scope(self):
        self.prepare_scope(FileNotFoundError('fixture cwd'),None,True)
        with self.assertRaisesRegex(RuntimeError,'still exists'):lifecycle.Diagnostic.leftovers(self.d)
        self.service.assert_not_called()

    def test_actual_PID_absence_allows_racing_disappearance(self):
        self.prepare_scope(FileNotFoundError('fixture PID'),None,False)
        self.assertEqual(lifecycle.Diagnostic.leftovers(self.d),[]);self.service.assert_not_called()


class ScenarioTests(ParentFixture,unittest.TestCase):
    """Exercise the actual scenario loop with fake Ray/Popen metadata only."""
    def prepare(self,detached,controlled):
        self.d.collector=SimpleNamespace(session=self.session,known={},collect=Mock(),
            observe=Mock(),stable=Mock(),same_identity=lifecycle.HeadDescendants.same_identity)
        self.d.register=Mock();self.d.reader=self.reader
        self.identity=dict(pid=123,uid=self.uid,proc_start_ticks=12,boot_id='fixture-boot',
            cwd=str(self.root),environment={'EXP_ROOT':str(self.root),'REPRO_RUN_ID':'cpu'})
        self.driver_identity=dict(self.identity,pid=456)
        self.d.collector.known={123:self.identity,456:self.driver_identity}
        self.d.collector.observe.return_value={'identity':self.identity}
        self.d.collector.stable.return_value={'identity':self.identity}
        self.d.proc.exists=Mock(return_value=False)
        self.constructor_start=lifecycle.time.monotonic()
        def popen(args,**kwargs):
            folder=Path(next(a.split('=',1)[1] for a in args if a.startswith('--spec='))).parent
            expected=dict(actor_id='a'*32,job_id='b'*8,namespace='cpu',name='CPU-0',detached=detached)
            (folder/'driver-events.jsonl').write_text(json.dumps(dict(event='actor_submitted',expected=expected))+'\n',encoding='utf8')
            lifecycle.write(folder/'actor-submitted.json',expected)
            lifecycle.write(folder/'constructor-entered.json',dict(expected,process={'identity':self.identity},
                constructor_monotonic_s=self.constructor_start,delay_seconds=15 if controlled else 0))
            if not controlled:lifecycle.write(folder/'driver-ready.json',expected)
            self.driver=SimpleNamespace(pid=456,returncode=None if controlled else 0,args=args)
            self.driver.poll=Mock(side_effect=lambda:self.driver.returncode)
            return self.driver
        def term(identity,*args,**kwargs):
            if identity['pid']==456:self.driver.returncode=-15
            return dict(controlled_signal_sent=True,already_absent=False)
        self.term.side_effect=term
        self.patches.enter_context(patch.object(lifecycle.subprocess,'Popen',side_effect=popen))

    def test_detached_unexpected_death_cannot_pass(self):
        self.prepare(True,True);self.reader.read.side_effect=[dict(state='ALIVE',pid=123),dict(state='DEAD',pid=123),dict(state='DEAD',pid=123)]
        with self.assertRaisesRegex(RuntimeError,'without observed survival'):self.d.scenario(True,True,0)
        self.assertEqual(self.d.pending_scenarios,{0})
        self.assertEqual(self.term.call_count,1)  # driver only, no actor release

    def test_controlled_exit_past_safe_constructor_window_refused(self):
        self.prepare(True,True);self.constructor_start-=14
        self.reader.read.return_value=dict(state='PENDING_CREATION',pid=123)
        with self.assertRaisesRegex(TimeoutError,'window expired'):self.d.scenario(True,True,0)
        self.term.assert_not_called();self.assertEqual(self.d.pending_scenarios,{0})

    def test_stale_knownPID_GCS_alive_cannot_ack_live_actor(self):
        self.prepare(False,False);self.reader.read.return_value=dict(state='ALIVE',pid=123)
        self.d.collector.observe.side_effect=FileNotFoundError('fixture stale live PID')
        with self.assertRaises(FileNotFoundError):self.d.scenario(False,False,0)
        self.assertFalse((self.folder/'0/parent-observed.json').exists());self.term.assert_not_called()

    def test_wrong_GCS_PID_cannot_ack(self):
        self.prepare(False,False);self.reader.read.return_value=dict(state='ALIVE',pid=999)
        with self.assertRaisesRegex(ValueError,'exact live actor'):self.d.scenario(False,False,0)
        self.assertFalse((self.folder/'0/parent-observed.json').exists());self.term.assert_not_called()

    def test_detached_actual_survival_and_parent_release_required(self):
        self.prepare(True,True)
        self.reader.read.side_effect=[dict(state='ALIVE',pid=123),dict(state='ALIVE',pid=123),dict(state='DEAD',pid=123)]
        self.d.scenario(True,True,0)
        self.assertEqual([c.args[0]['pid'] for c in self.term.call_args_list],[456,123])
        self.assertEqual(self.d.pending_scenarios,set())
        log=(self.folder/'lifecycle.jsonl').read_text()
        self.assertIn('CPU_detached_survived_driver',log);self.assertIn('CPU_scenario_terminal_observed',log)

    def test_detached_GCS_alive_but_current_PID_gone_refuses(self):
        self.prepare(True,True);self.reader.read.return_value=dict(state='ALIVE',pid=123)
        self.d.collector.observe.side_effect=FileNotFoundError('gone after driver exit')
        with self.assertRaises(FileNotFoundError):self.d.scenario(True,True,0)
        self.assertEqual(self.term.call_count,1);self.assertEqual(self.d.pending_scenarios,{0})

    def test_detached_absent_outcome_cannot_count_as_parent_release(self):
        self.prepare(True,True);self.reader.read.return_value=dict(state='ALIVE',pid=123)
        original=self.term.side_effect
        self.term.side_effect=lambda identity,*a,**k: original(identity,*a,**k) if identity['pid']==456 else dict(controlled_signal_sent=False,already_absent=True)
        with self.assertRaisesRegex(RuntimeError,'parent release not performed'):self.d.scenario(True,True,0)
        self.assertEqual(self.d.pending_scenarios,{0})

    def test_driver_absent_outcome_cannot_count_as_controlled_exit(self):
        self.prepare(False,True);self.reader.read.return_value=dict(state='ALIVE',pid=123)
        self.term.side_effect=lambda *a,**k:dict(controlled_signal_sent=False,already_absent=True)
        with self.assertRaisesRegex(RuntimeError,'no controlled exit'):self.d.scenario(False,True,0)
        self.assertEqual(self.d.pending_scenarios,{0})

    def test_driver_natural_exit_before_control_refused(self):
        self.prepare(False,True);self.reader.read.return_value=dict(state='ALIVE',pid=123)
        def reap():
            if hasattr(self,'driver'):self.driver.returncode=0
        self.d.reap=reap
        with self.assertRaisesRegex(ValueError,'live driver/creation window'):self.d.scenario(False,True,0)
        self.term.assert_not_called();self.assertEqual(self.d.pending_scenarios,{0})

    def test_GCS_dead_before_control_cannot_be_controlled_exit(self):
        self.prepare(False,True);self.reader.read.return_value=dict(state='DEAD',pid=123)
        with self.assertRaisesRegex(ValueError,'live driver/creation window'):self.d.scenario(False,True,0)
        self.term.assert_not_called()


if __name__=='__main__':unittest.main()
