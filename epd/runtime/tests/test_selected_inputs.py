"""Read real small fixture files; reviews are CPU-only mocks, never GPU permits."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import preflight_guard
import selected_inputs
from experiment_plan import CANDIDATES, candidate_id
import test_selected_unit


class SelectedInputTests(unittest.TestCase):
    def setUp(self):
        fixture = test_selected_unit.SelectedUnitTests()
        fixture.setUp()
        self.fixture = fixture
        parent = Path(os.environ['EPD_CPU_TEST_TMP']).resolve(strict=True)
        self.temp = tempfile.TemporaryDirectory(prefix='selected-input-cpu-', dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.owner = self.root / 'inputs.json'
        self.template = self.root / 'selected-template.json'
        self.template.write_text(json.dumps({'schema': 'epd-selected-template-v1', 'phase': 'selected_g3',
            'model': 'MiniCPM-V-2_6', 'dataset': fixture.dataset, 'urls_by_system': {
                'replicas': fixture.spec['urls'], 'pd': ['http://127.0.0.1:18320'],
                'epd': ['http://127.0.0.1:18330']}}))
        manifest = self.write('source.json', {'files': [{'path': self.template.name,
            'sha256': hashlib.sha256(self.template.read_bytes()).hexdigest()}]})
        self.inputs = {'source_manifest_file': manifest['path'], 'source_manifest_sha256': manifest['sha256'],
                       'deploy_sha256': 'a' * 64}
        self.deployed = {'host': 'CPU-fixture-host', 'uid': 0, 'boot_id': 'CPU-fixture-boot'}
        self.config = fixture.config
        self.runtime = {**self.deployed,
            'gpu_capacity_bytes': {uuid: 10000 for uuid in self.config['gpu_uuids']},
            'gpu_admission_free_bytes': {uuid: 10000 for uuid in self.config['gpu_uuids']},
            'gpu_memory_cap_bytes': {uuid: 6500 for uuid in self.config['gpu_uuids']},
            'memory_limit_fraction': .65, 'memory_sample_max_gap_s': 1.0}
        self.body = {'kind': 'calibration_selection', 'source_manifest_sha256': manifest['sha256'],
            'deploy_sha256': self.inputs['deploy_sha256'], 'selected_candidates': [
                value['candidate'] for value in fixture.selection['selected'].values()], 'raw_files': []}
        runtime = self.bind('runtime_binding', self.runtime)
        self.selection = fixture.selection
        for required in self.selection['required_full_G3'].values():
            required['source_manifest_sha256'] = manifest['sha256']
            required['runtime_binding_sha256'] = runtime['sha256']
        self.bind('selection', self.selection)
        self.bind('selected_fixtures', fixture.fixtures)
        self.bind('rgb_manifest', {'CPU-fixture': 'RGB manifest only'})

    def write(self, name, body):
        path = self.root / name
        path.write_text(json.dumps(body))
        return {'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def bind(self, key, body):
        old = self.body.get(key)
        if old is not None:
            self.body['raw_files'].remove(old)
        value = self.write(key + '.json', body)
        self.body[key] = value
        self.body['raw_files'].append(value)
        return value

    def load(self, system='replicas'):
        prerequisite = self.write('prerequisite.json', {'proof': self.body,
            'review_file': 'CPU-MOCK-not-a-real-review.json', 'review_sha256': 'b' * 64})
        self.inputs.update(prerequisite_file=prerequisite['path'], prerequisite_sha256=prerequisite['sha256'])
        with patch.object(selected_inputs, 'SOURCE', self.root), \
             patch.object(preflight_guard, 'require_review', return_value={'CPU-MOCK': True}):
            return selected_inputs.load_execution(self.template, self.config, self.inputs, self.owner, system, self.deployed)

    def test_all_three_selected_systems_use_same_full_input_vector(self):
        specs = [self.load(system) for system in ('replicas', 'pd', 'epd')]
        self.assertEqual([spec['unit'] for spec in specs], ['replicas', 'pd', 'epd'])
        self.assertEqual([len(spec['servers']) for spec in specs], [3, 1, 1])
        self.assertTrue(all(spec['batches'] == specs[0]['batches'] for spec in specs))
        self.assertTrue(all(spec['max_requests'] == 120 and spec['wall_seconds'] == 1600 for spec in specs))

    def test_unknown_system_rejected(self):
        with self.assertRaises(ValueError):
            self.load('runner-up')

    def test_unreviewed_artifact_rejected(self):
        self.body['raw_files'].remove(self.body['selected_fixtures'])
        with self.assertRaises(ValueError):
            self.load()

    def test_tampered_raw_fixture_rejected(self):
        (self.root / self.body['selected_fixtures']['path']).write_text('{}')
        with self.assertRaises(ValueError):
            self.load()

    def test_wrong_prerequisite_source_rejected(self):
        self.body['source_manifest_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.load()

    def test_unselected_candidate_rejected(self):
        self.body['selected_candidates'].remove(self.selection['selected']['replicas']['candidate'])
        with self.assertRaises(ValueError):
            self.load()

    def test_changed_template_rejected(self):
        self.template.write_text(self.template.read_text() + ' ')
        with self.assertRaises(ValueError):
            self.load()

    def test_runtime_must_match_actual_boot(self):
        self.deployed['boot_id'] = 'another-boot'
        with self.assertRaises(ValueError):
            self.load()

    def test_other_system_selection_source_cannot_be_omitted(self):
        self.selection['required_full_G3']['epd']['source_manifest_sha256'] = '0' * 64
        self.bind('selection', self.selection)
        with self.assertRaises(ValueError):
            self.load()

    def test_no_runner_up_fallback(self):
        runner_up = next(item for item in CANDIDATES if item[0] == 'replicas' and item[3] == 8)
        self.selection['selected']['replicas']['candidate'] = candidate_id(runner_up)
        self.bind('selection', self.selection)
        with self.assertRaises(ValueError):
            self.load()


if __name__ == '__main__':
    unittest.main()
