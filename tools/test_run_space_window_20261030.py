"""CPU-only argv checks; production remote lifecycle remains unvalidated."""
import unittest
import json
from unittest.mock import Mock, patch
import space_window_20261030 as window
import test_space_window_20261030 as window_tests
from pathlib import Path
import run_space_window_20261030 as launcher


class CommandTests(unittest.TestCase):
    def test_prepare_binds_designated_commit(self):
        argv=launcher.command('prepare',Path('/scope/config.json'),'a'*40)
        self.assertEqual(argv[-2:],['--commit','a'*40])
        self.assertEqual(argv[1:4],['-I','-S','-B'])

    def test_runtime_phases_do_not_reprepare(self):
        for phase in ('cpu','numeric','model','formal'):
            argv=launcher.command(phase,Path('/scope/config.json'),'b'*40)
            self.assertNotIn('--commit',argv)
            self.assertEqual(argv[-3:],[phase,'--config',str(Path('/scope/config.json'))])

    def test_unknown_phase_and_revision_refused(self):
        for phase,commit in [('retry','a'*40),('prepare','main'),('formal','A'*40)]:
            with self.assertRaises(ValueError):launcher.command(phase,Path('/config'),commit)


class FinalAdmissionTests(unittest.TestCase):
    def setUp(self):
        fixture=window_tests.WindowTests();fixture.setUp()
        self.proof,self.config=fixture.proof,fixture.config
        self.supervision=Mock()

    def attempt(self, now):
        with patch.object(launcher.time,'time',return_value=now/1000):
            return launcher.supervise_phase(window,self.proof,self.config,'formal',None,self.supervision,[],{},None,lambda:None)

    def test_final_spawn_receives_complete_budget(self):
        now=window.END-12180000;self.proof['observed_ms']=now
        result=self.attempt(now)
        self.assertEqual(result['admitted_ms'],now)
        self.assertEqual(self.supervision.supervise.call_args.args[-1],12060)

    def test_refresh_time_cannot_consume_cleanup_margin(self):
        now=window.END-12180000;self.proof['observed_ms']=now
        window.validate(self.proof,now,'formal',self.config)
        with self.assertRaises(ValueError):self.attempt(now+1)
        self.supervision.supervise.assert_not_called()

    def test_snapshot_expires_before_spawn(self):
        with self.assertRaises(ValueError):self.attempt(window.START+300001)
        self.supervision.supervise.assert_not_called()


if __name__=='__main__':unittest.main()
