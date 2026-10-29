"""CPU-only configuration contracts; do not create runtime/asset directories or use GPUs."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reproduction_paths import ProjectLayout


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.candidate = {'schema':'reproduction-project-v1','project':'spaceserve',
            'project_root':'/local/boyjiang/spaceserve','state':'candidate','host':'qjh003','uid':2147,
            'run_id':None,'gpu_devices':[],'gpu_uuids':[],'allowed_actions':[],
            'booking':None,'source_commit':None,'source_manifest_sha256':None}

    def approved(self):
        return {**copy.deepcopy(self.candidate), 'state':'approved_scope','run_id':'test-run',
            'gpu_devices':[0], 'gpu_uuids':['GPU-00000000-0000-0000-0000-000000000001'],
            'allowed_actions':['numeric'], 'booking':{'CPU-MOCK':'not actual proof'},
            'source_commit':'a'*40,'source_manifest_sha256':'b'*64}

    def test_plan_reads_without_creating_directories_and_keeps_assets_outside_runs(self):
        plan = ProjectLayout(self.candidate).describe()
        self.assertEqual(plan['code_root'], '/local/boyjiang/spaceserve/repo/spaceserve/runtime')
        self.assertEqual(plan['run_root'], '/local/boyjiang/spaceserve/runs/UNCONFIGURED')
        self.assertFalse(plan['creates_files']); self.assertFalse(plan['grants_GPU_or_Gates'])
        self.assertNotIn('/runs/', plan['assets_root'])

    def test_candidate_refuses_all_execution_phases(self):
        layout = ProjectLayout(self.candidate)
        for phase in ('numeric','model','formal'):
            with self.assertRaises(ValueError): layout.require_scope(phase)

    def test_old_host_old_root_wrong_project_and_bad_uid_refused(self):
        for key,value in (('host','qjh000'),('project_root','/var/tmp/old-window'),
                          ('project','other'),('uid',True)):
            data = {**self.candidate,key:value}
            with self.assertRaises(ValueError): ProjectLayout(data)

    def test_run_id_cannot_escape_or_be_unconfigured_reserved_value(self):
        for run in ('', '.', '..', '../x', '/x', 'x/y', 'x\\y', 'UNCONFIGURED'):
            with self.assertRaises(ValueError): ProjectLayout({**self.candidate,'run_id':run})

    def test_assets_reject_absolute_parent_and_windows_escape(self):
        layout = ProjectLayout(self.candidate)
        for value in ('', '.', '../outside', '/outside', 'model/../../outside', 'x\\y', 'C:/outside'):
            with self.assertRaises(ValueError): layout.asset(value)

    def test_gpu_uuid_duplicates_bad_types_or_mismatched_count_refused(self):
        good = self.approved()
        for devices,uuids in (([True],good['gpu_uuids']),([0,0],good['gpu_uuids']*2),
                              ([0],[]),([0],['OLD-UUID'])):
            with self.assertRaises(ValueError): ProjectLayout({**good,'gpu_devices':devices,'gpu_uuids':uuids})

    def test_exact_phase_source_and_booking_required_before_existing_guards(self):
        with patch('reproduction_paths.socket.gethostname',return_value='qjh003'), \
             patch('reproduction_paths.os.getuid',return_value=2147,create=True):
            ProjectLayout(self.approved()).require_scope('numeric')
            for key,value in (('booking',None),('source_commit','OLD'),('allowed_actions',[]),('run_id',None)):
                with self.assertRaises(ValueError): ProjectLayout({**self.approved(),key:value}).require_scope('numeric')
            with self.assertRaises(ValueError): ProjectLayout(self.approved()).require_scope('model')

    def test_other_project_config_is_not_silently_loaded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'CPU-MOCK.json'; path.write_text(json.dumps(self.candidate))
            with self.assertRaises(ValueError): ProjectLayout.read(path,'epd')

    def test_temporary_scope_is_structural_only_and_never_formal_or_epd(self):
        good={**self.approved(),'booking':None,'temporary_gpu_use':{'CPU-MOCK':'not actual authorization'},
              'allowed_actions':['numeric','model','formal']}
        with patch('reproduction_paths.socket.gethostname',return_value='qjh003'), \
             patch('reproduction_paths.os.getuid',return_value=2147,create=True):
            ProjectLayout(good).require_scope('numeric')
            ProjectLayout(good).require_scope('model')
            with self.assertRaises(ValueError):ProjectLayout(good).require_scope('formal')
            epd={**good,'project':'epd','project_root':'/local/boyjiang/epd',
                 'gpu_devices':[0,1,2],'gpu_uuids':['GPU-'+str(n).zfill(8)+'-0000-0000-0000-000000000001' for n in range(3)]}
            with self.assertRaises(ValueError):ProjectLayout(epd).require_scope('numeric')


if __name__ == '__main__': unittest.main()
