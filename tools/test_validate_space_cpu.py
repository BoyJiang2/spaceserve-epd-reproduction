"""CPU ownership/environment contracts; never spawn or query a host."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import validate_space_cpu as cpu


class CPUContracts(unittest.TestCase):
    def row(self,pid,ppid=999,uid=2147,ticks=100,marked=False):
        return {'pid':pid,'ppid':ppid,'uid':uid,'start_ticks':ticks,
                'nonce':'fixed' if marked else None,'root':str(cpu.RUN) if marked else None,
                'run_id':cpu.RUN_ID if marked else None}

    def test_bystanders_foreign_uid_and_old_processes_do_not_gain_ownership(self):
        rows={1:self.row(1,marked=True,uid=0),2:self.row(2),3:self.row(3,marked=True,ticks=1)}
        self.assertEqual(cpu.select_owned(rows,{},'fixed',50),{})

    def test_nonce_requires_exact_root_and_run(self):
        rows={1:self.row(1,marked=True),2:self.row(2,marked=True),3:self.row(3,marked=True)}
        rows[2]['root']='/another-project';rows[3]['run_id']='other'
        self.assertEqual(set(cpu.select_owned(rows,{},'fixed',50)),{1})

    def test_real_descendant_chain_survives_separate_sessions_and_orphaning(self):
        root=self.row(1,marked=True);rows={1:root,2:self.row(2,ppid=1),3:self.row(3,ppid=2)}
        selected=cpu.select_owned(rows,{1:root},'fixed',50)
        self.assertEqual(set(selected),{1,2,3})
        orphan=self.row(3,ppid=1)
        self.assertEqual(set(cpu.select_owned({3:orphan},selected,'fixed',50)),{3})

    def test_recycled_parent_and_pid_never_inherit_recorded_ownership(self):
        root=self.row(1);replacement=self.row(1,ticks=101)
        rows={1:replacement,2:self.row(2,ppid=1)}
        self.assertEqual(cpu.select_owned(rows,{1:root},'fixed',50),{})

    def test_environment_is_offline_and_hides_gpu_without_inherited_injection(self):
        env=cpu.child_environment('fixed')
        self.assertEqual(env['CUDA_VISIBLE_DEVICES'],'')
        for name in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_DATASETS_OFFLINE','PYTHONNOUSERSITE'):
            self.assertEqual(env[name],'1')
        self.assertNotIn('PYTHONPATH',env)
        self.assertEqual(env['REPRO_CPU_ROOT'],str(cpu.RUN))
        self.assertLess(len(env['TMPDIR']),70)


if __name__=='__main__':unittest.main(verbosity=2)
