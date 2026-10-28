"""Actual Linux CPU-suite receipt for the reviewed new root; never grants a Gate."""
import ast
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys
import unittest

ROOT = Path('/var/tmp/boyjiang-spaceserve-window-20261028-2300')
SOURCE_SHA = '4c38a17a53e28a1631a1e54e2513b05930925871ae049010d2b4d1ecd93686fb'
INPUT_SHA = '504760aae3c903cb090b766c7937640c2afdd8ea693a516da8c1a9733ff3357c'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_success(result, expected, actual):
    if (len(actual) != len(set(actual)) or set(actual) != set(expected)
            or result.testsRun != len(expected) or not result.wasSuccessful() or result.skipped):
        raise RuntimeError('CPU suite incomplete, failed, duplicated or skipped; preserve log')


def test_ids(suite):
    result = []
    for item in suite:
        result.extend(test_ids(item) if isinstance(item, unittest.TestSuite) else [item.id()])
    return result


def main():
    if not __debug__ or socket.gethostname() != 'qjh000' or os.getuid() != 2147:
        raise RuntimeError('CPU verification host/UID/debug differs')
    if ROOT.is_symlink() or Path(sys.prefix).resolve() != (ROOT/'envs/space').resolve():
        raise RuntimeError('use the new independent Python environment')
    manifest = ROOT/'configs/runtime-extension-source-manifest.json'
    if sha(manifest) != SOURCE_SHA or sha(ROOT/'configs/relocated-inputs.json') != INPUT_SHA:
        raise RuntimeError('source or staged input pins differ')
    rows = json.loads(manifest.read_text())
    if len(rows) != 56 or len({row['path'] for row in rows}) != 56:
        raise RuntimeError('reviewed source membership differs')
    for row in rows:
        path = ROOT/row['path']
        if (path.is_symlink() or not path.resolve(strict=True).is_relative_to(ROOT.resolve())
                or path.stat().st_size != row['bytes'] or sha(path) != row['sha256']):
            raise RuntimeError('deployed source differs: ' + row['path'])
    log_path, receipt_path = (ROOT/'evidence'/name for name in ('extension-target-CPU.log', 'extension-target-CPU.json'))
    if log_path.exists() or receipt_path.exists():
        raise RuntimeError('refuse CPU evidence overwrite')
    expected = []
    for path in sorted((ROOT/'scripts').glob('test_*.py')):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.ClassDef):
                expected.extend(path.stem+'.'+node.name+'.'+method.name for method in node.body
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith('test_'))
    if len(expected) != 31:
        raise RuntimeError('reviewed test membership differs')
    sys.path.insert(0, str(ROOT/'scripts'))
    suite = unittest.defaultTestLoader.discover(str(ROOT/'scripts'), pattern='test_*.py')
    actual = test_ids(suite)
    with log_path.open('x') as output:
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    require_success(result, expected, actual)
    for row in rows:
        if sha(ROOT/row['path']) != row['sha256']:
            raise RuntimeError('source changed during CPU suite')
    state = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'root': str(ROOT), 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
             'source_manifest_sha256': SOURCE_SHA, 'input_manifest_sha256': INPUT_SHA,
             'tests_passed': result.testsRun, 'tests_skipped': len(result.skipped), 'test_ids': actual,
             'log_sha256': sha(log_path), 'helper_sha256': sha(Path(__file__)),
             'packages': {name: importlib.metadata.version(name) for name in
                          ('torch', 'vllm', 'transformers', 'psutil', 'nvidia-cublas-cu12')},
             'new_model_requests': 0, 'grants_no_G2_or_G3': True}
    with receipt_path.open('x') as output:
        json.dump(state, output, indent=2)
    print(json.dumps({'tests_passed': result.testsRun, 'tests_skipped': 0, 'new_model_requests': 0}))


if __name__ == '__main__':
    main()
