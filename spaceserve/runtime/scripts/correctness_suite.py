"""Fixed Qwen reference and routing suite; exactly 7 reference or 15 target requests."""
import asyncio
import json
import math
import os
from pathlib import Path
import time
from resource_guard import RunInterrupted,CONFIG


def journal(path,event):
    with path.open('a',encoding='utf-8') as output:
        output.write(json.dumps(event)+'\n')
        output.flush()
        os.fsync(output.fileno())


async def recorded_request(session,case,body,index,path):
    row={'case':case,'request':body,'request_index':index,'submission_perf_counter':time.perf_counter()}
    journal(path,{'event':'submitted',**row})
    try:
        async with session.post('http://127.0.0.1:19770/generate',json=body) as response:
            text=await response.text()
            row.update(http_status=response.status,completed_perf_counter=time.perf_counter())
            journal(path,{'event':'received','request_index':index,'http_text':text,
                          'http_status':response.status,'completed_perf_counter':row['completed_perf_counter']})
            row['response']=json.loads(text)
    except BaseException as error:
        row['error']=type(error).__name__+': '+str(error)
        journal(path,{'event':'interrupted' if isinstance(error,(asyncio.CancelledError,RunInterrupted)) else 'error',
                      'request_index':index,'error':row['error'],'perf_counter':time.perf_counter()})
        if not isinstance(error,Exception) or isinstance(error,RunInterrupted):
            raise
    return row


def cases(dataset):
    manifest=json.loads((dataset/'manifest.json').read_text())
    subjects=(('bench',0),('dog',1),('bear',2),('cat',5))
    rows=[{'id':subject,'files':[manifest['images'][index]['file']], 'keywords':[subject],
           'question':'Describe the main subject in this image in one short sentence.','tokens':32}
          for subject,index in subjects]
    rows.append({'id':'four-coco-subjects','files':[manifest['images'][index]['file'] for _,index in subjects],
                 'keywords':[subject for subject,_ in subjects], 'tokens':128,
                 'question':'Describe each of the four images separately, in order, using one short sentence per image.'})
    for count in (1,4):
        rows.append({'id':f'coco-{count}','files':[r['file'] for r in manifest['images'][:count]],
                     'question':manifest['prompt'],'tokens':32})
    return rows


def validate(row,reference=None):
    response=row['response']
    case=row['case']
    tokens=response['output_token_ids']
    stamps=response['timestamps']
    if len(tokens)!=case['tokens'] or len(stamps)!=len(tokens) or not response['processed_prompt_token_ids']:
        raise RuntimeError('incorrect output length or absent actual processed input IDs')
    if any(not math.isfinite(t) for t in stamps) or any(a>b for a,b in zip(stamps,stamps[1:])):
        raise RuntimeError('invalid generation timestamps')
    if not row['submission_perf_counter']<=stamps[0]<=stamps[-1]<=row['completed_perf_counter']:
        raise RuntimeError('generation timestamps outside the actual submitted request')
    keywords=case.get('keywords',[])
    locations=[response['output'].lower().find(word) for word in keywords]
    semantic=all(value>=0 for value in locations) and locations==sorted(locations)
    result={'semantic_check':semantic,'exact_output_equal':None,'exact_input_equal':None}
    if reference is None and len(case['files'])>1 and not semantic:
        result['reference_semantic_limit']=True
        return result
    if reference is not None:
        expected=reference['response']
        result['exact_output_equal']=tokens==expected['output_token_ids']
        result['exact_input_equal']=response['processed_prompt_token_ids']==expected['processed_prompt_token_ids']
        if not result['exact_input_equal']:
            raise RuntimeError('actual processed inputs differ from native reference')
        ref_positions=[expected['output'].lower().find(word) for word in keywords]
        reference_semantic=all(value>=0 for value in ref_positions) and ref_positions==sorted(ref_positions)
        result['reference_semantic_limit']=not reference_semantic
        if not reference_semantic and len(case['files'])>1:
            semantic=result['exact_output_equal']
    if not semantic:
        raise RuntimeError('fixed semantic/routing check failed')
    return result


async def run(root,output,reference_path=None):
    import aiohttp
    from transformers import AutoTokenizer
    dataset=CONFIG.asset('dataset')
    suites=cases(dataset)
    references=json.loads(reference_path.read_text()) if reference_path else None
    if references is not None:
        if [r['case'] for r in references]!=suites:
            raise RuntimeError('reference suite differs')
        selected=suites+suites[:4]*2
        expected=references+references[:4]*2
    else:
        selected=suites
        expected=[None]*7
    tokenizer=AutoTokenizer.from_pretrained(str(CONFIG.asset('models/Qwen2-VL-7B-Instruct')),trust_remote_code=True)
    raw_path=output.with_suffix('.jsonl')
    with raw_path.open('x',encoding='utf-8') as raw:
        raw.write(json.dumps({'event':'suite-start','expected_requests':len(selected)})+'\n')
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
        async def request(index,case):
            prompt=tokenizer.apply_chat_template([{'role':'user','content':
                '<|vision_start|><|image_pad|><|vision_end|>'*len(case['files'])+case['question']}],
                tokenize=False,add_generation_prompt=True)
            body={'input':{'prompt':prompt,'multi_modal_data':{'images_paths':[str(dataset/name) for name in case['files']]}},
                  'stream':False,'temperature':0.0,'max_tokens':case['tokens'],'ignore_eos':True}
            return await recorded_request(session,case,body,index,raw_path)
        # Preserve the existing C4 distinct subjects, sequential multi-image, then C8 routing protocol.
        rows=await asyncio.gather(*(request(index,case) for index,case in enumerate(selected[:4])))
        for index,case in enumerate(selected[4:7],4):
            rows.append(await request(index,case))
        if references is not None:
            rows+=await asyncio.gather(*(request(index,case) for index,case in enumerate(selected[7:],7)))
    failures=[]
    for index,(row,reference) in enumerate(zip(rows,expected)):
        try:
            if row.get('http_status')!=200:
                raise RuntimeError('HTTP failure or request exception')
            row['checks']=validate(row,reference)
        except Exception as error:
            row['check_error']=type(error).__name__+': '+str(error)
            failures.append(index)
    if len({row.get('response',{}).get('output') for row in rows[:4]})!=4:
        failures.append('first-four-routing-not-distinct')
    with output.open('x',encoding='utf-8') as stream:
        json.dump(rows,stream,indent=2)
    if failures:
        raise RuntimeError('correctness suite failed; original per-request records preserved: '+str(failures))
    return len(rows)
