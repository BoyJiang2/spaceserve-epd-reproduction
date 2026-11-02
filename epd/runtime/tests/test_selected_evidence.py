"""Map synthetic production artifacts through the original strict G3 consumer, CPU only."""
import json
from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import selected_evidence
from preflight_guard import digest
import test_preflight_v5 as legacy


class SelectedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = legacy.SelectedG3CPU()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.original = self.fixture.bundle()
        self.owner = self.fixture.owner
        self.data = self.fixture.data
        self.payload = {'schema': 'selected-evidence-input-v1',
            'config': self.fixture.write('producer-config.json', self.fixture.config),
            'source_manifest': self.original['source_manifest'], 'deployment': self.original['deployment'],
            'runtime_binding': self.original['runtime_binding'], 'selection': self.original['selection'],
            'fixtures': self.original['systems']['replicas']['inputs'], 'units': {}}
        self.reference = self.data / 'producer-native-reference.jsonl'
        selection = json.loads((self.data / self.original['selection']['path']).read_bytes())
        rgb = self.fixture.write('CPU-MOCK-rgb.json', {'CPU-MOCK': 'no actual image/GPU'})
        body = {'kind': 'calibration_selection', 'source_manifest_sha256': self.fixture.source_sha,
            'deploy_sha256': self.fixture.deploy_sha,
            'selected_candidates': [row['candidate'] for row in selection['selected'].values()],
            'selection': self.payload['selection'], 'selected_fixtures': self.payload['fixtures'],
            'runtime_binding': self.payload['runtime_binding'], 'rgb_manifest': rgb,
            'raw_files': [self.payload[key] for key in ('selection', 'fixtures', 'runtime_binding')] + [rgb]}
        approval = self.fixture.fake_review('CPU-MOCK-calibration-review.json', 'G3', digest(body))
        prerequisite = self.fixture.write('CPU-MOCK-calibration-prerequisite.json', {
            'proof': body, 'review_file': approval['path'], 'review_sha256': approval['sha256']})
        for system, group in self.original['systems'].items():
            output = self.data / system
            output.mkdir()
            claim_path = self.data / group['claim']['path']
            claim = json.loads(claim_path.read_bytes())
            execution = {'schema': 'CPU-MOCK-execution-only', 'candidate': group['candidate'],
                         'candidate_config_sha256': group['candidate_config_sha256']}
            (output / 'execution.json').write_text(json.dumps(execution))
            claim.update(execution=execution, execution_sha256=digest(execution))
            claim['unit']['execution_sha256'] = digest(execution)
            claim_path.write_text(json.dumps(claim))
            ledger_path = self.data / group['ledger']['path']
            ledger = json.loads(ledger_path.read_bytes())
            ledger['units']['selected_g3/' + system] = claim['unit']
            ledger_path.write_text(json.dumps(ledger))
            receipt = {'claim': str(claim_path), 'ledger': str(ledger_path),
                       'claim_sha256': self.fixture.sha(claim_path), 'key': 'selected_g3/' + system}
            terminal = {'state': 'released', 'failure': None, 'errors': [], 'sessions': {}, 'claim': receipt}
            for name, session in group['sessions'].items():
                folder = output / name
                (folder / 'memory').mkdir(parents=True)
                saved = {key: session[key] for key in ('run_id', 'start_utc_ms', 'start_monotonic', 'end_utc_ms', 'end_monotonic')}
                saved['terminal'] = str(folder / 'terminal.json')
                (folder / 'session.json').write_text(json.dumps(saved))
                terminal['sessions'][name] = saved
                (folder / 'terminal.json').write_text(json.dumps({
                    'state': 'released', 'failure': None, 'errors': [], 'claim': receipt}))
                for key, relative in (('requests', 'requests.jsonl'), ('client_windows', 'case-windows.jsonl'),
                        ('endpoints', 'endpoints.json'), ('registry', 'memory/process-registry.json'),
                        ('provider', 'memory/provider.json'), ('raw_nvml', 'memory/raw-nvml.jsonl'),
                        ('memory_samples', 'memory/samples.jsonl'), ('booking', 'booking.json'), ('release', 'release.json')):
                    shutil.copyfile(self.data / session[key]['path'], folder / relative)
            (output / 'terminal.json').write_text(json.dumps(terminal))
            inputs = {**self.fixture.inputs, 'run_id': claim['unit']['run_id'],
                'booking_file': group['admission_booking']['path'], 'booking_sha256': group['admission_booking']['sha256'],
                'prerequisite_file': prerequisite['path'], 'prerequisite_sha256': prerequisite['sha256']}
            self.payload['units'][system] = {'inputs': self.fixture.write(system + '-actual-inputs.json', inputs),
                'terminal': {'path': (output / 'terminal.json').relative_to(self.data).as_posix(),
                             'sha256': self.fixture.sha(output / 'terminal.json')}}

    def build(self):
        self.owner.write_text(json.dumps(self.payload))
        return selected_evidence.build(self.owner, self.payload, self.reference)

    def test_original_strict_consumer_accepts_complete_cpu_artifact_mapping(self):
        proof = self.build()
        result = self.fixture.consume_fake_fixture(proof)
        self.assertEqual(result['state'], 'independent_full_selected_G3_consumed')
        self.assertIn('blocked', result['formal_admission'])
        for group in proof['systems'].values():
            self.assertEqual(group['reference'], proof['systems']['replicas']['reference'])
        original = b''.join((self.data / self.original['systems']['replicas']['sessions'][name]['requests']['path']).read_bytes()
                            for name in ('cold', 'restart'))
        self.assertEqual(self.reference.read_bytes(), original)

    def test_missing_system_rejected_without_reference(self):
        del self.payload['units']['pd']
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse(self.reference.exists())

    def test_changed_actual_request_is_caught_by_strict_consumer(self):
        path = self.data / 'pd/restart/requests.jsonl'
        rows = [json.loads(line) for line in path.read_bytes().splitlines()]
        rows[0]['output_token_ids'][0] = 999
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        with self.assertRaisesRegex(ValueError, 'reference differs'):
            self.fixture.consume_fake_fixture(self.build())

    def test_missing_release_is_never_fabricated(self):
        (self.data / 'epd/restart/release.json').unlink()
        with self.assertRaises(FileNotFoundError):
            self.build()
        self.assertFalse(self.reference.exists())

    def test_raw_api_release_unknown_is_rejected_by_strict_consumer(self):
        path = self.data / 'pd/cold/release.json'
        release = json.loads(path.read_bytes())
        release['api_exit_observations'][0]['state'] = 'unknown'
        path.write_text(json.dumps(release))
        with self.assertRaisesRegex(ValueError, 'release is unconfirmed'):
            self.fixture.consume_fake_fixture(self.build())

    def test_existing_reference_not_overwritten(self):
        self.reference.write_bytes(b'original evidence')
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual(self.reference.read_bytes(), b'original evidence')


if __name__ == '__main__':
    unittest.main()
