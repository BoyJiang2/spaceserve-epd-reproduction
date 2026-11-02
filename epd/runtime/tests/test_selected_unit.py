"""Selected120 vectors and frozen calibration bindings, using CPU-only fixtures."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiment_plan import CANDIDATES, candidate_id, config_sha256
from fixed_unit import official_servers
from selected_unit import make_batches, session_batches, validate_spec


class SelectedUnitTests(unittest.TestCase):
    def setUp(self):
        self.dataset = str(Path(__file__).resolve().parent)
        self.manifest = b'CPU fixture RGB manifest'
        self.source = '1' * 64
        fixtures = []
        for session in ('cold', 'restart'):
            for images in (1, 4, 8):
                for tokens in (32, 128):
                    for concurrency, count in ((1, 2), (8, 8)):
                        case = f'i{images}-o{tokens}-c{concurrency}'
                        for index in range(count):
                            fixtures.append({'fixture_id': f'{session}-{case}-{index}',
                                'session': session, 'case': case, 'output_tokens': tokens,
                                'input': {'prompt': 'Describe the image.', 'images': [
                                    {'path': str(Path(self.dataset) / f'image-{j}.jpg'),
                                     'rgb_sha256': 'a' * 64} for j in range(images)]}})
        self.fixtures = {'fixtures': fixtures}
        sessions = make_batches(self.fixtures)
        candidate = next(c for c in CANDIDATES if c[0] == 'replicas' and c[3] == 4)
        self.config = {'gpu_uuids': ['GPU-fixture-0', 'GPU-fixture-1', 'GPU-fixture-2']}
        self.spec = {'schema': 'epd-fixed-unit-v1', 'phase': 'selected_g3', 'unit': 'replicas',
            'candidate': candidate_id(candidate), 'candidate_config_sha256': config_sha256(candidate),
            'source_manifest_sha256': self.source, 'runtime_binding_sha256': '2' * 64,
            'rgb_manifest_sha256': hashlib.sha256(self.manifest).hexdigest(),
            'rgb_manifest': str(Path(self.dataset) / 'fixture-rgb.json'),
            'model': 'MiniCPM-V-2_6', 'dataset': self.dataset,
            'urls': ['http://127.0.0.1:18310', 'http://127.0.0.1:18311', 'http://127.0.0.1:18312'],
            'max_requests': 120, 'wall_seconds': 1600, 'request_diagnostics': True,
            'sessions': sessions, 'batches': sessions['cold'] + sessions['restart']}
        self.spec['servers'] = official_servers(self.spec, self.config)
        self.selection = {'selected': {}, 'required_full_G3': {}}
        for system in ('replicas', 'pd', 'epd'):
            chosen = next(c for c in CANDIDATES if c[0] == system and c[3] == 4)
            self.selection['selected'][system] = {'candidate': candidate_id(chosen)}
            self.selection['required_full_G3'][system] = {'candidate': candidate_id(chosen), 'requests': 120,
                'candidate_config_sha256': config_sha256(chosen),
                'source_manifest_sha256': self.source, 'runtime_binding_sha256': '2' * 64}

    def validate(self):
        with patch.object(Path, 'read_bytes', return_value=self.manifest):
            return validate_spec(self.spec, self.config, self.source, self.selection)

    def first(self, session='cold'):
        return self.spec['sessions'][session][0]['requests'][0]

    def test_complete_two_sessions_and_three_replica_distribution(self):
        self.assertEqual(self.validate(), 120)
        ids = set()
        for name in ('cold', 'restart'):
            batches = session_batches(self.spec, name)
            rows = [row for batch in batches for row in batch['requests']]
            self.assertEqual(len(batches), 12)
            self.assertEqual([r['dispatch_index'] for r in rows], list(range(60)))
            self.assertEqual([sum(r['dispatch_index'] % 3 == i for r in rows) for i in range(3)], [20] * 3)
            ids.update(r['fixture_id'] for r in rows)
        self.assertEqual(len(ids), 120)

    def test_extra_request_rejected(self):
        self.spec['sessions']['cold'][0]['requests'].append(copy.deepcopy(self.first()))
        with self.assertRaises(ValueError): self.validate()

    def test_duplicate_across_sessions_rejected(self):
        self.first('restart')['fixture_id'] = self.first()['fixture_id']
        with self.assertRaises(ValueError): self.validate()

    def test_wrong_case_order_rejected(self):
        rows = self.spec['sessions']['cold']
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(ValueError): self.validate()

    def test_restart_dispatch_must_start_at_zero(self):
        self.first('restart')['dispatch_index'] = 60
        with self.assertRaises(ValueError): self.validate()

    def test_wrong_image_count_rejected(self):
        self.first()['input']['images'] *= 4
        with self.assertRaises(ValueError): self.validate()

    def test_wrong_output_geometry_rejected(self):
        self.spec['sessions']['cold'][0]['tokens'] = 31
        with self.assertRaises(ValueError): self.validate()

    def test_nonhex_rgb_rejected(self):
        self.first()['input']['images'][0]['rgb_sha256'] = 'g' * 64
        with self.assertRaises(ValueError): self.validate()

    def test_image_outside_dataset_rejected(self):
        self.first()['input']['images'][0]['path'] = str(Path(self.dataset).parent / 'outside.jpg')
        with self.assertRaises(ValueError): self.validate()

    def test_system_candidate_mismatch_rejected(self):
        self.spec['unit'] = 'pd'
        with self.assertRaises(ValueError): self.validate()

    def test_new_deadline_rejected(self):
        self.spec['wall_seconds'] = 1601
        with self.assertRaises(ValueError): self.validate()

    def test_extra_budget_rejected(self):
        self.spec['max_requests'] = 121
        with self.assertRaises(ValueError): self.validate()

    def test_noninteger_budget_rejected(self):
        self.spec['max_requests'] = 120.0
        with self.assertRaises(ValueError): self.validate()

    def test_partial_system_selection_rejected(self):
        del self.selection['selected']['pd']
        with self.assertRaises(ValueError): self.validate()

    def test_all_frozen_profiles_accept_the_same_vector(self):
        for candidate in CANDIDATES:
            with self.subTest(candidate=candidate_id(candidate)):
                system = candidate[0]
                self.spec.update(unit=system, candidate=candidate_id(candidate),
                                 candidate_config_sha256=config_sha256(candidate))
                self.spec['urls'] = (['http://127.0.0.1:18310', 'http://127.0.0.1:18311',
                                     'http://127.0.0.1:18312'] if system == 'replicas'
                                    else ['http://127.0.0.1:18310'])
                self.spec['servers'] = official_servers(self.spec, self.config)
                self.selection['selected'][system] = {'candidate': candidate_id(candidate)}
                self.selection['required_full_G3'][system].update(candidate=candidate_id(candidate),
                    candidate_config_sha256=config_sha256(candidate))
                self.assertEqual(self.validate(), 120)

    def test_diagnostics_cannot_be_disabled(self):
        self.spec['request_diagnostics'] = False
        with self.assertRaises(ValueError): self.validate()

    def test_unknown_session_rejected(self):
        with self.assertRaises(ValueError): session_batches(self.spec, 'third')

    def test_selected_candidate_must_match(self):
        self.selection['selected']['replicas']['candidate'] = 'not-selected'
        with self.assertRaises(ValueError): self.validate()

    def test_foreign_gpu_argv_rejected(self):
        self.spec['servers'][0]['CUDA_VISIBLE_DEVICES'] = 'GPU-foreign'
        with self.assertRaises(ValueError): self.validate()

    def test_wrong_source_rejected(self):
        self.spec['source_manifest_sha256'] = '3' * 64
        with self.assertRaises(ValueError): self.validate()

    def test_wrong_runtime_rejected(self):
        self.spec['runtime_binding_sha256'] = '3' * 64
        with self.assertRaises(ValueError): self.validate()

    def test_rgb_manifest_bytes_rejected(self):
        self.spec['rgb_manifest_sha256'] = '0' * 64
        with self.assertRaises(ValueError): self.validate()

    def test_missing_fixture_rejected(self):
        self.fixtures['fixtures'].pop()
        with self.assertRaises(ValueError): make_batches(self.fixtures)

    def test_unknown_fixture_session_rejected(self):
        self.fixtures['fixtures'][0]['session'] = 'unknown'
        with self.assertRaises(ValueError): make_batches(self.fixtures)


if __name__ == '__main__':
    unittest.main()
