import copy
import hashlib
import json
from pathlib import Path
import unittest

from analyze_cells import HOST_ROOT, audit_cell, validate_schedule


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(block=0, load='low', images=1, tokens=128, concurrency=1,
                        system='epd', mode='off', warmup=20, formal=100)
        self.folder = Path('cell')
        self.dataset = {'images': [{'file': f'{i}.jpg'} for i in range(20)]}
        self.reference = {'coco-1': {'response': {'processed_prompt_token_ids': [1, 2, 3]}}}
        rows = []
        for warm, count in [(True, 20), (False, 100)]:
            for index in range(count):
                start = 10 + index * 2 if not warm else -100 + index * 2
                stamps = [start + .1 + i * .01 for i in range(128)]
                rows.append(dict(warmup=warm, repetition=-1 if warm else 0, index=index,
                                 images=[HOST_ROOT + f'/dataset/{index % 20}.jpg'],
                                 endpoint='http://127.0.0.1:19810', success=True, visual_tokens=64,
                                 submission_perf_counter=start, latency_s=1.5, ttft_s=.1, tpot_s=.01,
                                 output_tokens=128, response={'timestamps': stamps,
                                 'output_token_ids': [7] * 128, 'processed_prompt_token_ids': [1, 2, 3]}))
        summary = dict(repetition=0, requests=100, successes=100, failure_rate=0,
                       start_perf_counter=10, end_perf_counter=210, duration_s=200,
                       requests_per_s=.5, output_tokens_per_s=64)
        summary.update({key: {'p50': value, 'p95': value} for key, value in [('latency_s', 1.5), ('ttft_s', .1), ('tpot_s', .01)]})
        self.files = {
            'COMPLETED': self.row,
            'measurement/config.json': dict(images=1, tokens=128, concurrency=1, warmup=20,
                 requests=100, repetitions=1, lite=False, model=HOST_ROOT+'/models/MiniCPM-V-2_6',
                 dataset=HOST_ROOT+'/dataset', urls=['http://127.0.0.1:19810'],prompt='synthetic-prompt'),
            'measurement/requests.jsonl': rows, 'measurement/summary.json': [summary],
            'gpu-memory.jsonl': [{'perf_counter': t, 'gpus': [dict(device=4+i, foreign_compute_pids=[],
                  owned_process_sum_bytes=100, owned_processes=[{'pid': 15+i, 'used_bytes': 100}]) for i in range(3)]} for t in range(10, 211)],
            'runtime.json': {'boot_id': 'same-test-boot', 'python_prefix': HOST_ROOT+'/envs/epd',
                  'captured_utc': '2026-10-26T13:00:00+00:00',
                  'loaded_cublas_sha256': {HOST_ROOT+'/envs/epd/libcublas.so': 'a'*64},
                  'workers': [{'pid':15+i,'gpu_uuid':uuid} for i,uuid in enumerate(__import__('analyze_cells').UUIDS)]},
            'model-runtime-0.json': {'pid':14, 'operation':'runtime', 'results':[
                  {'pid':15+i,'parameters_by_device':{'cuda:0':10},'parameters_by_dtype':{'torch.float16':10},'parameters_by_component':{'llm':10}} for i in range(3)]}
        }
        cache = {'passed':True,'inference_requests':0,'records':[
             {'url':'http://127.0.0.1:19810','pid':14,'manifest_sha256':'b'*64,
              'images':[{'file':f'{i}.jpg','rgb_sha256':'c'*64,'mode':'RGB','size':[448,448]} for i in range(20)]}]}
        self.files['rgb-before.json'] = copy.deepcopy(cache)
        self.files['rgb-after.json'] = copy.deepcopy(cache)
        uuids = dict(zip(__import__('analyze_cells').DEVICES, __import__('analyze_cells').UUIDS))
        for when, timestamp in [('before', 1), ('after', 211)]:
            self.files[f'host-{when}.json'] = {
                'host_ns': timestamp * 10**9, 'utc_ns': 1793000000000000000,
                'finished_utc_ns': 1793000000010000000, 'load_average': [1, 2, 3],
                'meminfo': 'MemAvailable: 123 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n',
                'compute_processes': '',
                'gpus': '\n'.join(f'{i}, {uuids.get(i, "GPU-other-"+str(i))}, 0, 0' for i in range(8))}

    def audit(self, protocol=None):
        return audit_cell(self.folder, self.row, self.dataset, self.reference,
                          lambda p, lines=False: self.files[p.relative_to(self.folder).as_posix()],protocol)

    def test_frozen_prompt_and_image_order_checked(self):
        images=[{k:v for k,v in image.items() if k!='mode'} for image in self.files['rgb-before.json']['records'][0]['images']]
        protocol={'images':images,'dataset_manifest_sha256':'b'*64,'loads':{'A':{
            'prompt':'synthetic-prompt','prompt_sha256':hashlib.sha256(b'synthetic-prompt').hexdigest(),
            'requests':[{'index':i,'warmup':warmup,'images':[images[i%20]]} for warmup,count in [(True,20),(False,100)] for i in range(count)]}}}
        self.audit(protocol)
        self.files['measurement/config.json']['prompt']='different'
        with self.assertRaisesRegex(ValueError,'prompt differs'):
            self.audit(protocol)
        self.files['measurement/config.json']['prompt']='synthetic-prompt'
        protocol['loads']['A']['requests'][0]['images']=[images[1]]
        with self.assertRaisesRegex(ValueError,'sequence differs'):
            self.audit(protocol)

    def test_recompute_metrics_and_sampled_three_gpu_memory(self):
        result = self.audit()
        self.assertEqual(result['sampled_peak_owned_bytes'], 300)
        self.assertEqual(len(result['pooled_source_rows']), 100)

    def test_shared_host_context_cannot_be_missing_or_overlap_measurement(self):
        snapshot = self.files.pop('host-before.json')
        with self.assertRaises(KeyError):
            self.audit()
        self.files['host-before.json'] = snapshot
        snapshot['host_ns'] = 20 * 10**9
        with self.assertRaisesRegex(ValueError, 'overlap formal'):
            self.audit()
        snapshot['host_ns'] = 10**9
        snapshot['gpus'] = '\n'.join(snapshot['gpus'].splitlines()[1:])
        with self.assertRaisesRegex(ValueError, 'incomplete shared-host GPU'):
            self.audit()

    def test_duplicate_request_cannot_replace_missing_request(self):
        self.files['measurement/requests.jsonl'][-1] = copy.deepcopy(self.files['measurement/requests.jsonl'][-2])
        with self.assertRaisesRegex(ValueError, 'missing/duplicate'):
            self.audit()

    def test_incorrect_input_routing_and_length_fail(self):
        for key, value in [('visual_tokens', 63), ('images', ['wrong.jpg']), ('success', False), ('endpoint', 'wrong')]:
            with self.subTest(key=key):
                original = self.files['measurement/requests.jsonl'][0][key]
                self.files['measurement/requests.jsonl'][0][key] = value
                with self.assertRaisesRegex(ValueError, 'request failed'):
                    self.audit()
                self.files['measurement/requests.jsonl'][0][key] = original

    def test_summary_tampering_foreign_gpu_and_missing_sample_fail(self):
        self.files['measurement/summary.json'][0]['requests_per_s'] = .6
        with self.assertRaisesRegex(ValueError, 'metric differs'):
            self.audit()
        self.files['measurement/summary.json'][0]['requests_per_s'] = .5
        self.files['gpu-memory.jsonl'][0]['gpus'][0]['foreign_compute_pids'] = [123]
        with self.assertRaisesRegex(ValueError, 'foreign process'):
            self.audit()
        self.files['gpu-memory.jsonl'] = []
        with self.assertRaisesRegex(ValueError, 'no GPU'):
            self.audit()

    def test_frozen_schedules_have_exact_unique_global_pairs(self):
        root = Path(__file__).resolve().parents[1]
        for name, phase in [('B', 'overhead'), ('C', 'performance')]:
            rows = json.loads((root / f'configs/{name}-schedule.json').read_text())['rows']
            validate_schedule(rows, phase)
            rows[-1] = rows[-2]
            with self.assertRaisesRegex(ValueError, 'missing/duplicate'):
                validate_schedule(rows, phase)

    def test_sampling_gaps_duplicate_gpu_and_missing_attribution_fail(self):
        original = copy.deepcopy(self.files['gpu-memory.jsonl'])
        for samples in ([original[0], original[-1]], [original[100]],
                        [{**original[0], 'gpus': original[0]['gpus']+[original[0]['gpus'][0]]}]):
            self.files['gpu-memory.jsonl'] = samples
            with self.assertRaises(ValueError):
                self.audit()
        self.files['gpu-memory.jsonl'] = original
        self.files['gpu-memory.jsonl'][1]['gpus'][0]['owned_process_sum_bytes'] = None
        with self.assertRaisesRegex(ValueError,'sum missing'):
            self.audit()

    def test_missing_runtime_or_changed_rgb_cannot_be_complete(self):
        runtime=self.files.pop('runtime.json')
        with self.assertRaises(KeyError):
            self.audit()
        self.files['runtime.json']=runtime
        self.files['rgb-after.json']['records'][0]['images'][0]['rgb_sha256']='d'*64
        with self.assertRaisesRegex(ValueError,'RGB cache changed'):
            self.audit()


if __name__ == '__main__':
    unittest.main()
