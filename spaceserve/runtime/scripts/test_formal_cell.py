import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit_formal_cell


def fixture(root):
    case=root/'case'
    (case/'measurement').mkdir(parents=True)
    (root/'dataset').mkdir()
    (root/'evidence').mkdir()
    (root/'models/Qwen2-VL-7B-Instruct').mkdir(parents=True)
    (root/'models/Qwen2-VL-7B-Instruct/config.json').write_text('{"image_token_id":99}')
    (root/'results/preflight-models-attempt1').mkdir(parents=True)
    (root/'results/preflight-models-attempt1/reference.json').write_text(json.dumps([{'case':{'id':'coco-4'},'response':{'processed_prompt_token_ids':[99]*1024}}]))
    (case/'launch.json').write_text('{"role":"baseline-space","block":0}')
    manifest={'images':[{'file':f'image{i}.jpg'} for i in range(20)]}
    (root/'dataset/manifest.json').write_text(json.dumps(manifest))
    (root/'evidence/MODEL_INPUTS_VERIFIED-attempt1.json').write_text(json.dumps({'frozen_prompts':{'4':{'prompt':'frozen'}}}))
    config={'model':str(root/'models/Qwen2-VL-7B-Instruct'),'dataset':str(root/'dataset'),
            'urls':['http://127.0.0.1:19770'],'images':4,'concurrency':4,'tokens':128,'warmup':20,
            'requests':100,'repetitions':1,'prompt':'frozen','profile_after_warmup':False}
    (case/'measurement/config.json').write_text(json.dumps(config))
    rows=[]
    for warm,count in ((True,20),(False,100)):
        for i in range(count):
            start=999+i*.0001 if warm else 1000+i*.05
            stamps=[start+.01+j*.001 for j in range(128)]
            rows.append({'index':i,'warmup':warm,'repetition':-1 if warm else 0,'success':True,
                'output_tokens':128,'visual_tokens':1024,'submission_perf_counter':start,'latency_s':.2,
                'endpoint':'http://127.0.0.1:19770',
                'ttft_s':stamps[0]-start,'tpot_s':(stamps[-1]-stamps[0])/127,
                'images':[str(root/'dataset'/f'image{(i*4+j)%20}.jpg') for j in range(4)],
                'response':{'output_token_ids':[1]*128,'timestamps':stamps,'processed_prompt_token_ids':[99]*1024}})
    (case/'measurement/requests.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    summary={'repetition':0,'start_perf_counter':1000,'end_perf_counter':1006,'duration_s':6,
             'requests':100,'successes':100,'failure_rate':0,'requests_per_s':100/6,'output_tokens_per_s':12800/6,
             'latency_s':{'p50':.2,'p95':.2},'ttft_s':{'p50':.01,'p95':.01},'tpot_s':{'p50':.001,'p95':.001}}
    (case/'measurement/summary.json').write_text(json.dumps([summary]))
    gpu={'device':4,'foreign_compute_pids':[],'owned_processes':[{'pid':123,'used_bytes':120}], 'owned_process_sum_bytes':120}
    samples=[{'perf_counter':1000+i*.1,'gpus':[copy.deepcopy(gpu)]} for i in range(61)]
    (case/'gpu-memory.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in samples))
    (case/'rgb-after.json').write_text('{"passed":true}')
    return case,rows,samples


class FormalCellTests(unittest.TestCase):
    def test_exact_single_cell_and_reject_corrupted_inputs_or_monitor(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory).resolve()
            case,rows,samples=fixture(root)
            planned={'images':4,'concurrency':4,'role':'baseline-space','block':0}
            with patch.object(audit_formal_cell,'ROOT',root):
                self.assertEqual(audit_formal_cell.audit(case,planned)['formal_requests'],100)
                for key,value in (('endpoint','http://wrong'),('response',{'processed_prompt_token_ids':[0]*1024})):
                    bad=copy.deepcopy(rows)
                    bad[-1][key]=value
                    (case/'measurement/requests.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in bad))
                    with self.assertRaisesRegex(RuntimeError,'processed input IDs'): audit_formal_cell.audit(case,planned)
                (case/'measurement/requests.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
                with self.assertRaisesRegex(RuntimeError,'model or load'):
                    audit_formal_cell.audit(case,{**planned,'images':1})
                corrupted=copy.deepcopy(rows)
                corrupted[-1]['images'].reverse()
                (case/'measurement/requests.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in corrupted))
                with self.assertRaisesRegex(RuntimeError,'image sequence'): audit_formal_cell.audit(case,planned)
                (case/'measurement/requests.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
                samples[30]['gpus'][0]['foreign_compute_pids']=[999]
                (case/'gpu-memory.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in samples))
                with self.assertRaisesRegex(RuntimeError,'foreign target'): audit_formal_cell.audit(case,planned)


if __name__=='__main__': unittest.main()
