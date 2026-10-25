"""Run all 320 client submissions with a CPU-only fake HTTP transport."""
import asyncio
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/benchmark.py'


def run_case(observe, concurrency):
    bodies, events = [], []
    class Response:
        status = 200
        def __init__(self, result):
            self.result = result
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def json(self):
            await asyncio.sleep(0)
            return self.result
        async def text(self):
            await asyncio.sleep(0)
            return json.dumps(self.result)
    class Session:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        def post(self, url, json, **kwargs):
            if url.endswith('/repro/observe'):
                events.append((json['operation'], len(bodies), url))
                return Response({'enabled': True, 'capturing': json['operation'] == 'start'})
            bodies.append((url, json))
            return Response({'timestamps': [time.perf_counter()] * 128, 'output_token_ids': [1] * 128})
    tokenizer = types.SimpleNamespace(apply_chat_template=lambda *a, **kw: 'fixed prompt')
    dependencies = {'aiohttp': types.SimpleNamespace(ClientSession=Session, ClientTimeout=lambda **kw: None),
                    'transformers': types.SimpleNamespace(AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *a, **kw: tokenizer))}
    with tempfile.TemporaryDirectory() as directory, patch.dict('sys.modules', dependencies):
        spec = importlib.util.spec_from_file_location('bench_under_test', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        dataset = Path(directory)
        (dataset / 'manifest.json').write_text(json.dumps({'images': [{'file': f'{i}.jpg'} for i in range(20)], 'prompt': 'fixed'}))
        args = types.SimpleNamespace(output=dataset / 'result', dataset=dataset, model='MiniCPM', images=4,
                                     concurrency=concurrency, timeout=120, urls=['http://a', 'http://b', 'http://c'],
                                     warmup=20, repetitions=3, requests=100, tokens=128, observe=observe)
        with contextlib.redirect_stdout(io.StringIO()):
            asyncio.run(module.run(args))
        rows = [json.loads(line) for line in (args.output / 'requests.jsonl').read_text().splitlines()]
        summaries = json.loads((args.output / 'summary.json').read_text())
        assert len(rows) == 320 and sum(not row['warmup'] for row in rows) == 300
        assert all(row['success'] for row in rows)
        assert all(row['requests'] == row['successes'] == 100 for row in summaries)
    for _, body in bodies:
        images = body['input']['multi_modal_data']['images_paths']
        body['input']['multi_modal_data']['images_paths'] = [Path(name).name for name in images]
    return bodies, events


class BenchmarkControlTests(unittest.TestCase):
    def test_only_on_mode_controls_last_window(self):
        for concurrency in [1, 8]:
            with self.subTest(concurrency=concurrency):
                off, off_events = run_case(False, concurrency)
                on, on_events = run_case(True, concurrency)
                self.assertEqual(off, on)
                self.assertEqual(off_events, [])
                self.assertEqual([(op, count) for op, count, _ in on_events], [('start', 304)] * 3 + [('stop', 320)] * 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
