import asyncio
import json
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import patch

try:
    import benchmark
except ModuleNotFoundError as error:
    raise unittest.SkipTest('requires copied target benchmark CPU dependencies') from error


class ProfileWindowTests(unittest.TestCase):
    def test_only_sixteen_diagnostic_requests_are_profiled_after_twenty_warmups(self):
        events=[]
        class Response:
            status=200
            def __init__(self,url): self.url=url
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
            async def text(self):
                if self.url.endswith('/generate'):
                    return json.dumps({'output_token_ids':[1]*128,'timestamps':[time.perf_counter()]*128,
                                       'processed_prompt_token_ids':[99]*1024})
                return '{}'
        class Session:
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
            def post(self,url,**kwargs):
                events.append(url.rsplit('/',1)[-1])
                return Response(url)
        tokenizer=types.SimpleNamespace(apply_chat_template=lambda *a,**k:'fixed CPU prompt',
                                        convert_tokens_to_ids=lambda name:99)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory)
            dataset=root/'dataset'
            dataset.mkdir()
            (dataset/'manifest.json').write_text(json.dumps({'images':[{'file':f'image{i}.jpg'} for i in range(20)],'prompt':'describe'}))
            args=types.SimpleNamespace(output=root/'measurement',dataset=dataset,model='Qwen2-VL-7B-Instruct',
                images=4,urls=['http://cpu-fixture'],tokens=128,concurrency=8,timeout=10,
                warmup=20,requests=16,repetitions=1,profile_after_warmup=True)
            with patch.object(benchmark.AutoTokenizer,'from_pretrained',return_value=tokenizer), \
                 patch.object(benchmark.aiohttp,'ClientSession',return_value=Session()):
                asyncio.run(benchmark.run(args))
            self.assertEqual(events,['generate']*20+['start']+['generate']*16+['stop'])
            rows=[json.loads(line) for line in (root/'measurement/requests.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows),36)
            self.assertEqual(sum(row['warmup'] for row in rows),20)


if __name__=='__main__':
    unittest.main()
