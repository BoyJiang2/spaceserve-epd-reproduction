"""CPU only: exact lane, phase-budget and snapshot boundary regressions."""
import copy
import json
from pathlib import Path
import unittest
import space_window_20261030 as window


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((Path(__file__).resolve().parents[1]/'spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json').read_bytes())
        self.proof=dict(origin='gputime_read_only_api',read_only=True,observed_ms=window.START,
            resources=[dict(id=window.RESOURCE,node='qjh003',active=True,gpu_count=8)],
            bookings=[dict(id=ticket,node='qjh003',resource_id=window.RESOURCE,user='boyjiang',
                kind=kind,start_ms=window.START,end_ms=end) for kind,ticket,end in
                [('cpu',window.CPU,1793329200000),('gpu',window.GPU,window.END)]])

    def test_all_phase_budgets_at_real_start(self):
        for phase in window.BUDGETS:
            with self.subTest(phase=phase):
                value=window.validate(self.proof,window.START,phase,self.config)
                self.assertFalse(value['source_or_runtime_Gates_granted'])
                self.assertEqual(value['cleanup_seconds'],120)

    def test_before_start_refused(self):
        with self.assertRaises(ValueError):window.validate(self.proof,window.START-1,'prepare',self.config)

    def test_stale_future_or_prestart_snapshot(self):
        for observed in (window.START-1,window.START+1,window.START-300001):
            self.proof['observed_ms']=observed
            with self.assertRaises(ValueError):window.validate(self.proof,window.START,'cpu',self.config)

    def test_snapshot_older_than_five_minutes(self):
        with self.assertRaises(ValueError):
            window.validate(self.proof,window.START+300001,'cpu',self.config)

    def test_exact_formal_admission_edge_and_one_ms_late(self):
        now=window.END-12180000;self.proof['observed_ms']=now
        window.validate(self.proof,now,'formal',self.config)
        with self.assertRaises(ValueError):window.validate(self.proof,now+1,'formal',self.config)

    def test_foreign_lane_wrong_owner_duplicate_and_missing(self):
        for change in ('owner','id','duplicate','missing'):
            with self.subTest(change=change):
                proof=copy.deepcopy(self.proof)
                if change=='owner':proof['bookings'][0]['user']='other'
                if change=='id':proof['bookings'][1]['id']='old-ticket'
                if change=='duplicate':proof['bookings'].append(copy.deepcopy(proof['bookings'][0]))
                if change=='missing':proof['bookings'].pop()
                with self.assertRaises(ValueError):window.validate(proof,window.START,'numeric',self.config)

    def test_foreign_conflict(self):
        self.proof['bookings'].append(dict(resource_id=window.RESOURCE,user='other',kind=None,
            start_ms=window.START,end_ms=window.START+60000))
        with self.assertRaises(ValueError):window.validate(self.proof,window.START,'cpu',self.config)

    def test_wrong_resource_gpu_profile_and_auto_extension(self):
        for key,value in [('gpu_devices',[0]),('mask_off',0),('workload_cpu_affinity',[50]),
                          ('temporary_gpu_use',{}),('run_id','space-16-20261029')]:
            with self.subTest(key=key):
                config=copy.deepcopy(self.config);config[key]=value
                with self.assertRaises(ValueError):window.validate(self.proof,window.START,'model',config)

    def test_no_late_extension_even_if_owned_ticket_exists(self):
        now=window.END;self.proof['observed_ms']=now
        with self.assertRaises(ValueError):window.validate(self.proof,now,'cpu',self.config)


if __name__=='__main__':unittest.main()
