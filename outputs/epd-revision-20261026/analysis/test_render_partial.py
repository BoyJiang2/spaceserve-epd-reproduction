"""Partial comparisons must stop when global evidence conflicts."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from render_report import render


class PartialRenderTests(unittest.TestCase):
    def test_global_conflicts_suppress_all_pair_ratios(self):
        cells = [{'schedule_index': i, 'block': b, 'load': load, 'system': system,
                  'mode': 'off', 'status': 'valid',
                  'metrics': {'requests_per_s': 2 if system == 'epd' else 1,
                              'output_tokens_per_s': 256}}
                 for i, (b, load, system) in enumerate(
                     (b, load, system) for b in range(6) for load in 'ABCDE'
                     for system in ('baseline-epd', 'epd'))]
        for error in ('host boot differs across blocks', 'overlapping/out-of-order actual cells'):
            with self.subTest(error=error), tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
                root = Path(directory)
                result = {'complete': False, 'cells': cells, 'source_sha256': {},
                          'chronology_errors': [error]}
                with patch('render_report.analyze', return_value=result):
                    render(root, 'performance', root / 'report')
                text = (root / 'report/report.md').read_text(encoding='utf-8')
                self.assertIn('全局可比性检查失败', text)
                self.assertIn(error, text)
                self.assertNotIn('2.0000×', text)
                self.assertEqual(text.count('2.0000 / 256.00'), 30)


if __name__ == '__main__':
    unittest.main()
