"""Local service-identity fixtures only; no actual proc/SSH inspection."""
import copy
import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
import space_user_service_guard as guard


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.value=dict(boot_id=guard.BOOT,
            child=dict(pid=3831927,uid=2147,comm='(sd-pam)',ppid=3831926,start_ticks=23944191,cgroup=guard.CGROUP,cmdline_sha256=guard.PAM_SHA),
            parent=dict(pid=3831926,uid=2147,comm='systemd',ppid=1,start_ticks=23944190,cgroup=guard.CGROUP,cmdline_sha256=guard.USER_SHA,exe='/usr/lib/systemd/systemd'),
            init=dict(pid=1,uid=0,comm='systemd',ppid=0,start_ticks=856,cgroup='0::/init.scope\n',cmdline_sha256=guard.INIT_SHA))

    def test_exact_observed_chain_allowed(self):guard.validate(self.value)
    def test_boot_rejected(self):
        self.value['boot_id']='other'
        with self.assertRaises(ValueError):guard.validate(self.value)
    def test_all_child_identity_constraints(self):
        for k,v in [('uid',0),('comm','python'),('ppid',999),('start_ticks',0),('cmdline_sha256','x'),('cgroup','else'),('pid',True)]:
            value=copy.deepcopy(self.value);value['child'][k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):guard.validate(value)
    def test_all_parent_identity_constraints(self):
        for k,v in [('uid',0),('comm','python'),('ppid',99),('exe','/tmp/systemd'),('cmdline_sha256','x'),('cgroup','else'),('start_ticks',23944199)]:
            value=copy.deepcopy(self.value);value['parent'][k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):guard.validate(value)
    def test_fixed_init_anchor_constraints(self):
        for k,v in [('uid',2147),('pid',2),('ppid',2),('comm','python'),('start_ticks',857),('cgroup','else'),('cmdline_sha256','x')]:
            value=copy.deepcopy(self.value);value['init'][k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):guard.validate(value)
    def test_identity_double_read_must_match(self):
        after=copy.deepcopy(self.value);after['child']['start_ticks']+=1
        with patch.object(guard,'snapshot',side_effect=[self.value,after]):
            with self.assertRaisesRegex(ValueError,'changed'):guard.exception(None,3831927)
    def test_snapshot_evidence_and_hash_returned(self):
        with patch.object(guard,'snapshot',side_effect=[self.value,copy.deepcopy(self.value)]):
            result=guard.exception(None,3831927)
        self.assertEqual(result['snapshot'],self.value);self.assertEqual(len(result['sha256']),64)
    def test_non_pam_can_only_fall_back_to_existing_ssh_rule(self):
        with patch.object(guard,'snapshot',return_value=None):self.assertIsNone(guard.exception(None,77))
    def test_callback_restored_after_success(self):
        original=Mock(return_value=None);assets=SimpleNamespace(pam_exception=original)
        assets.guard_processes=lambda proc:assets.pam_exception(proc,3831927)
        with patch.object(guard,'snapshot',side_effect=[self.value,copy.deepcopy(self.value)]):result=guard.guard_processes(assets,None)
        self.assertEqual(result['snapshot'],self.value);self.assertIs(assets.pam_exception,original)
    def test_readable_project_cwd_stays_rejected_and_callback_restored(self):
        original=Mock(return_value=None);assets=SimpleNamespace(pam_exception=original,guard_processes=Mock(side_effect=ValueError('Project cwd active')))
        with patch.object(guard,'snapshot',side_effect=AssertionError('must not exempt readable cwd')):
            with self.assertRaisesRegex(ValueError,'Project cwd'):guard.guard_processes(assets,None)
        self.assertIs(assets.pam_exception,original);original.assert_not_called()
    def test_invalid_service_cannot_be_exempted(self):
        self.value['parent']['exe']='/tmp/fake';original=Mock(return_value=None);assets=SimpleNamespace(pam_exception=original)
        assets.guard_processes=lambda proc:assets.pam_exception(proc,3831927)
        with patch.object(guard,'snapshot',return_value=self.value):
            with self.assertRaises(ValueError):guard.guard_processes(assets,None)
        self.assertIs(assets.pam_exception,original)


if __name__=='__main__':unittest.main()
