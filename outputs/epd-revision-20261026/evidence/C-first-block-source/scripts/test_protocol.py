import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import sys
import signal
import unittest
from unittest.mock import patch

from correctness_suite import cases
from freeze_schedule import schedule
try:
    import psutil
except ModuleNotFoundError:
    # Cleanup tests inject a fake process table; the production environment still requires psutil.
    sys.modules['psutil'] = SimpleNamespace()
import owned_processes
import resource_guard


class ProtocolTests(unittest.TestCase):
    def test_shared_host_snapshot_keeps_full_host_context_without_overwrite(self):
        from run_cells import host_snapshot
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            destination = Path(temporary) / 'host.json'
            with patch('run_cells.os.getloadavg', return_value=(1, 2, 3), create=True), patch.object(Path, 'read_text', return_value='MemAvailable: 42 kB\nSwapFree: 9 kB\n'), patch('run_cells.subprocess.check_output', side_effect=['all eight GPUs', 'all compute PIDs'] * 2) as query:
                host_snapshot(destination)
                with self.assertRaises(FileExistsError):
                    host_snapshot(destination)
            data = json.loads(destination.read_text())
            self.assertEqual(data['gpus'], 'all eight GPUs')
            self.assertEqual(data['compute_processes'], 'all compute PIDs')
            self.assertIn('SwapFree', data['meminfo'])
            self.assertEqual(data['load_average'], [1, 2, 3])
            self.assertLessEqual(data['utc_ns'], data['finished_utc_ns'])
            self.assertFalse(any('--id=' in argument for call in query.call_args_list for argument in call.args[0]))

    def test_exiting_identity_denial_only_retries_reads(self):
        error = owned_processes.IdentityUnconfirmed('exiting raylet')
        with patch.object(owned_processes, '_owned_once', side_effect=[error, []]) as scan, patch.object(owned_processes.time, 'sleep') as sleep:
            self.assertEqual(owned_processes.owned(str(owned_processes.ROOT) + ':ours'), [])
            self.assertEqual(scan.call_count, 2)
            sleep.assert_called_once_with(.05)

    def test_persistent_unconfirmed_identity_still_fails(self):
        with patch.object(owned_processes, '_owned_once', side_effect=owned_processes.IdentityUnconfirmed('unknown')), patch.object(owned_processes.time, 'monotonic', side_effect=[0, 2]):
            with self.assertRaises(owned_processes.IdentityUnconfirmed):
                owned_processes.owned(str(owned_processes.ROOT) + ':ours')

    def test_resume_rejects_changed_budget_before_reading_data(self):
        from resume_preflight import validate_checkpoint
        with self.assertRaisesRegex(RuntimeError, 'budget'):
            validate_checkpoint(Path('unused'), {'completed_groups': [], 'remaining_groups': [], 'reference_requests': 17, 'target_requests_completed': 204, 'new_target_budget': 68})

    def test_resume_reference_and_single_start_guards(self):
        from resume_preflight import validate_checkpoint, COMPLETED_GROUPS, REMAINING_GROUPS
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            root = Path(temporary)
            destination = root / 'results/preflight-models'
            for name in COMPLETED_GROUPS:
                (destination / name).mkdir(parents=True)
            reference = destination / 'reference.json'
            reference.write_text(json.dumps({'passed': True, 'cases': [{}] * 17}))
            checkpoint = {'completed_groups': COMPLETED_GROUPS, 'remaining_groups': REMAINING_GROUPS,
                          'reference_requests': 17, 'target_requests_completed': 204, 'new_target_budget': 68,
                          'reference_sha256': resource_guard.sha(reference)}
            self.assertEqual(len(validate_checkpoint(root, checkpoint)), 17)
            (destination / 'RESUME_STARTED.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'already started'):
                validate_checkpoint(root, checkpoint)
            reference.write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'reference changed'):
                validate_checkpoint(root, checkpoint)

    def test_global_blocks_and_fixed_budget(self):
        config = schedule()
        self.assertEqual(len(config['rows']), 60)
        self.assertEqual(config['formal_requests'], 6000)
        for block in range(6):
            self.assertEqual(len([row for row in config['rows'] if row['block'] == block]), 10)
        self.assertFalse(config['approved_for_gpu'])

    def test_correctness_cases_are_seventeen_with_two_eight_image_lengths(self):
        result = cases({'images': [{'file': str(i)} for i in range(20)], 'prompt': 'Describe.'})
        self.assertEqual(len(result), 17)
        self.assertEqual(sum(bool(row.get('parallel')) for row in result), 8)
        self.assertEqual([row['tokens'] for row in result if len(row['images']) == 8], [32, 128])

    def test_code_guard_rejects_changed_code_and_escape(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            root = Path(folder)
            (root / 'configs').mkdir()
            (root / 'evidence').mkdir()
            (root / 'file.py').write_text('pass')
            rows = [{'path': 'file.py', 'sha256': hashlib.sha256(b'pass').hexdigest()}]
            manifest = root / 'configs/code-manifest.json'
            manifest.write_text(json.dumps(rows))
            approval = root / 'evidence/G2_CODE_APPROVED.json'
            approval.write_text(json.dumps({'passed': True, 'allowed_actions': ['numeric'], 'code_manifest_sha256': resource_guard.sha(manifest)}))
            with patch.object(resource_guard, 'ROOT', root):
                self.assertEqual(resource_guard.code_identity(), resource_guard.sha(manifest))
                with self.assertRaises(RuntimeError):
                    resource_guard.code_identity('performance')
                (root / 'file.py').write_text('changed')
                with self.assertRaises(RuntimeError):
                    resource_guard.code_identity()
                rows[0]['path'] = '../outside.py'
                manifest.write_text(json.dumps(rows))
                approval.write_text(json.dumps({'passed': True, 'code_manifest_sha256': resource_guard.sha(manifest)}))
                with self.assertRaises(RuntimeError):
                    resource_guard.code_identity()

    def test_idle_refuses_an_unowned_gpu_process(self):
        rows = '\n'.join(uuid + ', 0, 0' for uuid in resource_guard.UUIDS)
        with patch.object(resource_guard.subprocess, 'check_output', side_effect=[rows, '1234\n']):
            with self.assertRaises(RuntimeError):
                resource_guard.idle()

    def test_cleanup_does_not_signal_same_user_other_run(self):
        identity = str(owned_processes.ROOT) + ':this-run'
        stopped = []
        class Process:
            def __init__(self, pid, run):
                self.pid, self.run, self.dead = pid, run, False
            def uids(self): return SimpleNamespace(real=1000)
            def status(self): return 'zombie' if self.dead else 'running'
            def environ(self): return {'EXP_ROOT': str(owned_processes.ROOT), 'REPRO_RUN_ID': self.run}
            def create_time(self): return float(self.pid)
            def parents(self): return []
            def name(self): return 'python3'
            def cmdline(self): return [str(owned_processes.ROOT / 'scripts/start_server.sh')]
            def terminate(self): self.dead = True; stopped.append(self.pid)
            def kill(self): self.terminate()
        me, ours, foreign = Process(999, ''), Process(1, identity), Process(2, str(owned_processes.ROOT) + ':other-run')
        fake = SimpleNamespace(Process=lambda pid=None: me if pid is None else {1: ours, 2: foreign}[pid],
                               process_iter=lambda: [ours, foreign], STATUS_ZOMBIE='zombie',
                               NoSuchProcess=LookupError, AccessDenied=PermissionError)
        with patch.object(owned_processes, 'psutil', fake), patch.object(os, 'getuid', return_value=1000, create=True):
            owned_processes.stop(identity)
        self.assertEqual(stopped, [1])
        self.assertFalse(foreign.dead)

    def test_sigterm_unwinds_through_cleanup(self):
        cleaned = []
        with self.assertRaises(resource_guard.RunInterrupted):
            with resource_guard.run_signals():
                try:
                    signal.raise_signal(signal.SIGTERM)
                finally:
                    cleaned.append(True)
        self.assertEqual(cleaned, [True])

    def test_access_denied_candidate_does_not_count_as_clean(self):
        denied = SimpleNamespace(pid=1234, name=lambda: 'python3', cmdline=lambda: [str(owned_processes.ROOT)])
        def fail():
            raise PermissionError('identity denied')
        denied.uids = fail
        fake = SimpleNamespace(process_iter=lambda: [denied], NoSuchProcess=LookupError, AccessDenied=PermissionError)
        with patch.object(owned_processes, 'psutil', fake):
            with self.assertRaises(RuntimeError):
                owned_processes.owned(str(owned_processes.ROOT) + ':ours')
        with patch.dict(sys.modules, {'psutil': fake}):
            self.assertEqual(resource_guard.remaining_owned(), ['1234:identity-unconfirmed'])


if __name__ == '__main__':
    unittest.main()
