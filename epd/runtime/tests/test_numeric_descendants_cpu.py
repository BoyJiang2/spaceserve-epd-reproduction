"""CPU-MOCK only: ownership failures cannot become cleanup permission."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from numeric_descendants import HeadDescendants, HeadProc
from unittest.mock import patch


class DescendantsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.session = self.root/'session'
        self.rows = {pid:self.row(pid,parent) for pid,parent in ((10,1),(11,10),(12,11))}
        self.edges = {10:[dict(tid=10,raw='',children=[]),dict(tid=99,raw='11',children=[11])],
                      11:[dict(tid=11,raw='12',children=[12])],12:[]}
        self.events = []; self.calls = 0
        self.proc = SimpleNamespace(snapshot=self.snapshot,children=lambda pid,check:copy.deepcopy(self.edges[pid]),exists=lambda pid:pid in self.rows)
        self.collector = HeadDescendants(uid=2147,boot_id='boot',root=str(self.root),run_id='unit',
            session=str(self.session),supervisor_pid=1,proc=self.proc,record=self.record,check=lambda:None)
        self.process = SimpleNamespace(pid=10,poll=lambda:None,args=list(self.rows[10]['identity']['argv']))

    def row(self,pid,parent):
        return dict(identity=dict(pid=pid,ppid=parent,uid=2147,proc_start_ticks=pid*10,boot_id='boot',
            cwd=str(self.root),exe='/python',argv=['python','--session-dir='+str(self.session)],
            environment={'EXP_ROOT':str(self.root),'REPRO_RUN_ID':'unit'}),raw={'stat':'raw'})

    def snapshot(self,pid,uid):
        self.calls += 1
        return copy.deepcopy(self.rows[pid])

    def record(self,event,**data): self.events.append((event,data))

    def test_all_tid_children_and_grandchild(self):
        self.collector.register(self.process)
        self.assertEqual({r['pid'] for r in self.collector.collect()},{10,11,12})
        self.assertEqual([event for event,_ in self.events].count('head_descendant_registered'),2)

    def test_known_exited_leaf_does_not_erase_history_or_stop_other_observations(self):
        self.collector.register(self.process);self.collector.collect()
        previous=copy.deepcopy(self.collector.known)
        del self.rows[12];self.edges[11]=[]
        original=self.proc.snapshot
        def snapshot(pid,uid):
            if pid not in self.rows:raise FileNotFoundError('process exited')
            return original(pid,uid)
        self.proc.snapshot=snapshot
        self.assertEqual({r['pid'] for r in self.collector.collect()},{10,11,12})
        self.assertEqual(self.collector.known,previous)
        event=[data for name,data in self.events if name=='head_known_pid_absent'][-1]
        self.assertEqual(event['identity']['pid'],12)
        self.assertFalse(event['release_or_quiescence_granted'])

    def test_missing_snapshot_with_existing_pid_is_still_unknown(self):
        self.collector.register(self.process)
        self.proc.snapshot=lambda *args:(_ for _ in ()).throw(FileNotFoundError('field absent'))
        with self.assertRaises(FileNotFoundError):self.collector.collect()
        self.assertFalse(any(name=='head_known_pid_absent' for name,data in self.events))

    def test_foreign_scope_fields_rejected(self):
        for key,value in [('uid',7),('boot_id','other'),('cwd',str(self.root.parent)),
                          ('environment',{'EXP_ROOT':str(self.root),'REPRO_RUN_ID':'other'})]:
            with self.subTest(key=key):
                original=self.rows[10]['identity'][key];self.rows[10]['identity'][key]=value
                with self.assertRaises(ValueError):self.collector.register(self.process)
                self.assertEqual(self.collector.known,{})
                self.rows[10]['identity'][key]=original

    def test_session_substring_does_not_authorize(self):
        self.rows[10]['identity']['argv']=['python','--session-dir='+str(self.session)+'-foreign/log'];self.process.args=list(self.rows[10]['identity']['argv'])
        with self.assertRaisesRegex(ValueError,'session'):self.collector.register(self.process)

    def test_session_parent_traversal_rejected(self):
        self.rows[10]['identity']['argv']=['python','--session-dir='+str(self.session)+'/../foreign'];self.process.args=list(self.rows[10]['identity']['argv'])
        with self.assertRaisesRegex(ValueError,'session'):self.collector.register(self.process)

    def test_direct_popen_parent_and_exited_checks(self):
        self.rows[10]['identity']['ppid']=2
        with self.assertRaises(ValueError):self.collector.register(self.process)
        self.process.poll=lambda:0
        with self.assertRaisesRegex(ValueError,'exited'):self.collector.register(self.process)
        self.assertEqual(self.events,[])

    def test_journal_failure_prevents_registration(self):
        def fail(*args,**kwargs):raise OSError('fsync')
        self.collector.record=fail
        with self.assertRaises(OSError):self.collector.register(self.process)
        self.assertEqual(self.collector.known,{})

    def test_child_parent_mismatch_is_not_adopted(self):
        self.collector.register(self.process);self.rows[11]['identity']['ppid']=2
        with self.assertRaisesRegex(ValueError,'relation'):self.collector.collect()
        self.assertNotIn(11,self.collector.known)

    def test_parent_reuse_during_children_scan_refuses_child(self):
        self.collector.register(self.process)
        def children(pid,check):
            self.rows[pid]['identity']['proc_start_ticks']+=1
            return self.edges[pid]
        self.proc.children=children
        with self.assertRaisesRegex(ValueError,'reused'):self.collector.collect()
        self.assertNotIn(11,self.collector.known)

    def test_identity_change_between_reads_refuses_registration(self):
        def snapshot(pid,uid):
            row=self.snapshot(pid,uid)
            if self.calls>1:row['identity']['exe']='/changed'
            return row
        self.proc.snapshot=snapshot
        with self.assertRaisesRegex(ValueError,'changed'):self.collector.register(self.process)
        self.assertEqual(self.collector.known,{})

    def test_permission_error_is_not_empty_children(self):
        self.collector.register(self.process)
        def children(pid,check):raise PermissionError('children')
        self.proc.children=children
        with self.assertRaises(PermissionError):self.collector.collect()

    def test_retitled_worker_uses_real_parent_chain(self):
        self.collector.register(self.process)
        self.rows[11]['identity']['argv']=['ray::IDLE']
        self.collector.collect()
        self.rows[11]['identity']['argv']=['ray::actor']
        self.assertEqual({r['pid'] for r in self.collector.collect()},{10,11,12})

    def test_unknown_orphan_not_adopted_by_matching_environment(self):
        self.collector.register(self.process);self.rows[11]['identity']['ppid']=1
        self.rows[11]['identity']['argv']=['ray::IDLE']
        with self.assertRaises(ValueError):self.collector.collect()
        self.assertNotIn(11,self.collector.known)

    def test_popen_command_disagreement_refuses_registration(self):
        self.process.args=['python','--session-dir=/different']
        with self.assertRaisesRegex(ValueError,'argv differs'):self.collector.register(self.process)
        self.assertEqual(self.collector.known,{})

    def test_arbitrary_flag_cannot_claim_session(self):
        self.rows[10]['identity']['argv']=['python','--unrelated='+str(self.session)]
        self.process.args=list(self.rows[10]['identity']['argv'])
        with self.assertRaisesRegex(ValueError,'session'):self.collector.register(self.process)

    def test_already_known_orphan_blocks_new_closure(self):
        self.collector.register(self.process);self.collector.collect()
        self.rows[11]['identity']['ppid']=1
        with self.assertRaises(ValueError):self.collector.collect()

    def test_same_tick_parent_child_is_allowed(self):
        self.rows[11]['identity']['proc_start_ticks']=100
        self.collector.register(self.process);self.collector.collect()
        self.assertIn(11,self.collector.known)

    def test_duplicate_or_conflicting_selected_flags(self):
        for args in [ ['--session-dir='+str(self.session),'--session_dir='+str(self.session)],
                      ['--session-dir='+str(self.root/'foreign'),'--log-dir='+str(self.session/'logs')]]:
            with self.subTest(args=args):
                self.rows[10]['identity']['argv']=['python',*args];self.process.args=['python',*args]
                with self.assertRaisesRegex(ValueError,'conflicting'):self.collector.register(self.process)
                self.assertEqual(self.collector.known,{})

    def test_journal_retains_both_identity_observations(self):
        self.collector.register(self.process);self.collector.collect()
        for event,data in self.events:
            if event == 'head_children_observed':
                self.assertEqual(data['parent_before']['identity'],data['parent_after']['identity'])
                self.assertIn('raw',data['parent_after'])
            else:
                self.assertEqual(data['observation_before']['identity'],data['observation_after']['identity'])
                self.assertIn('raw',data['observation_after'])
                if 'parent_before' in data:self.assertIn('raw',data['parent_after'])

    def test_process_limit_prevents_new_child(self):
        self.collector.register(self.process)
        for pid in range(10000,14095):self.collector.known[pid]=self.row(pid,1)['identity']
        with self.assertRaisesRegex(ValueError,'bound'):self.collector.collect()
        self.assertNotIn(11,self.collector.known)

    def test_deadline_during_child_edge_prevents_adoption(self):
        self.collector.register(self.process)
        def checked_children(pid,check):
            self.collector.check=lambda:(_ for _ in ()).throw(TimeoutError('deadline'))
            return self.edges[pid]
        self.proc.children=checked_children
        with self.assertRaises(TimeoutError):self.collector.collect()
        self.assertNotIn(11,self.collector.known)

    def test_deadline_prevents_discovery(self):
        self.collector.register(self.process)
        def expired():raise TimeoutError('deadline')
        self.collector.check=expired
        with self.assertRaises(TimeoutError):self.collector.collect()
        self.assertEqual(set(self.collector.known),{10})


class ProcAdapterTests(unittest.TestCase):
    def test_real_file_parser_enumerates_all_tid_children(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);tasks=base/'proc/10/task'
            for tid,children in ((10,''),(22,'11 12')):
                p=tasks/str(tid);p.mkdir(parents=True);(p/'children').write_text(children)
            (tasks.parent/'stat').write_text('10 (parent) '+' '.join(['S','1']+['0']*17+['42']))
            def path(value):
                return base/str(value).lstrip('/')
            with patch('numeric_descendants.Path',side_effect=path):
                result=HeadProc().children(10,lambda:None)
            self.assertEqual([r['tid'] for r in result],[10,22])
            self.assertEqual(result[1]['children'],[11,12])

    def test_foreign_uid_adapter_stops_before_cmdline(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);p=base/'proc/10';p.mkdir(parents=True)
            (p/'status').write_text('Uid: 2147 9 2147 2147\n')
            with patch('numeric_descendants.Path',side_effect=lambda value:base/str(value).lstrip('/')):
                with self.assertRaisesRegex(ValueError,'Foreign'):HeadProc().snapshot(10,2147)




class ThreadInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(os.environ['EPD_CPU_TEST_TMP']).resolve(strict=True));self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.parent=self.root/'123';self.tasks=self.parent/'task'
        self.task=self.tasks/'777';self.task.mkdir(parents=True);(self.task/'children').write_text('456')
        self.stat=self.parent/'stat';self.set_start(42)
        self.path_patch=patch('numeric_descendants.Path',side_effect=lambda value:self.root if value=='/proc' else Path(value))
        self.path_patch.start();self.addCleanup(self.path_patch.stop)

    def set_start(self,start):
        self.stat.write_text('123 (parent) '+' '.join(['S','1']+['0']*17+[str(start)]))

    def observe(self,mode):
        original=Path.read_text;stat_reads=0
        def read(path,*args,**kwargs):
            nonlocal stat_reads
            if path==self.task/'children':
                if mode=='permission':raise PermissionError('fixture')
                if mode!='live_tid':
                    path.unlink();self.task.rmdir()
                if mode=='parent_reused':self.set_start(43)
                raise FileNotFoundError(2,'fixture thread exited',str(path))
            if path==self.stat:
                stat_reads+=1
                if mode=='tid_reappeared' and stat_reads==2:self.task.mkdir()
            return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',read):return HeadProc().children(123,lambda:None)

    def test_vanished_tid_with_same_live_parent_is_explicit_missing_observation(self):
        row=self.observe('gone')[0]
        self.assertEqual(row['children'],[]);self.assertIsNone(row['raw'])
        self.assertTrue(row['tid_absent_before_and_after']);self.assertEqual(row['parent_start_ticks'],42)
        self.assertFalse(row['release_or_quiescence_granted'])

    def test_missing_children_with_live_tid_is_refused(self):
        with self.assertRaises(FileNotFoundError):self.observe('live_tid')

    def test_parent_pid_reuse_during_missing_tid_is_refused(self):
        with self.assertRaisesRegex(ValueError,'parent identity changed'):self.observe('parent_reused')

    def test_tid_reappearing_after_parent_check_is_refused(self):
        with self.assertRaises(FileNotFoundError):self.observe('tid_reappeared')

    def test_permission_error_is_never_a_missing_tid(self):
        with self.assertRaises(PermissionError):self.observe('permission')

    def test_ordinary_tid_keeps_raw_child_inventory(self):
        self.assertEqual(HeadProc().children(123,lambda:None),[dict(tid=777,raw='456',children=[456])])


if __name__=='__main__':unittest.main()
