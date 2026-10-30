"""Resume-planning tests: stdlib only, no GPU, no Ray, no psutil."""
import json
import tempfile
import unittest
from pathlib import Path
import os
import shutil
import uuid
_TMPROOT = Path(__file__).resolve().parent / '_test_tmp'


class _Temp:
    """Workspace-local temp dir: the host temp area is not deletable under the sandbox."""

    def __enter__(self):
        _TMPROOT.mkdir(exist_ok=True)
        self._path = str(_TMPROOT / ('t-' + uuid.uuid4().hex[:8]))
        os.makedirs(self._path)
        return self._path

    def __exit__(self, *exc):
        shutil.rmtree(self._path, ignore_errors=True)
        return False


import resume_plan


def cell(index, block=0, images=1, concurrency=1, role='space', requests=100):
    return dict(index=index, block=block, images=images, concurrency=concurrency,
                role=role, requests=requests, warmup=20)


def write_marker(root, row, **overrides):
    path = Path(root) / resume_plan.cell_dirname(row)
    path.mkdir(parents=True)
    state = dict(formal_code_manifest_sha256='a' * 64, schedule_index=row['index'],
                 formal_requests=row['requests'], warmup_requests=20)
    state.update(overrides)
    (path / 'COMPLETED.json').write_text(json.dumps(state))


class ResumePlanTests(unittest.TestCase):
    def test_empty_output_is_all_pending(self):
        with _Temp() as root:
            done, pending, blocked = resume_plan.classify(root, [cell(0), cell(1)], 'a' * 64)
            self.assertEqual(done, [])
            self.assertEqual([row['index'] for row in pending], [0, 1])
            self.assertEqual(blocked, [])

    def test_completed_cell_is_skipped_only_with_matching_manifest(self):
        with _Temp() as root:
            rows = [cell(0), cell(1)]
            write_marker(root, rows[0])
            done, pending, blocked = resume_plan.classify(root, rows, 'a' * 64)
            self.assertEqual([row['index'] for row in done], [0])
            self.assertEqual([row['index'] for row in pending], [1])
            self.assertEqual(blocked, [])

    def test_foreign_manifest_is_blocked_not_skipped(self):
        with _Temp() as root:
            rows = [cell(0)]
            write_marker(root, rows[0], formal_code_manifest_sha256='b' * 64)
            done, pending, blocked = resume_plan.classify(root, rows, 'a' * 64)
            self.assertEqual(done, [])
            self.assertEqual(pending, [])
            self.assertEqual(len(blocked), 1)
            self.assertIn('manifest', blocked[0]['reason'])

    def test_partial_cell_directory_is_blocked(self):
        with _Temp() as root:
            rows = [cell(0)]
            (Path(root) / resume_plan.cell_dirname(rows[0])).mkdir(parents=True)
            done, pending, blocked = resume_plan.classify(root, rows, 'a' * 64)
            self.assertEqual(pending, [])
            self.assertEqual(len(blocked), 1)
            self.assertIn('without COMPLETED.json', blocked[0]['reason'])

    def test_corrupt_marker_is_blocked(self):
        with _Temp() as root:
            rows = [cell(0)]
            path = Path(root) / resume_plan.cell_dirname(rows[0])
            path.mkdir(parents=True)
            (path / 'COMPLETED.json').write_text('{not json')
            done, pending, blocked = resume_plan.classify(root, rows, 'a' * 64)
            self.assertEqual(len(blocked), 1)
            self.assertIn('unreadable', blocked[0]['reason'])

    def test_schedule_index_mismatch_is_blocked(self):
        with _Temp() as root:
            rows = [cell(0)]
            write_marker(root, rows[0], schedule_index=7)
            done, pending, blocked = resume_plan.classify(root, rows, 'a' * 64)
            self.assertEqual(len(blocked), 1)
            self.assertIn('schedule_index', blocked[0]['reason'])

    def test_dry_run_mode_skips_manifest_comparison(self):
        with _Temp() as root:
            rows = [cell(0), cell(1)]
            write_marker(root, rows[0], formal_code_manifest_sha256='unrelated')
            done, pending, blocked = resume_plan.classify(root, rows, None, verify_code=False)
            self.assertEqual([row['index'] for row in done], [0])
            self.assertEqual([row['index'] for row in pending], [1])
            self.assertEqual(blocked, [])

    def test_summary_reports_complete_only_when_nothing_pending_or_blocked(self):
        rows = [cell(0), cell(1)]
        self.assertFalse(resume_plan.summary(rows[:1], rows[1:], [])['complete'])
        self.assertTrue(resume_plan.summary(rows, [], [])['complete'])
        self.assertFalse(resume_plan.summary(rows, [], [{'index': 9}])['complete'])

    def test_dirname_is_stable(self):
        self.assertEqual(resume_plan.cell_dirname(cell(7, block=2, images=4, concurrency=8, role='space-mask')),
                         '007-b2-i4-c8-space-mask')


if __name__ == '__main__':
    unittest.main()
