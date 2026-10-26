"""CPU-only request manifest before inference; exact shared benchmark template."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import time

from analyze_cells import HOST_ROOT, LOADS


def build(root, tokenizer):
    from PIL import Image
    dataset = root / 'dataset'
    manifest_path = dataset / 'manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    if len(manifest['images']) != 20:
        raise ValueError('require the frozen 20-image dataset')
    images = []
    for row in manifest['images']:
        path = dataset / row['file']
        if path.resolve().parent != dataset.resolve() or path.name != row['file']:
            raise ValueError('image escaped frozen dataset')
        with Image.open(path) as source:
            rgb = source.convert('RGB')
            if rgb.size != (448, 448):
                raise ValueError('image sizing differs from frozen protocol')
            images.append({'file': row['file'], 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                           'rgb_sha256': hashlib.sha256(rgb.tobytes()).hexdigest(), 'size': list(rgb.size)})
    if len({image['file'] for image in images}) != 20:
        raise ValueError('duplicate dataset images')
    loads = {}
    for name, (count, tokens, concurrency) in LOADS.items():
        prompt = tokenizer.apply_chat_template([{'role': 'user', 'content': '(<image>./</image>)' * count + manifest['prompt']}],
                                               tokenize=False, add_generation_prompt=True)
        requests = []
        for warmup, total in ((True, 20), (False, 100)):
            for index in range(total):
                requests.append({'warmup': warmup, 'index': index,
                    'images': [images[(index * count + j) % 20] for j in range(count)]})
        loads[name] = {'images': count, 'tokens': tokens, 'concurrency': concurrency,
                       'prompt': prompt, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                       'temperature': 0.0, 'ignore_eos': True, 'requests': requests}
    return {'dataset_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'model': HOST_ROOT + '/models/MiniCPM-V-2_6', 'dataset': HOST_ROOT + '/dataset',
            'tokenizer_class': type(tokenizer).__name__, 'images': images, 'loads': loads,
            'inference_requests': 0, 'grants_no_gate': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if root != Path(HOST_ROOT):
        raise RuntimeError('production freeze must use the dedicated target root')
    if args.output.resolve() != root / 'evidence/frozen-request-protocol.json':
        raise RuntimeError('request freeze output must be the dedicated new evidence file')
    # Tokenizer loads CPU metadata only; no model, Torch tensor or CUDA operation.
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(root/'models/MiniCPM-V-2_6', trust_remote_code=True, local_files_only=True)
    result = build(root, tokenizer)
    result.update(frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  freeze_perf_counter=time.perf_counter(),
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
