"""Pure booking fixtures; no network, Ray, process or GPU operations."""
import copy
import unittest

import epd_cpu_renewal_20261030 as policy


class RenewalTests(unittest.TestCase):
    def setUp(self):
        self.now=policy.BOOKING['start_ms']+1000000
        self.proof=dict(origin='gputime_read_only_api',read_only=True,observed_ms=self.now,
            resources=[dict(id='h20/qjh003',node='qjh003',active=True,gpu_count=8)],
            bookings=[dict(policy.BOOKING),dict(id='foreignGPU',resource_id='h20/qjh003',
                kind='gpu',user='other',start_ms=policy.BOOKING['start_ms'],end_ms=policy.BOOKING['end_ms'])])

    def test_exact_renewed_CPU_allows_foreign_GPU_without_granting_GPU(self):
        result=policy.validate(self.proof,self.now,360)
        self.assertEqual(result['CPU_booking_id'],policy.BOOKING['id'])
        self.assertFalse(result['GPU_approved']);self.assertFalse(result['runtime_Gates_granted'])

    def test_old_CPU_ticket_cannot_authorize_new_unit(self):
        self.proof['bookings'][0]['id']='bk-20261029T1809-58743aa0'
        with self.assertRaises(ValueError):policy.validate(self.proof,self.now,360)

    def test_CPU_and_whole_node_conflicts_rejected(self):
        for lane in ('cpu',None):
            proof=copy.deepcopy(self.proof);proof['bookings'].append(dict(resource_id='h20/qjh003',
                kind=lane,user='other',start_ms=self.now,end_ms=self.now+360000))
            with self.subTest(lane=lane),self.assertRaises(ValueError):policy.validate(proof,self.now,360)

    def test_stale_future_and_wrong_owner_proofs_rejected(self):
        for delta in (-300001,1):
            proof=copy.deepcopy(self.proof);proof['observed_ms']=self.now+delta
            with self.assertRaises(ValueError):policy.validate(proof,self.now,360)
        self.proof['bookings'][0]['user']='other'
        with self.assertRaises(ValueError):policy.validate(self.proof,self.now,360)

    def test_full_unit_and_reserve_must_fit(self):
        now=policy.BOOKING['end_ms']-479999;self.proof['observed_ms']=now
        with self.assertRaises(ValueError):policy.validate(self.proof,now,360)
        now-=1;self.proof['observed_ms']=now
        self.assertEqual(policy.validate(self.proof,now,360)['booking_end_ms'],policy.BOOKING['end_ms'])

    def test_invalid_or_unbounded_budgets_rejected(self):
        for seconds in (True,0,361,float('inf')):
            with self.assertRaises(ValueError):policy.validate(self.proof,self.now,seconds)

    def test_cleanup_tail_conflict_is_not_available_CPU(self):
        self.proof['bookings'].append(dict(resource_id='h20/qjh003',kind='cpu',user='other',
            start_ms=self.now+360000+10000,end_ms=self.now+600000))
        with self.assertRaises(ValueError):policy.validate(self.proof,self.now,360)


if __name__=='__main__':unittest.main()
