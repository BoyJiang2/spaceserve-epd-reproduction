"""Fixed 17-case new-host suite; input/routing failures are never waived."""
import asyncio
import json
import math
from pathlib import Path
import re
import time


def cases(manifest):
    colors = ('red', 'green', 'blue', 'yellow')
    singles = [{'name': color, 'images': [f'routing_{color}.png'], 'tokens': 32,
                'question': 'What is the single dominant color of this image? Reply with one color word.', 'colors': [color]} for color in colors]
    result = singles + [{'name': 'four-colors', 'images': [f'routing_{color}.png' for color in colors], 'tokens': 32,
                         'question': 'List the dominant colors of all four images in order. Reply only with comma-separated color names.', 'colors': list(colors)}]
    result.extend({'name': f'coco-{count}', 'images': [row['file'] for row in manifest['images'][:count]],
                   'tokens': 32, 'question': manifest['prompt']} for count in (1, 4))
    result.extend({**case, 'name': f'c8-{i}', 'parallel': True} for i, case in enumerate(singles * 2))
    result.extend({'name': f'coco8-t{tokens}', 'images': [row['file'] for row in manifest['images'][:8]],
                   'tokens': tokens, 'question': manifest['prompt']} for tokens in (32, 128))
    if len(result) != 17:
        raise RuntimeError('wrong fixed correctness budget')
    return result


async def run(url, model, dataset, output, reference=None):
    import aiohttp
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
    manifest = json.loads((dataset / 'manifest.json').read_text())
    selected = cases(manifest)
    audit_path = output.with_suffix('.requests.jsonl')
    with audit_path.open('x'):
        pass
    output.write_text(json.dumps({'passed': False, 'status': 'running', 'raw_log': audit_path.name}))
    def audit(row):
        with audit_path.open('a') as stream:
            stream.write(json.dumps(row) + '\n')
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
        async def one(case):
            prompt = tokenizer.apply_chat_template([{'role': 'user', 'content': '(<image>./</image>)' * len(case['images']) + case['question']}], tokenize=False, add_generation_prompt=True)
            body = {'input': {'prompt': prompt, 'multi_modal_data': {'images_paths': [str(dataset / name) for name in case['images']]}},
                    'stream': False, 'max_tokens': case['tokens'], 'temperature': 0.0, 'ignore_eos': True}
            started = time.perf_counter()
            result = None
            audit({'event': 'submitted', 'case': case, 'submission_perf_counter': started})
            try:
                async with session.post(url + '/generate', json=body) as response:
                    if response.status != 200:
                        result = {'http_status': response.status, 'http_body': (await response.text())[:2000]}
                        raise RuntimeError('correctness HTTP ' + str(response.status))
                    result = await response.json()
                ended = time.perf_counter()
                tokens, stamps = result['output_token_ids'], result['timestamps']
                if len(tokens) != case['tokens'] or len(stamps) != len(tokens) or any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in stamps) or any(b < a for a, b in zip(stamps, stamps[1:])) or not started <= stamps[0] <= stamps[-1] <= ended:
                    raise RuntimeError('output length or clock mismatch')
                if not isinstance(result.get('repro_request_id'), str) or not result['repro_request_id'].strip():
                    raise RuntimeError('request ID missing or empty')
                starts = {getattr(tokenizer, name) for name in ('im_start_id', 'slice_start_id') if hasattr(tokenizer, name)}
                ends = {getattr(tokenizer, name) for name in ('im_end_id', 'slice_end_id') if hasattr(tokenizer, name)}
                inside, visual = False, 0
                for token in result['processed_prompt_token_ids']:
                    if token in starts:
                        inside = True
                    elif token in ends:
                        inside = False
                    elif inside:
                        visual += 1
                if visual != 64 * len(case['images']):
                    raise RuntimeError('unexpected visual-token processing')
                row = {'case': case, 'response': result, 'visual_tokens': visual}
                audit({'event': 'completed', 'success': True, **row})
                return row
            except BaseException as error:
                row = {'event': 'completed', 'case': case, 'success': False, 'error': repr(error), 'response': result}
                audit(row)
                output.write_text(json.dumps({'passed': False, 'status': 'failed', 'error': repr(error), 'raw_log': audit_path.name}))
                raise

        results = []
        results.extend(await asyncio.gather(*(one(case) for case in selected[:4])))
        for case in selected[4:7]:
            results.append(await one(case))
        results.extend(await asyncio.gather(*(one(case) for case in selected[7:15])))
        for case in selected[15:]:
            results.append(await one(case))
    errors, differences = [], []
    if reference is not None and len(reference) != 17:
        raise RuntimeError('wrong reference budget')
    for index, row in enumerate(results):
        case, result = row['case'], row['response']
        colors = re.findall(r'\b(red|green|blue|yellow)\b', result['output'].lower())
        if case.get('colors') and len(case['images']) == 1 and colors[:1] != case['colors']:
            errors.append(case['name'] + ':single-color routing')
        if reference is not None:
            golden = reference[index]
            if golden['case'] != case or golden['response']['processed_prompt_token_ids'] != result['processed_prompt_token_ids']:
                errors.append(case['name'] + ':input IDs')
            equal = golden['response']['output_token_ids'] == result['output_token_ids']
            row['exact_token_ids_equal'] = equal
            if not equal:
                differences.append(case['name'])
            if case.get('colors') and len(case['images']) > 1:
                golden_colors = re.findall(r'\b(red|green|blue|yellow)\b', golden['response']['output'].lower())
                row['reference_quality_limit'] = golden_colors[:4] != case['colors']
                if row['reference_quality_limit'] and not equal:
                    errors.append(case['name'] + ':baseline quality limited and token IDs differ')
                elif not row['reference_quality_limit'] and colors[:4] != case['colors']:
                    errors.append(case['name'] + ':multi-color routing')
    if len({row['response']['output'] for row in results[:4]}) != 4:
        errors.append('four single-color responses not distinct')
    if len({str(row['response'].get('repro_request_id')) for row in results}) != 17:
        errors.append('request IDs not unique')
    output.write_text(json.dumps({'passed': not errors, 'errors': errors, 'output_differences': differences,
                                  'natural_image_semantic_correctness_guaranteed': False, 'cases': results}, indent=2))
    if errors:
        raise RuntimeError('correctness suite failed: ' + repr(errors))
    return results
