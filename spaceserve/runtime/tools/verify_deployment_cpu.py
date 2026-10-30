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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from runtime_config import context
CONFIG = context()
ROOT = CONFIG.run_root
SOURCE_SHA = CONFIG.config.get('source_manifest_sha256')
INPUT_SHA = CONFIG.config.get('asset_manifest_sha256')


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
    if not __debug__ or socket.gethostname() != CONFIG.config['host'] or os.getuid() != 2147:
        raise RuntimeError('CPU verification host/UID/debug differs')
    if ROOT.is_symlink() or Path(sys.prefix).resolve() != CONFIG.asset('envs/space').resolve():
        raise RuntimeError('use the verified shared project Python environment')
    manifest = ROOT/'configs/runtime-extension-source-manifest.json'
    if sha(manifest) != SOURCE_SHA or sha(ROOT/'configs/asset-inputs.json') != INPUT_SHA:
        raise RuntimeError('source or staged input pins differ')
    rows = json.loads(manifest.read_text())
    required = json.loads((ROOT/'configs/source-files.json').read_text())
    if [row['path'] for row in rows] != [row['path'] for row in required] or len({row['path'] for row in rows}) != len(rows):
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
    for directory in ('scripts','tools'):
        for path in sorted((ROOT/directory).glob('test_*.py')):
            for node in ast.parse(path.read_bytes()).body:
                if isinstance(node, ast.ClassDef):
                    expected.extend(path.stem+'.'+node.name+'.'+method.name for method in node.body
                        if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith('test_'))
    if not expected or len(expected) != len(set(expected)):
        raise RuntimeError('empty/duplicate reviewed test membership')
    sys.path.insert(0, str(ROOT/'scripts'))
    sys.path.insert(0, str(ROOT/'tools'))
    suite = unittest.TestSuite(unittest.TestLoader().discover(str(ROOT/directory),pattern='test_*.py')
                               for directory in ('scripts','tools'))
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
