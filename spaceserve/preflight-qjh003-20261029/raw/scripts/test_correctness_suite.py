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
            model=assets/'models/Qwen2-VL-7B-Instruct';loaded=[];sent=[];connectors=[]
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
            def connector(**kwargs):connectors.append(kwargs);return kwargs
            modules['aiohttp'].TCPConnector=connector
            config=types.SimpleNamespace(asset=lambda relative:assets/relative)
            # The failing version has no CONFIG import; create=True keeps this a behavioral regression.
            with patch.object(suite,'CONFIG',config,create=True),patch.dict('sys.modules',modules):
                self.assertEqual(asyncio.run(suite.run(root,root/'reference.json')),7)
                self.assertEqual(asyncio.run(suite.run(root,root/'target.json',root/'reference.json')),15)
            self.assertEqual(connectors,[{'force_close':True},{'force_close':True}])
            self.assertEqual(loaded,[str(model),str(model)])
            self.assertEqual(len(sent),22)
            self.assertTrue(all(Path(p).parent==dataset for body in sent for p in body['input']['multi_modal_data']['images_paths']))
            self.assertFalse((root/'dataset').exists())
            self.assertFalse((root/'models').exists())

    def test_connection_reuse_does_not_retry_posts(self):
        import aiohttp
        async def exercise(force_close,path):
            peers=[];received=[]
            async def serve(reader,writer):
                peers.append(writer)
                try:
                    while True:
                        header=await reader.readuntil(b'\r\n\r\n')
                        length=int(next(line.split(b':',1)[1] for line in header.split(b'\r\n') if line.lower().startswith(b'content-length:')))
                        received.append(await reader.readexactly(length))
                        body=b'{"output":"ok"}'
                        writer.write(b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(body)).encode()+b'\r\nConnection: keep-alive\r\n\r\n'+body)
                        await writer.drain()
                except (asyncio.IncompleteReadError,ConnectionError):pass
                finally:writer.close()
            async def reused(session,context,params):
                peers[-1].transport.abort()
                await asyncio.sleep(.01)
            trace=aiohttp.TraceConfig();trace.on_connection_reuseconn.append(reused)
            server=await asyncio.start_server(serve,'127.0.0.1',0)
            try:
                port=server.sockets[0].getsockname()[1]
                class LocalSession:
                    def __init__(self,session):self.session=session
                    def post(self,url,json):return self.session.post('http://127.0.0.1:'+str(port),json=json)
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(force_close=force_close),trace_configs=[trace],timeout=aiohttp.ClientTimeout(total=2)) as client:
                    session=LocalSession(client)
                    first=await recorded_request(session,{'id':'cpu-http'},{'ping':1},0,path)
                    second=await recorded_request(session,{'id':'cpu-http'},{'ping':2},1,path)
                self.assertEqual(first.get('http_status'),200)
                self.assertEqual(len(received),2 if force_close else 1)
                self.assertEqual(second.get('http_status'),200 if force_close else None)
                rows=[json.loads(line) for line in path.read_text().splitlines()]
                self.assertEqual(sum(row['event']=='submitted' for row in rows),2)
                self.assertEqual(sum(row['event']=='error' for row in rows),0 if force_close else 1)
            finally:
                server.close();await server.wait_closed()
                for writer in peers:writer.close()
                await asyncio.sleep(.01)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            for force in (False,True):
                asyncio.run(asyncio.wait_for(exercise(force,Path(directory)/('http-'+str(force)+'.jsonl')),5))

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
