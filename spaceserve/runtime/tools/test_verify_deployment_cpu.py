"""Synthetic result validation only; no target imports, SSH or GPU use."""
import types
import unittest

from verify_deployment_cpu import require_success


class ReceiptTests(unittest.TestCase):
    def test_exact_success_and_failure_modes(self):
        good = types.SimpleNamespace(testsRun=2, skipped=[], wasSuccessful=lambda: True)
        require_success(good, ['A', 'B'], ['B', 'A'])
        for result, actual in [
            (good, ['A', 'A']), (good, ['A']), (good, ['A', 'OTHER']),
            (types.SimpleNamespace(testsRun=1, skipped=[], wasSuccessful=lambda: True), ['A', 'B']),
            (types.SimpleNamespace(testsRun=2, skipped=[('B', 'skip')], wasSuccessful=lambda: True), ['A', 'B']),
            (types.SimpleNamespace(testsRun=2, skipped=[], wasSuccessful=lambda: False), ['A', 'B'])]:
            with self.assertRaises(RuntimeError):
                require_success(result, ['A', 'B'], actual)


if __name__ == '__main__':
    unittest.main()
