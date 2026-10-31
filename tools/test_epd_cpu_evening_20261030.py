"""CPU permission fixtures only; no network, processes, Ray or GPU."""
import copy
import os
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
import epd_cpu_evening_20261030 as policy


class EveningTests(unittest.TestCase):
    def test_cpu_lock_refuses_unsafe_file_or_busy_controller(self):
        parent=MagicMock();parent.is_symlink.return_value=False
        parent.is_dir.return_value=True;parent.stat.return_value.st_uid=2147
        lock=SimpleNamespace(LOCK_EX=2,LOCK_NB=4,flock=MagicMock())
        info=SimpleNamespace(st_uid=2147,st_nlink=1,st_mode=stat.S_IFREG|0o600)
        with patch.dict(sys.modules,{'fcntl':lock}),patch('pathlib.Path',return_value=parent), \
                patch.object(os,'getuid',return_value=2147,create=True), \
                patch.object(os,'O_NOFOLLOW',0x10000,create=True), \
                patch.object(os,'O_CLOEXEC',0x20000,create=True), \
                patch.object(os,'open',return_value=42),patch.object(os,'fstat',return_value=info), \
                patch.object(os,'close') as close:
            self.assertEqual(policy.acquire_cpu50(),42)
            lock.flock.assert_called_once_with(42,6);close.assert_not_called()
            lock.flock.side_effect=BlockingIOError('busy')
            with self.assertRaises(BlockingIOError):policy.acquire_cpu50()
            close.assert_called_once_with(42)
            lock.flock.reset_mock();info.st_mode=stat.S_IFREG|0o666
            with self.assertRaises(ValueError):policy.acquire_cpu50()
            lock.flock.assert_not_called()

    def setUp(self):
        self.now=policy.START_MS
        self.proof=dict(origin='gputime_read_only_api',read_only=True,observed_ms=self.now,
            resources=[dict(id='h20/qjh003',node='qjh003',active=True)],bookings=[])

    def ticket(self,lane='cpu',start=None,end=None,user='other'):
        return dict(resource_id='h20/qjh003',kind=lane,user=user,
            start_ms=self.now if start is None else start,
            end_ms=self.now+330000 if end is None else end)

    def test_direct_permission_does_not_invent_owned_booking_or_gpu_gate(self):
        self.proof['bookings']=[self.ticket('gpu')]
        result=policy.validate(self.proof,self.now,300)
        self.assertIsNone(result['CPU_booking_id'])
        for name in ('cpu_booking_claimed','GPU_approved','runtime_Gates_granted'):
            self.assertIs(result[name],False)

    def test_malformed_snapshot_is_not_empty_clearance(self):
        for field in ('resources','bookings'):
            for value in ({},'',None,[None],[{}]):
                proof=copy.deepcopy(self.proof);proof[field]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                    policy.validate(proof,self.now,300)

    def test_raw_API_validation_precedes_filtering(self):
        raw=dict(resources=self.proof['resources'],bookings=[])
        normalized=policy.normalize_snapshot(raw,self.now)
        policy.validate(normalized,self.now,300)
        for name in ('resources','bookings'):
            for value in ({},'',None,[None],[{}]):
                broken=copy.deepcopy(raw);broken[name]=value
                with self.subTest(name=name,value=value),self.assertRaises(ValueError):
                    policy.normalize_snapshot(broken,self.now)
        raw['bookings']=[self.ticket(start=True)]
        with self.assertRaises(ValueError):policy.normalize_snapshot(raw,self.now)

    def test_foreign_cpu_whole_unknown_lane_and_cleanup_tail_rejected(self):
        for lane in ('cpu',None,'unknown'):
            proof=copy.deepcopy(self.proof);proof['bookings']=[self.ticket(lane)]
            with self.subTest(lane=lane),self.assertRaises(ValueError):
                policy.validate(proof,self.now,300)
        self.proof['bookings']=[self.ticket(start=self.now+329999)]
        with self.assertRaises(ValueError):policy.validate(self.proof,self.now,300)

    def test_exact_nonoverlap_and_owned_cpu_are_allowed(self):
        self.proof['bookings']=[self.ticket(end=self.now,start=self.now-1000),
            self.ticket(start=self.now+330000,end=self.now+600000),self.ticket(user='boyjiang')]
        policy.validate(self.proof,self.now,300)

    def test_old_window_stale_future_and_untrusted_proofs_rejected(self):
        for observed in (self.now-1,self.now+1,self.now-300001):
            proof=copy.deepcopy(self.proof);proof['observed_ms']=observed
            with self.assertRaises(ValueError):policy.validate(proof,self.now,300)
        for field,value in (('origin','fixture'),('read_only',False)):
            proof=copy.deepcopy(self.proof);proof[field]=value
            with self.assertRaises(ValueError):policy.validate(proof,self.now,300)

    def test_latest_admission_and_cleanup_boundary(self):
        now=policy.END_MS-330000;self.proof['observed_ms']=now
        policy.validate(self.proof,now,300)
        with self.assertRaises(ValueError):policy.validate(self.proof,now+1,300)
        with self.assertRaises(ValueError):policy.validate(self.proof,policy.START_MS-1,1)

    def test_bad_interval_owner_resource_and_budgets_rejected(self):
        for changes in (dict(start_ms=True),dict(end_ms=self.now),dict(user='')):
            row=self.ticket();row.update(changes);proof=copy.deepcopy(self.proof)
            proof['bookings']=[row]
            with self.assertRaises(ValueError):policy.validate(proof,self.now,300)
        self.proof['resources'][0]['active']=False
        with self.assertRaises(ValueError):policy.validate(self.proof,self.now,300)
        for seconds in (True,0,301,float('inf')):
            with self.assertRaises(ValueError):policy.validate(self.proof,self.now,seconds)


if __name__=='__main__':unittest.main()
