import copy
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from correctness_suite import validate,recorded_request
import correctness_suite as suite
import time
import types
from unittest.mock import patch


class CorrectnessTests(unittest.TestCase):
    def test_input_length_routing_and_multimage_limit(self):
        row={'case':{'tokens':2,'keywords':['dog'],'files':['image']},
             'submission_perf_counter':0,'completed_perf_counter':3,
             'response':{'output_token_ids':[1,2],'timestamps':[1.0,2.0],
                         'processed_prompt_token_ids':[9],'output':'dog'}}
        self.assertTrue(validate(row,row)['exact_input_equal'])
        for key,value in (('output_token_ids',[1]),('timestamps',[2.0,1.0]),('output','cat')):
            bad=copy.deepcopy(row)
            bad['response'][key]=value
            with self.assertRaises(RuntimeError): validate(bad,row)
        bad=copy.deepcopy(row)
        bad['response']['processed_prompt_token_ids']=[10]
        with self.assertRaises(RuntimeError): validate(bad,row)
        multi=copy.deepcopy(row)
        multi['case']['files']=['a','b']
        multi['case']['keywords']=['cat','bear']
        self.assertTrue(validate(multi)['reference_semantic_limit'])
        self.assertTrue(validate(multi,multi)['reference_semantic_limit'])

    def test_shared_assets_route_outside_empty_run(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            base=Path(directory);root=base/'run';root.mkdir()
            assets=base/'assets';dataset=assets/'dataset';dataset.mkdir(parents=True)
            (dataset/'manifest.json').write_text(json.dumps({'prompt':'Describe the image.','images':[{'file':str(i)+'.jpg'} for i in range(20)]}))
            model=assets/'models/Qwen2-VL-7B-Instruct';loaded=[];sent=[]
            class Tokenizer:
                @classmethod
                def from_pretrained(cls,path,**kwargs):loaded.append(path);return cls()
                def apply_chat_template(self,messages,**kwargs):return messages[0]['content']
            class Response:
                status=200
                def __init__(self,body):self.body=body
                async def __aenter__(self):return self
                async def __aexit__(self,*args):pass
                async def text(self):
                    paths=self.body['input']['multi_modal_data']['images_paths']
                    words={'0':'bench','1':'dog','2':'bear','5':'cat'}
                    output=' '.join(words.get(Path(p).stem,'object') for p in paths)
                    tokens=self.body['max_tokens'];stamp=time.perf_counter()
                    return json.dumps({'output':output,'output_token_ids':[1]*tokens,'timestamps':[stamp]*tokens,'processed_prompt_token_ids':[9]})
            class Session:
                def __init__(self,**kwargs):pass
                async def __aenter__(self):return self
                async def __aexit__(self,*args):pass
                def post(self,url,json):sent.append(json);return Response(json)
            modules={'aiohttp':types.SimpleNamespace(ClientSession=Session,ClientTimeout=lambda **kwargs:None),
                     'transformers':types.SimpleNamespace(AutoTokenizer=Tokenizer)}
            config=types.SimpleNamespace(asset=lambda relative:assets/relative)
            # The failing version has no CONFIG import; create=True keeps this a behavioral regression.
            with patch.object(suite,'CONFIG',config,create=True),patch.dict('sys.modules',modules):
                self.assertEqual(asyncio.run(suite.run(root,root/'reference.json')),7)
                self.assertEqual(asyncio.run(suite.run(root,root/'target.json',root/'reference.json')),15)
            self.assertEqual(loaded,[str(model),str(model)])
            self.assertEqual(len(sent),22)
            self.assertTrue(all(Path(p).parent==dataset for body in sent for p in body['input']['multi_modal_data']['images_paths']))
            self.assertFalse((root/'dataset').exists())
            self.assertFalse((root/'models').exists())

    def test_partial_responses_survive_cancellation(self):
        class Response:
            status=200
            def __init__(self,wait): self.wait=wait
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
            async def text(self):
                if self.wait: await asyncio.Event().wait()
                return '{"output":"kept response"}'
        class Session:
            def post(self,url,json): return Response(json['wait'])
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path=Path(directory)/'journal.jsonl'
            async def exercise():
                await recorded_request(Session(),{'id':'completed'},{'wait':False},0,path)
                task=asyncio.create_task(recorded_request(Session(),{'id':'cancelled'},{'wait':True},1,path))
                await asyncio.sleep(.01)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError): await task
            asyncio.run(exercise())
            rows=[json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual([row['event'] for row in rows],['submitted','received','submitted','interrupted'])
            self.assertEqual(rows[1]['http_text'],'{"output":"kept response"}')


if __name__=='__main__':
    unittest.main()
