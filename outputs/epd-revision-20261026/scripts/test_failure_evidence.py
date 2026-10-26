"""CPU fake-HTTP regressions for failed responses and invalid processed inputs."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import correctness_suite


class Tokenizer:
    im_start_id, im_end_id = 1, 2
    @classmethod
    def from_pretrained(cls, *args, **kwargs): return cls()
    def apply_chat_template(self, *args, **kwargs): return 'prompt'


class Response:
    failure = 'http'
    def __init__(self, body):
        paths = body['input']['multi_modal_data']['images_paths']
        color = next((color for color in ('red', 'green', 'blue', 'yellow') if color in paths[0]), 'red')
        bad = color == 'red'
        self.status = 400 if bad and self.failure == 'http' else 200
        self.data = {'output': color, 'output_token_ids': [7] * body['max_tokens'],
                     'timestamps': [time.perf_counter()] * body['max_tokens'], 'repro_request_id': str(id(self)),
                     'processed_prompt_token_ids': [1] + [0] * ((63 if bad and self.failure == 'visual' else 64) * len(paths)) + [2]}
        if self.failure == 'missing': self.data.pop('processed_prompt_token_ids')
        if bad and self.failure == 'clock-nan': self.data['timestamps'][1] = float('nan')
        if bad and self.failure == 'clock-reverse': self.data['timestamps'][1] -= .01
        if bad and self.failure == 'rid': self.data['repro_request_id'] = ''
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    async def json(self): return self.data
    async def text(self): return json.dumps(self.data)


class Session:
    def __init__(self, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    def post(self, url, json, **kwargs): return Response(json)


FAKES = {'aiohttp': SimpleNamespace(ClientSession=Session, ClientTimeout=lambda **kwargs: None),
         'transformers': SimpleNamespace(AutoTokenizer=Tokenizer)}


class FailureEvidenceTests(unittest.TestCase):
    def fixture(self, root):
        dataset = root / 'dataset'
        dataset.mkdir()
        (dataset / 'manifest.json').write_text(json.dumps({'images': [{'file': f'{i}.png'} for i in range(20)], 'prompt': 'describe'}))
        return dataset

    def test_correctness_http_and_visual_failure_preserve_successes_and_error_response(self):
        for failure in ('http', 'visual', 'clock-nan', 'clock-reverse', 'rid'):
            with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary, patch.dict(sys.modules, FAKES), patch.object(Response, 'failure', failure):
                root = Path(temporary)
                output = root / 'check.json'
                with self.assertRaises(RuntimeError):
                    asyncio.run(correctness_suite.run('http://fake', 'MiniCPM-V-2_6', self.fixture(root), output))
                rows = [json.loads(line) for line in output.with_suffix('.requests.jsonl').read_text().splitlines()]
                completed = [row for row in rows if row['event'] == 'completed']
                self.assertTrue(any(row['success'] for row in completed))
                self.assertTrue(any(not row['success'] and row['response'] is not None for row in completed))
                self.assertFalse(json.loads(output.read_text())['passed'])

    def test_benchmark_missing_or_wrong_visual_ids_is_recorded_failure(self):
        for failure in ('missing', 'visual'):
            with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary, patch.dict(sys.modules, FAKES), patch.object(Response, 'failure', failure):
                spec = importlib.util.spec_from_file_location('tested_benchmark', Path(__file__).with_name('benchmark.py'))
                benchmark = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(benchmark)
                root = Path(temporary)
                args = SimpleNamespace(output=root / 'output', dataset=self.fixture(root), model='MiniCPM-V-2_6', urls=['http://fake'],
                                       images=1, concurrency=1, tokens=32, warmup=1, requests=1, repetitions=1, timeout=120, lite=False)
                with self.assertRaises(RuntimeError):
                    asyncio.run(benchmark.run(args))
                rows = [json.loads(line) for line in (args.output / 'requests.jsonl').read_text().splitlines()]
                self.assertFalse(rows[0]['success'])
                self.assertIsInstance(rows[0]['response'], dict)
                self.assertFalse((args.output / 'summary.json').exists())


if __name__ == '__main__':
    unittest.main()
