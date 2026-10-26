import asyncio
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


def load(enabled):
    with patch.dict(os.environ, {'REPRO_OBSERVE': '1' if enabled else '0'}):
        spec = importlib.util.spec_from_file_location('tested_observe', Path(__file__).with_name('observe.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class Event:
    def __init__(self, **kwargs):
        self.recorded = False
    def record(self, stream):
        self.recorded = True
    def synchronize(self):
        raise AssertionError('synchronization must not occur inside calls')
    def elapsed_time(self, other):
        return 1.0


class ObserveTests(unittest.TestCase):
    def test_off_returns_original_and_does_not_import_cuda(self):
        module = load(False)
        def original(value):
            return value
        self.assertIs(module.call('step_llm')(original), original)
        module.mark('unused')
        self.assertEqual(module.records, [])

    def test_worker_op_and_step_identity_no_synchronization(self):
        module = load(True)
        cuda = SimpleNamespace(Event=Event, current_stream=lambda: SimpleNamespace(cuda_stream=123), current_device=lambda: 0)
        with patch.dict(sys.modules, {'torch': SimpleNamespace(cuda=cuda)}):
            def original(worker, request_ids):
                return [9] * len(request_ids)
            wrapped = module.call('step_llm')(original)
            worker = SimpleNamespace(stage='D')
            for index in range(2):
                meta = {'op_id': 'engine:' + str(index), 'request_ids': ['a', 'b']}
                self.assertEqual(wrapped(worker, ['a', 'b'], repro_meta=meta), [9, 9])
        self.assertEqual(len(module.gpu_windows), 2)
        self.assertEqual(module.gpu_windows[-1][3]['request_step_ordinals'], [2, 2])
        self.assertEqual(module.gpu_windows[0][3]['op_id'], 'engine:0')
        self.assertEqual([row['op_id'] for row in module.records], ['engine:0', 'engine:0', 'engine:1', 'engine:1'])

    def test_async_migration_context_does_not_cross_requests(self):
        module = load(True)
        async def migrate(engine, request):
            await asyncio.sleep(0)
            return module.worker_metadata('migrate_blocks_encoding', ([1],))['request_ids']
        wrapped = module.call('_migrate_blocks_encoding')(migrate)
        async def run():
            return await asyncio.gather(*(wrapped(None, SimpleNamespace(req=SimpleNamespace(request_id=rid))) for rid in (7, 8)))
        self.assertEqual(asyncio.run(run()), [['7'], ['8']])
        self.assertEqual(module.request_context.get(), ())

    def test_overflow_is_explicit_and_reset_clears(self):
        module = load(True)
        module.LIMIT = 2
        for _ in range(3):
            module.mark('bounded')
        self.assertTrue(module.overflow)
        self.assertEqual(len(module.records), 2)
        module.reset()
        self.assertFalse(module.overflow)
        self.assertEqual(module.records, [])

    def test_baseline_metadata_preserves_mixed_prefill_members(self):
        module = load(True)
        request = SimpleNamespace(seq_group_metadata_list=[SimpleNamespace(request_id='a', is_prompt=True), SimpleNamespace(request_id='b', is_prompt=False)])
        fields = module.details((None, request), 'baseline.execute_model', {})
        self.assertEqual(fields, {'request_ids': ['a', 'b'], 'prompt': [True, False]})


if __name__ == '__main__':
    unittest.main()
