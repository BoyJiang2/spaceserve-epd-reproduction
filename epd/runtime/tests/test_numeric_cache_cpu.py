"""Unexecuted CPU-MOCK contracts only; no CUDA/Ray/model imports or real probe evidence."""
import copy
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numeric_cache as native


class TensorFixture:
    dtype = 'torch.float16'
    device = NS(type='cuda')

    def __init__(self, shape):
        self.shape = shape

    def stride(self):
        return tuple(math.prod(self.shape[index + 1:]) for index in range(len(self.shape)))

    def is_contiguous(self): return True
    def storage_offset(self): return 0
    def untyped_storage(self): return NS(nbytes=lambda: math.prod(self.shape) * 2)


class NativeCacheContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ['EPD_CPU_TEST_TMP'])
        self.addCleanup(self.temp.cleanup)
        model = Path(self.temp.name)/'MiniCPM-V-2_6'; model.mkdir()
        (model/'config.json').write_text('{"CPU-MOCK":true}')
        self.worker = NS(stage=NS(name='DECODING'), model=None, device='CPU-MOCK-cuda-device',
            model_config=NS(model=str(model), dtype='fp16', pd_fused=False, use_dummy_weights=False),
            cache_config=NS(block_size=16, cpu_swap_space=0, gpu_memory_utilization=.65),
            parallel_config=NS(to_list=lambda: list(native.PARALLEL)),
            kv_cache=TensorFixture((1, 2, 2, 2, 1, 1)), ve_cache=TensorFixture((3000, 64, 3584)),
            qualification_identity=Mock(return_value={'gpu_uuid':'CPU-MOCK-A'}),
            _profile_num_available_blocks=Mock(return_value=(2, 0)),
            _profile_num_available_blocks_encoding=Mock(return_value=(3000, 0)),
            _get_block_size_in_bytes=Mock(return_value=8),
            _get_block_size_in_bytes_encoding=Mock(return_value=64*3584*2),
            get_perimage_embedding_size=Mock(return_value=(64,3584)),
            init_kvcache_and_swap=Mock(return_value=[0]*64),
            init_vecache_and_swap=Mock(return_value=[1]*64))
        self.torch = NS(cuda=NS(get_device_properties=Mock(return_value=NS(total_memory=8<<30)),
            memory_reserved=Mock(return_value=0)))
        self.environment = patch.dict(os.environ, REPRO_NUMERIC_ONLY='1',
            REPRO_GPU_UUIDS=json.dumps(['CPU-MOCK-A','CPU-MOCK-B','CPU-MOCK-C']))
        self.environment.start(); self.addCleanup(self.environment.stop)

    def test_finite_vector_has_36_unique_ordered_directed_copies_and_seeds(self):
        vector = native.transfer_vector(['CPU-MOCK-A','CPU-MOCK-B','CPU-MOCK-C'])
        self.assertEqual(len(vector), 36)
        self.assertEqual([row['ordinal'] for row in vector], list(range(36)))
        self.assertEqual({row['seed'] for row in vector}, set(range(1,37)))
        self.assertEqual(len({(r['source_uuid'],r['target_uuid'],r['kind'],r['repetition']) for r in vector}), 36)
        self.assertTrue(all(r['source_uuid'] != r['target_uuid'] for r in vector))

    def test_context_and_encoding_refused_before_any_allocator_or_identity(self):
        for stage in ('CONTEXT','ENCODING'):
            self.worker.stage.name = stage
            with self.assertRaises(ValueError): native.allocate(self.worker, 'kv', self.torch)
        self.worker.qualification_identity.assert_not_called()
        self.worker.init_kvcache_and_swap.assert_not_called()
        self.worker.init_vecache_and_swap.assert_not_called()

    def test_model_or_non_six_component_parallel_refused(self):
        self.worker.model_runner = object()
        with self.assertRaises(ValueError): native.allocate(self.worker, 'kv', self.torch)
        del self.worker.model_runner
        self.worker.parallel_config.to_list = lambda: [1,0,1,0]
        with self.assertRaises(ValueError): native.allocate(self.worker, 'kv', self.torch)
        self.worker.init_kvcache_and_swap.assert_not_called()

    def test_kv_uses_only_official_kv_allocator_and_zero_cpu_blocks(self):
        result = native.probe(self.worker, 'allocate', 'kv', self.torch)
        self.worker._profile_num_available_blocks.assert_called_once_with(16,.65,0)
        self.worker.init_kvcache_and_swap.assert_called_once_with(2,0)
        self.worker.init_vecache_and_swap.assert_not_called()
        self.assertEqual(result['geometry']['shape'], [1,2,2,2,1,1])
        self.assertFalse(result['model_loaded'])

    def test_ve_uses_full_official_geometry_and_no_kv_allocator(self):
        result = native.probe(self.worker, 'allocate', 've', self.torch)
        self.worker.init_vecache_and_swap.assert_called_once_with(3000,0)
        self.worker.init_kvcache_and_swap.assert_not_called()
        self.assertEqual(result['geometry']['shape'], [3000,64,3584])

    def test_missing_identity_and_insufficient_memory_refuse_before_allocator(self):
        self.worker.qualification_identity.return_value = None
        with self.assertRaises(ValueError): native.allocate(self.worker, 've', self.torch)
        self.worker.qualification_identity.return_value = {'gpu_uuid':'CPU-MOCK-A'}
        self.torch.cuda.get_device_properties.return_value.total_memory = 1024
        with self.assertRaises(ValueError): native.allocate(self.worker, 've', self.torch)
        self.worker.init_vecache_and_swap.assert_not_called()

    def test_changed_native_ve_capacity_is_not_replaced_by_smaller_payload(self):
        self.worker._profile_num_available_blocks_encoding.return_value = (2999,0)
        with self.assertRaises(ValueError): native.allocate(self.worker, 've', self.torch)
        self.worker.init_vecache_and_swap.assert_not_called()

    def test_second_allocation_or_copy_after_failure_refused(self):
        native.probe(self.worker, 'allocate', 'kv', self.torch)
        transfer = native.transfer_vector(['CPU-MOCK-A','CPU-MOCK-B','CPU-MOCK-C'])[0]
        with patch.object(native, 'fill_and_check', side_effect=RuntimeError('CPU-MOCK corrupt source')) as check:
            with self.assertRaises(RuntimeError): native.probe(self.worker, 'prepare', transfer, self.torch)
            with self.assertRaises(ValueError): native.probe(self.worker, 'prepare', transfer, self.torch)
            self.assertEqual(check.call_count, 1)
        with self.assertRaises(ValueError): native.probe(self.worker, 'allocate', 'kv', self.torch)
        self.assertEqual(self.worker.init_kvcache_and_swap.call_count, 1)

    def test_shape_stride_and_cache_block_differences_refuse_without_truncation(self):
        original = native.geometry(self.worker.kv_cache, 'kv')
        for key in ('shape','stride','blocks','dtype'):
            changed = copy.deepcopy(original)
            changed[key] = 'CPU-MOCK-wrong'
            with self.assertRaises(ValueError): native.match_geometry(changed, original)

    def test_tail_chunk_covers_every_element_and_fourth_copy_refuses(self):
        n = native.CHUNK_ELEMENTS * 2 + 7
        ranges = native.chunk_ranges(n)
        self.assertEqual(ranges, [(0,native.CHUNK_ELEMENTS),(native.CHUNK_ELEMENTS,2*native.CHUNK_ELEMENTS),(2*native.CHUNK_ELEMENTS,n)])
        self.assertEqual(sum(end-start for start,end in ranges), n)
        native.probe(self.worker, 'allocate', 'kv', self.torch)
        self.worker._numeric_probe_state['copied'] = 3
        transfer = native.transfer_vector(['CPU-MOCK-A','CPU-MOCK-B','CPU-MOCK-C'])[0]
        with self.assertRaises(ValueError): native.validate_transfer(self.worker, transfer, True)


if __name__ == '__main__': unittest.main()
