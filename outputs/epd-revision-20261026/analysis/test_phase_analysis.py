"""Synthetic end-to-end B/C fixtures, never evidence of a GPU experiment."""
import copy
import datetime
import hashlib
import json
import shutil
from pathlib import Path
import tempfile
import unittest

import test_analyze_cells as fixture
from analyze_cells import CODE_SHA256, HOST_ROOT, LOADS, analyze


def write(path, value, lines=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = '\n'.join(json.dumps(row) for row in value) + '\n' if lines else json.dumps(value)
    path.write_bytes(text.encode())


def create_phase(root, phase):
    source = Path(__file__).resolve().parents[1]
    schedule_name = 'B' if phase == 'overhead' else 'C'
    for name in ['code-manifest.json', f'{schedule_name}-schedule.json']:
        target = root / 'configs' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source / 'configs' / name).read_bytes())
    schedule_path = root / f'configs/{schedule_name}-schedule.json'
    rows = json.loads(schedule_path.read_bytes())['rows']
    baseline = fixture.AuditTests()
    baseline.setUp()
    write(root / 'dataset/manifest.json', baseline.dataset)
    images=[{'file':f'{i}.jpg','sha256':'d'*64,'rgb_sha256':'c'*64,'size':[448,448]} for i in range(20)]
    protocol={'inference_requests':0,'dataset_manifest_sha256':hashlib.sha256((root/'dataset/manifest.json').read_bytes()).hexdigest(),
              'images':images,'loads':{},'boot_id':'same-test-boot','frozen_at_utc':'2026-10-26T12:59:00+00:00','freeze_perf_counter':0}
    for name,(count,tokens,concurrency) in LOADS.items():
        requests=[{'warmup':warmup,'index':i,'images':[images[(i*count+j)%20] for j in range(count)]}
                  for warmup,total in [(True,20),(False,100)] for i in range(total)]
        protocol['loads'][name]={'prompt':'synthetic-prompt','prompt_sha256':hashlib.sha256(b'synthetic-prompt').hexdigest(),'requests':requests}
    protocol_path=root/'evidence/frozen-request-protocol.json'
    write(protocol_path,protocol)
    references = {'cases': [{'case': {'name': name}, 'response': {'processed_prompt_token_ids': [1, 2, 3]}}
                  for name in ('coco-1', 'coco-4', 'coco8-t128')]}
    reference_path = root / 'results/preflight-models/reference.json'
    write(reference_path, references)
    write(root / 'evidence/G3_MODELS_APPROVED.json', {'passed': True, 'code_manifest_sha256': CODE_SHA256,
          'gpu_uuids': __import__('analyze_cells').UUIDS, 'boot_id': 'same-test-boot',
          'bound_files': [{'path': 'results/preflight-models/reference.json', 'sha256': hashlib.sha256(reference_path.read_bytes()).hexdigest()},
                          {'path':'evidence/frozen-request-protocol.json','sha256':hashlib.sha256(protocol_path.read_bytes()).hexdigest()}]})
    folders = []
    for index, row in enumerate(rows):
        folder = root / 'results' / phase / f'{index:03d}-b{row["block"]}-{row["load"]}-{row["system"]}-{row["mode"]}'
        folders.append(folder)
        files = copy.deepcopy(baseline.files)
        files['COMPLETED'] = row
        config = files['measurement/config.json']
        config.update(images=row['images'], tokens=row['tokens'], concurrency=row['concurrency'], lite=row['mode']=='lite')
        urls = ['http://127.0.0.1:19810'] if row['system']=='epd' else [f'http://127.0.0.1:{19800+i}' for i in range(3)]
        config['urls'] = urls
        for request in files['measurement/requests.jsonl']:
            request['images'] = [HOST_ROOT+f'/dataset/{(request["index"]*row["images"]+j)%20}.jpg' for j in range(row['images'])]
            request['endpoint'] = urls[request['index'] % len(urls)]
            request['visual_tokens'] = 64*row['images']
            request['output_tokens'] = row['tokens']
            request['submission_perf_counter'] += index*300
            request['response']['output_token_ids'] = [7]*row['tokens']
            request['response']['timestamps'] = [request['submission_perf_counter']+.1+i*.01 for i in range(row['tokens'])]
        summary = files['measurement/summary.json'][0]
        summary['start_perf_counter'] += index*300
        summary['end_perf_counter'] += index*300
        summary['output_tokens_per_s'] = row['tokens']/2
        for sample in files['gpu-memory.jsonl']:
            sample['perf_counter'] += index*300
        for when in ('before', 'after'):
            files[f'host-{when}.json']['host_ns'] += index*300*10**9
        files['runtime.json']['captured_utc'] = (datetime.datetime(2026,10,26,13,tzinfo=datetime.timezone.utc)+datetime.timedelta(seconds=index*300)).isoformat()
        model = files.pop('model-runtime-0.json')
        if row['system']=='epd':
            files['model-runtime-0.json']=model
            api_pids=[14]
        else:
            api_pids=[15,16,17]
            for i,pid in enumerate(api_pids):
                files[f'model-runtime-{i}.json']={'pid':pid,'operation':'runtime','results':[model['results'][i]]}
        for when in ('before','after'):
            record = files[f'rgb-{when}.json']['records'][0]
            record['manifest_sha256']=protocol['dataset_manifest_sha256']
            files[f'rgb-{when}.json']['records']=[{**record,'pid':pid,'url':url} for pid,url in zip(api_pids,urls)]
        if row['mode']=='lite':
            controls=[]
            for operation in ('reset','export'):
                for url,api_pid in zip(urls,api_pids):
                    pids=[15,16,17,14] if row['system']=='epd' else [api_pid]
                    results=[]
                    for pid in pids:
                        if operation=='reset':
                            results.append({'pid':pid,'reset':True})
                            continue
                        payload={'pid':pid,'overflow':False,'events':[], 'gpu_stream_windows':[{'stream_elapsed_ms':1}] if pid in [15,16,17] else [],
                                 'run_id':HOST_ROOT+':'+folder.name+':synthetic'}
                        files[f'lite/process-{pid}.json']=payload
                        results.append({'pid':pid,'overflow':False,'events':0,'gpu_windows':len(payload['gpu_stream_windows']),
                                        'path':f'{HOST_ROOT}/results/{phase}/{folder.name}/lite/process-{pid}.json'})
                    t=summary['start_perf_counter']-1 if operation=='reset' else summary['end_perf_counter']+1
                    controls.append({'operation':operation,'endpoint':url,'start':t,'end':t+.01,
                                     'state':{'pid':api_pid,'operation':operation,'results':results}})
            files['measurement/capture-control.json']=controls
        for name,value in files.items():
            write(folder/name,value,lines=name.endswith('.jsonl'))
    write(root / 'results' / phase / 'COMPLETED', {'code_manifest_sha256':CODE_SHA256,'schedule_sha256':hashlib.sha256(schedule_path.read_bytes()).hexdigest()})
    return folders


class PhaseTests(unittest.TestCase):
    def test_partial_still_checks_boot_and_chronology(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            root = Path(temporary)
            folders = create_phase(root, 'performance')
            (folders[-1] / 'COMPLETED').unlink()
            path = folders[0] / 'runtime.json'
            value = json.loads(path.read_bytes())
            value['boot_id'] = 'other-boot'
            write(path, value)
            result = analyze(root, 'performance')
            self.assertFalse(result['complete'])
            self.assertIn('host boot differs across blocks', result['chronology_errors'])
            self.assertFalse(result['intervals'])

    def test_continuation_ranges_are_explicit_and_cannot_expand_the_prefix(self):
        from analyze_cells import PREFIX_CODE_SHA256
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            root = Path(temporary)
            create_phase(root, 'performance')
            path = root / 'evidence/G3_MODELS_APPROVED.json'
            value = json.loads(path.read_bytes())
            value.update(scope='C-off-only', one_C_continuation_only=True,
                         performance_execution=[{'indices': [0, 9], 'producer_sha256': PREFIX_CODE_SHA256},
                                                {'indices': [10, 59], 'producer_sha256': CODE_SHA256}])
            write(path, value)
            result = analyze(root, 'performance')
            self.assertTrue(result['complete'])
            self.assertEqual(result['continuation_formal_window_gap_s'], 100)
            value['performance_execution'][0]['indices'] = [0, 10]
            write(path, value)
            with self.assertRaisesRegex(ValueError, 'producer ranges'):
                analyze(root, 'performance')

    def test_complete_B_and_overflow_not_accepted(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            root=Path(temporary)
            folders=create_phase(root,'overhead')
            result=analyze(root,'overhead')
            self.assertTrue(result['complete'])
            self.assertTrue(result['all_metric_equivalence_demonstrated'])
            self.assertEqual(len(result['intervals']),12)
            target=next(p for p in folders if p.name.endswith('-lite'))/'lite/process-15.json'
            payload=json.loads(target.read_bytes()); payload['overflow']=True
            write(target,payload)
            result=analyze(root,'overhead')
            self.assertFalse(result['complete'])
            self.assertFalse(result['intervals'])

    def test_complete_C_and_changed_boot_or_replayed_run_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            root=Path(temporary)
            folders=create_phase(root,'performance')
            result=analyze(root,'performance')
            self.assertTrue(result['complete'])
            self.assertEqual(len(result['intervals']),5)
            self.assertEqual(set(result['exploratory_contrasts']),{'D/C','E/D'})
            marker=folders[0]/'runtime.json'
            value=json.loads(marker.read_bytes()); value['boot_id']='other-boot'
            write(marker,value)
            result=analyze(root,'performance')
            self.assertFalse(result['complete'])
            self.assertIn('host boot differs across blocks',result['chronology_errors'])
            self.assertFalse(result['intervals'])
            value['boot_id']='same-test-boot'
            write(marker,value)
            first_row=json.loads((folders[0]/'COMPLETED').read_bytes())
            target=next(p for p in folders[2:] if all(json.loads((p/'COMPLETED').read_bytes())[k]==first_row[k] for k in ['load','system']))
            target_row=json.loads((target/'COMPLETED').read_bytes())
            shutil.copytree(folders[0],target,dirs_exist_ok=True)
            write(target/'COMPLETED',target_row)
            result=analyze(root,'performance')
            self.assertFalse(result['complete'])
            self.assertIn('overlapping/out-of-order actual cells',result['chronology_errors'])
            self.assertIn('duplicated runtime evidence',result['chronology_errors'])


if __name__=='__main__':
    unittest.main()
