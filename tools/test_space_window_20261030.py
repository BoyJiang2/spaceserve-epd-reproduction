"""CPU only: exact lane, phase-budget and snapshot boundary regressions."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import run_space_window_20261030 as runner
import space_window_20261030 as window


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((Path(__file__).resolve().parents[1]/'spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json').read_bytes())
        self.proof=dict(origin='gputime_read_only_api',read_only=True,observed_ms=window.START,
            resources=[dict(id=window.RESOURCE,node='qjh003',active=True,gpu_count=8)],
            bookings=[dict(id=ticket,node='qjh003',resource_id=window.RESOURCE,user='boyjiang',
                kind=kind,start_ms=window.START,end_ms=end) for kind,ticket,end in
                [('gpu',window.GPU,window.END)]])

    def test_all_phase_budgets_at_real_start(self):
        for phase in window.BUDGETS:
            with self.subTest(phase=phase):
                value=window.validate(self.proof,window.START,phase,self.config)
                self.assertFalse(value['source_or_runtime_Gates_granted'])
                self.assertEqual(value['cleanup_seconds'],120)

    def test_gpu_before_start_refused(self):
        now=window.START-1;self.proof['observed_ms']=now
        with self.assertRaises(ValueError):window.validate(self.proof,now,'numeric',self.config)

    def test_historical_human_confirmation_is_not_current_API(self):
        proof=window.human_confirmation(self.config,window.START)
        for phase in window.BUDGETS:
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                window.validate(proof,window.START,phase,self.config)

    def test_stale_future_or_prestart_snapshot(self):
        for observed in (window.CPU_START-1,window.START+1,window.START-300001):
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
                if change=='id':proof['bookings'][0]['id']='old-ticket'
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

    def test_cpu_prepare_before_gpu_start_with_independent_clearance(self):
        now=window.CPU_START+1;self.proof['observed_ms']=now
        for phase in ('prepare','cpu'):
            value=window.validate(self.proof,now,phase,self.config)
            self.assertFalse(value['CPU_booking_claimed'])
            self.assertEqual(value['authorization_kind'],'direct-human-CPU-fresh-clearance')
            self.assertFalse(value['source_or_runtime_Gates_granted'])

    def test_cpu_before_authorized_cpu_window_refused(self):
        now=window.CPU_START-1;self.proof['observed_ms']=now
        with self.assertRaises(ValueError):window.validate(self.proof,now,'prepare',self.config)

    def test_foreign_gpu_only_does_not_grant_or_block_cpu(self):
        now=window.START-1;self.proof['observed_ms']=now
        self.proof['bookings'].append(dict(resource_id=window.RESOURCE,user='other',kind='gpu',start_ms=window.CPU_START,end_ms=window.END))
        window.validate(self.proof,now,'prepare',self.config)
        self.proof['observed_ms']=window.START
        with self.assertRaises(ValueError):window.validate(self.proof,window.START,'numeric',self.config)

    def test_foreign_cpu_or_whole_blocks_preparation(self):
        now=window.CPU_START+1;self.proof['observed_ms']=now
        for kind in ('cpu',None):
            proof=copy.deepcopy(self.proof)
            proof['bookings'].append(dict(resource_id=window.RESOURCE,user='other',kind=kind,start_ms=now,end_ms=now+60000))
            with self.subTest(kind=kind), self.assertRaises(ValueError):window.validate(proof,now,'prepare',self.config)

    def test_unknown_foreign_lane_is_not_an_exemption(self):
        for phase in ('prepare','numeric'):
            for kind in ('unknown','whole-node'):
                proof=copy.deepcopy(self.proof)
                proof['bookings'].append(dict(resource_id=window.RESOURCE,user='other',kind=kind,start_ms=window.START,end_ms=window.END))
                with self.subTest(phase=phase,kind=kind), self.assertRaises(ValueError):
                    window.validate(proof,window.START,phase,self.config)

    def test_cpu_cleanup_edge_is_not_gpu_authorization(self):
        now=window.END-(window.BUDGETS['cpu']+120)*1000;self.proof['observed_ms']=now
        window.validate(self.proof,now,'cpu',self.config)
        with self.assertRaises(ValueError):window.validate(self.proof,now+1,'cpu',self.config)

    def test_cpu_phase_never_queries_gpu(self):
        with patch.object(runner.subprocess,'check_output') as query:
            for phase in ('prepare','cpu'):runner.require_gpu_idle(phase,self.config)
            query.assert_not_called()

    def test_unknown_phase_does_not_bypass_gpu_admission(self):
        with patch.object(runner.subprocess,'check_output') as query:
            with self.assertRaises(ValueError):runner.require_gpu_idle('other',self.config)
            query.assert_not_called()

    def test_gpu_phases_require_actual_strict_idle(self):
        good=self.config['gpu_uuids'][0]+', 0, 0\n'
        for phase in ('numeric','model','formal'):
            with patch.object(runner.subprocess,'check_output',side_effect=[good,'']) as query:
                runner.require_gpu_idle(phase,self.config);self.assertEqual(query.call_count,2)
        with patch.object(runner.subprocess,'check_output',side_effect=[self.config['gpu_uuids'][0]+', 1, 0\n','']):
            with self.assertRaises(ValueError):runner.require_gpu_idle('numeric',self.config)


if __name__=='__main__':unittest.main()
