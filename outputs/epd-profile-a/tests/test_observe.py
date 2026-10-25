"""CPU-only tests: disabled identity, NVTX balancing, and patch preconditions."""
import asyncio
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


def load(enabled):
    events = []
    nvtx = types.SimpleNamespace(range_start=lambda label: events.append(('start', label)) or len(events),
                                 range_end=lambda token: events.append(('end', token)),
                                 mark=lambda label: events.append(('mark', label)))
    spec = importlib.util.spec_from_file_location('observe_under_test', SCRIPTS / 'observe.py')
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, REPRO_OBSERVE='1' if enabled else '0'), patch.dict(sys.modules, {'torch': types.ModuleType('torch'), 'torch.cuda': types.SimpleNamespace(nvtx=nvtx)}):
        spec.loader.exec_module(module)
    return module, events


class ObserveTests(unittest.TestCase):
    def test_disabled_preserves_identity(self):
        module, events = load(False)
        def method(self):
            return 42
        self.assertIs(module.call('method')(method), method)
        with module.span('unused'):
            module.mark('unused')
        self.assertEqual(events, [])

    def test_exception_closes_sync_range(self):
        module, events = load(True)
        @module.call('broken')
        def method(self):
            raise ValueError('expected')
        with self.assertRaises(ValueError):
            method(object())
        self.assertEqual([item[0] for item in events], ['start', 'end'])

    def test_async_returns_and_closes(self):
        module, events = load(True)
        @module.call('async')
        async def method(self, ids):
            return ids
        self.assertEqual(asyncio.run(method(object(), ['request-a'])), ['request-a'])
        self.assertEqual([item[0] for item in events], ['start', 'end'])
        self.assertIn('request-a', events[0][1])

    def test_migration_ids_are_not_request_ids(self):
        module, _ = load(True)
        self.assertEqual(module.details((object(), [1, 2]), 'migrate_blocks_context'), {'blocks': ['1', '2'], 'batch': 2})

    def test_baseline_keyword_metadata(self):
        module, events = load(True)
        request = types.SimpleNamespace(seq_group_metadata_list=[types.SimpleNamespace(request_id='r7', is_prompt=True)])
        self.assertEqual(module.details((object(),), 'baseline.execute_model', {'execute_model_req': request}), {'ids': ['r7'], 'prompt': [True], 'batch': 1})
        @module.call('baseline.execute_model')
        def execute(self, execute_model_req=None):
            return execute_model_req
        self.assertIs(execute(object(), execute_model_req=request), request)
        self.assertIn('"ids":["r7"],"prompt":[true],"batch":1', events[0][1])

    def test_patch_all_validated_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'epd-profile-a-20261023'
            source = root / 'src/epdserve/epdserve'
            source.mkdir(parents=True)
            worker = source / 'worker.py'
            original = '\n'.join(f'def {name}(self): pass' for name in ['step_llm', 'step_encoding', 'migrate_blocks_context', 'migrate_blocks_encoding'])
            worker.write_text(original)
            result = subprocess.run([sys.executable, str(SCRIPTS / 'instrument.py'), str(root)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(worker.read_text(), original)
            self.assertFalse((root / 'instrumentation.patch').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
