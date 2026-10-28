import copy
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from correctness_suite import validate,recorded_request


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
