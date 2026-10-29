"""CPU-MOCK PID/NVML cleanup; no signals, Ray, Torch or CUDA calls."""
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numeric_release as release
from numeric_unit import identity_scope


class NumericReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='numeric-release-', dir=os.environ['EPD_CPU_TEST_TMP'])
        self.root = Path(self.temp.name).resolve(); self.now = 0.
        self.claim = SimpleNamespace(config=dict(root=str(self.root), uid=self.root.stat().st_uid,
            host='CPU-MOCK-host', gpu_uuids=['CPU-MOCK-A','CPU-MOCK-B','CPU-MOCK-C'], max_idle_bytes=10),
            inputs=dict(run_id='CPU-MOCK-unit', deploy_sha256='a'*64),
            deployed=dict(commit='b'*40, boot_id='CPU-MOCK-boot'), deadline=1800.,
            resources=dict(gpus={u:dict(capacity_bytes=1000) for u in ('CPU-MOCK-A','CPU-MOCK-B','CPU-MOCK-C')}))
        folder = self.root/'runtime/CPU-MOCK-unit'; folder.mkdir(parents=True)
        self.journal = folder/'numeric-lifecycle.jsonl'; self.rows = {}; self.calls = []; self.closed = []
        self.signal_impl = self.send
        self.proc = SimpleNamespace(identity=self.identity, environment=lambda pid:dict(EXP_ROOT=str(self.root), REPRO_RUN_ID='CPU-MOCK-unit'), boot=lambda:'CPU-MOCK-boot',
            exists=lambda pid:pid in self.rows, open_pidfd=lambda pid:(pid,self.rows[pid]['proc_start_ticks']),
            signal_pidfd=self.signal_pidfd, close_pidfd=self.closed.append)
        self.nvml = SimpleNamespace(read=self.read)
        self.guard = release.NumericRelease(self.claim, 'c'*64, self.nvml, self.proc, self.journal,
            clock=lambda:self.now, sleep=self.sleep)
        self.actors = [dict(identity_scope(self.claim, 'c'*64), gpu_uuid=uuid,
            pid=100+i, proc_start_ticks=1000+i, cwd=str(self.root), endpoint='gcs://127.0.0.1:45127')
            for i,uuid in enumerate(self.claim.config['gpu_uuids'])]
        for row in self.actors:
            self.rows[row['pid']] = dict(row); self.guard.register(row)

    def tearDown(self): self.temp.cleanup()

    def sleep(self, seconds): self.now += seconds

    def identity(self, pid, uid):
        if pid not in self.rows: raise FileNotFoundError('CPU-MOCK process absent')
        return {k:self.rows[pid][k] for k in ('pid','uid','proc_start_ticks','boot_id','cwd')}

    def read(self, uuid):
        pids = [r['pid'] for r in self.rows.values() if r['gpu_uuid']==uuid]
        return dict(capacity_bytes=1000, used_bytes=50 if pids else 0,
                    processes=[dict(pid=p, used_bytes=50) for p in pids])

    def send(self, pid, number):
        self.calls.append((pid,number)); self.rows.pop(pid, None)

    def signal_pidfd(self, descriptor, number):
        pid,ticks=descriptor
        if pid not in self.rows or self.rows[pid]['proc_start_ticks']!=ticks:
            raise ProcessLookupError('CPU-MOCK stable handle original process gone')
        self.signal_impl(pid,number)

    def test_importer_must_release_before_exporter(self):
        source,target = self.actors[:2]; self.guard.mapping_possible(source,target)
        with self.assertRaisesRegex(RuntimeError,'Importer'): self.guard.close(source['gpu_uuid'],source,timeout=3)
        self.assertEqual(self.calls,[])
        self.guard.close(target['gpu_uuid'],target,timeout=3)
        self.guard.close(source['gpu_uuid'],source,timeout=3)
        self.assertEqual([p for p,n in self.calls],[target['pid'],source['pid']])
        self.assertEqual(self.guard.known_identities(),[self.actors[2]])
        events=[json.loads(line) for line in self.journal.read_text().splitlines()]
        self.assertLess(next(i for i,r in enumerate(events) if r['event']=='mapping_possible'),
                        next(i for i,r in enumerate(events) if r['event']=='signal_intent'))

    def test_pid_reuse_or_root_runid_mismatch_never_signals(self):
        row=self.actors[0]; self.rows[row['pid']]['proc_start_ticks']+=1
        with self.assertRaises(ValueError): self.guard.close(row['gpu_uuid'],row,timeout=2)
        self.assertEqual(self.calls,[])
        other=self.actors[1]
        self.proc.environment=lambda pid:dict(EXP_ROOT=str(self.root), REPRO_RUN_ID='other')
        with self.assertRaises(ValueError): self.guard.close(other['gpu_uuid'],other,timeout=2)
        self.assertEqual(self.calls,[])

    def test_context_not_released_retains_exporter_and_never_retries_signal(self):
        source,target=self.actors[:2]; self.guard.mapping_possible(source,target)
        original=self.read
        self.nvml.read=lambda uuid: (dict(capacity_bytes=1000,used_bytes=50,processes=[dict(pid=target['pid'],used_bytes=50)])
                                      if uuid==target['gpu_uuid'] else original(uuid))
        with self.assertRaisesRegex(TimeoutError,'FAILED_RELEASE_UNCONFIRMED'):
            self.guard.close(target['gpu_uuid'],target,timeout=2)
        with self.assertRaisesRegex(RuntimeError,'Importer'): self.guard.close(source['gpu_uuid'],source,timeout=2)
        with self.assertRaises(ValueError): self.guard.close(target['gpu_uuid'],target,timeout=2)
        self.assertEqual(self.calls,[(target['pid'],signal.SIGTERM)])
        self.assertLessEqual(self.now,2.00001)

    def test_term_then_kill_is_bounded_and_checks_actual_exit(self):
        row=self.actors[0]
        def send(pid,number):
            self.calls.append((pid,number))
            if int(number)==9: self.rows.pop(pid)
        self.signal_impl=send
        with patch.object(signal,'SIGKILL',9,create=True):
            self.guard.close(row['gpu_uuid'],row,timeout=2)
        self.assertEqual([int(n) for pid,n in self.calls],[int(signal.SIGTERM),9])
        self.assertLess(self.now,2)

    def test_deadline_expired_never_signals_or_queries(self):
        self.now=self.claim.deadline
        with patch.object(self.nvml,'read') as query:
            with self.assertRaises(TimeoutError): self.guard.close(self.actors[0]['gpu_uuid'],self.actors[0],timeout=2)
            query.assert_not_called()
        self.assertEqual(self.calls,[])

    def test_failed_durable_intent_never_sends_signal(self):
        with patch.object(release.os,'fsync',side_effect=OSError('CPU-MOCK disk full')):
            with self.assertRaises(OSError): self.guard.close(self.actors[0]['gpu_uuid'],self.actors[0],timeout=2)
        self.assertEqual(self.calls,[])

    def test_pid_disappears_at_signal_race_requires_actual_observation(self):
        row=self.actors[0]
        def send(pid,number):
            self.rows.pop(pid); raise ProcessLookupError('CPU-MOCK exit race')
        self.signal_impl=send
        receipt=self.guard.close(row['gpu_uuid'],row,timeout=2)
        self.assertFalse(receipt['proc_observation']['exists'])
        self.assertEqual(receipt['raw_nvml']['processes'],[])

    def test_duplicate_registry_and_changed_mapping_refused(self):
        with self.assertRaises(ValueError): self.guard.register(self.actors[0])
        self.guard.mapping_possible(*self.actors[:2])
        with self.assertRaises(ValueError): self.guard.mapping_possible(self.actors[0],self.actors[2])
        with self.assertRaises(ValueError): self.guard.mapping_possible(self.actors[0],self.actors[0])

    def test_journal_cannot_be_outside_claim_or_reused(self):
        for path in (self.journal,self.root/'wrong.jsonl'):
            with self.assertRaises((ValueError,FileExistsError)):
                release.NumericRelease(self.claim,'c'*64,self.nvml,self.proc,path)

    def test_pid_reuse_during_durable_intent_cannot_signal_new_process(self):
        row=self.actors[0]; record=self.guard.record
        def race(event,**data):
            record(event,**data)
            if event=='signal_intent': self.rows[row['pid']]['proc_start_ticks']+=1
        self.guard.record=race
        with self.assertRaises(ValueError): self.guard.close(row['gpu_uuid'],row,timeout=2)
        self.assertEqual(self.calls,[])
        self.assertEqual(self.closed,[(row['pid'],row['proc_start_ticks'])])
        self.assertIn(row['pid'],self.rows)

    def test_cwd_or_environ_missing_is_not_process_exit(self):
        source,row=self.actors[:2]; self.guard.mapping_possible(source,row)
        for field in ('identity','environment'):
            with self.subTest(field=field):
                self.guard.attempted.clear()
                with patch.object(self.proc,field,side_effect=FileNotFoundError('CPU-MOCK missing subfile')), \
                     patch.object(self.nvml,'read',return_value=dict(capacity_bytes=1000,used_bytes=0,processes=[])):
                    with self.assertRaisesRegex(RuntimeError,'PID still exists'):
                        self.guard.close(row['gpu_uuid'],row,timeout=2)
                self.assertNotIn((row['pid'],row['proc_start_ticks']),self.guard.released)
                with self.assertRaisesRegex(RuntimeError,'Importer'):
                    self.guard.close(source['gpu_uuid'],source,timeout=2)
        self.assertEqual(self.calls,[])

    def test_fsync_crossing_deadline_never_sends_late_signal(self):
        row=self.actors[0]; record=self.guard.record
        def delayed(event,**data):
            record(event,**data)
            if event=='signal_intent': self.now+=3
        self.guard.record=delayed
        with self.assertRaises(TimeoutError): self.guard.close(row['gpu_uuid'],row,timeout=2)
        self.assertEqual(self.calls,[])
        self.assertEqual(self.closed,[(row['pid'],row['proc_start_ticks'])])

    def test_unavailable_pidfd_refuses_numeric_pid_fallback(self):
        row=self.actors[0]
        with patch.object(self.proc,'open_pidfd',side_effect=RuntimeError('CPU-MOCK pidfd unavailable')):
            with self.assertRaises(RuntimeError): self.guard.close(row['gpu_uuid'],row,timeout=2)
        self.assertEqual(self.calls,[])

    def test_original_process_exits_before_pidfd_open(self):
        row=self.actors[0]
        def open_pidfd(pid):
            self.rows.pop(pid); raise ProcessLookupError('CPU-MOCK exited before pidfd_open')
        self.proc.open_pidfd=open_pidfd
        receipt=self.guard.close(row['gpu_uuid'],row,timeout=2)
        self.assertFalse(receipt['proc_observation']['exists'])
        self.assertEqual(self.calls,[])
        self.assertEqual(self.closed,[])

    def test_real_proc_adapter_uses_only_pidfd_api_not_numeric_pid_signal(self):
        proc=release.NumericProc()
        with patch.object(release.os,'pidfd_open',return_value=42,create=True) as opened, \
             patch.object(release.signal,'pidfd_send_signal',create=True) as sent, \
             patch.object(release.os,'close') as closed, patch.object(release.os,'kill') as unsafe:
            descriptor=proc.open_pidfd(123)
            proc.signal_pidfd(descriptor,signal.SIGTERM); proc.close_pidfd(descriptor)
            opened.assert_called_once_with(123,0)
            sent.assert_called_once_with(42,signal.SIGTERM,None,0)
            closed.assert_called_once_with(42); unsafe.assert_not_called()


if __name__=='__main__': unittest.main()
