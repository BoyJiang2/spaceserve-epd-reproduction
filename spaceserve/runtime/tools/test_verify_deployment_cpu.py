"""Synthetic result validation only; no target imports, SSH or GPU use."""
import types
import unittest
import ast
import inspect
import tempfile
from pathlib import Path

from verify_deployment_cpu import require_success,main


class ReceiptTests(unittest.TestCase):
    def test_real_scanner_accepts_python_UTF8_BOM(self):
        tree=ast.parse(inspect.getsource(main))
        call=next(node for node in ast.walk(tree) if isinstance(node,ast.Call)
                  and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name)
                  and node.func.value.id=='ast' and node.func.attr=='parse')
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path=Path(directory)/'test_bom.py'
            path.write_bytes(b'\xef\xbb\xbfclass BomTest:\n    def test_example(self): pass\n')
            parsed=eval(compile(ast.Expression(call),'<production-test-scanner>','eval'),{'ast':ast,'path':path})
            self.assertEqual(parsed.body[0].name,'BomTest')

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
