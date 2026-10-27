"""Synthetic-only report checks. No downloaded GPU data is used."""
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

import render_report
from analyze_formal import comparisons
import test_analyze_formal as fixtures


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WholeMatrixTests('test_complete_matrix_all_planned_pairs_and_metrics')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_partial_has_every_plan_and_only_raw_observation_figure(self):
        last = self.fixture.schedule['cells'][-1]
        (self.fixture.root / 'results/formal' / self.fixture.name(last)).rmdir()
        result = self.fixture.analyze()
        result['synthetic'] = True
        output = self.fixture.root / 'partial-report'
        with patch.object(render_report, 'analyze', return_value=result):
            render_report.render(self.fixture.root, output)
            original = (output / 'report.md').read_bytes()
            with self.assertRaises(FileExistsError):
                render_report.render(self.fixture.root, output)
            self.assertEqual((output / 'report.md').read_bytes(), original)
        text = original.decode()
        self.assertIn('SYNTHETIC CPU TEST ONLY', text)
        self.assertIn('有效单元53/54', text)
        self.assertIn('不生成完整矩阵性能图', text)
        self.assertIn('53/2/', text)
        self.assertIn(hashlib.sha256((output / 'analysis.json').read_bytes()).hexdigest(), text)
        self.assertEqual({p.name for p in output.glob('*.png')}, {'raw-observations.png'})
        self.assertEqual({p.name for p in output.glob('*.svg')}, {'raw-observations.svg'})
        self.assertEqual(result['intervals'], [])
        self.assertIn('没有均值、拟合或置信区间', text)

    def test_global_conflict_disables_even_raw_figures(self):
        def out_of_order(case, row, root):
            result = self.fixture.described(case, row, root)
            if row['index'] == 1: result['start'] = 999
            return result
        result = self.fixture.analyze(out_of_order)
        result['synthetic'] = True
        output = self.fixture.root/'conflict-report'
        with patch.object(render_report,'analyze',return_value=result):
            render_report.render(self.fixture.root,output)
        self.assertTrue(result['global_errors'])
        self.assertFalse(list(output.glob('*.png')) + list(output.glob('*.svg')))

    def test_full_report_all_three_comparisons_and_actual_plot_exports(self):
        result = self.fixture.analyze()
        result['synthetic'] = True
        for cell in result['cells']:
            if (cell['role'], cell['images'], cell['concurrency']) == ('space-mask', 1, 1):
                cell['metrics']['requests_per_s'] = .8
                cell['metrics']['output_tokens_per_s'] = 102.4
        result['all_planned_pairs'], result['intervals'] = comparisons(result['cells'], True, [])
        output = self.fixture.root / 'full-report'
        with patch.object(render_report, 'analyze', return_value=result):
            render_report.render(self.fixture.root, output)
        text = (output / 'report.md').read_text(encoding='utf-8')
        self.assertIn('space-mask/space', text)
        self.assertIn('0.8000', text)  # A synthetic regression is retained in tables and plots.
        self.assertIn('df2', text)
        self.assertIn('MPS共享分配', text)
        for name in ('throughput-relative', 'latency'):
            self.assertTrue((output / (name + '.png')).read_bytes().startswith(b'\x89PNG'))
            self.assertIn('<svg', (output / (name + '.svg')).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
