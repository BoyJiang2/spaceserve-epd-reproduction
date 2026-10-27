"""Rehash model/data/source and freeze CPU tokenizer prompts; no CUDA/model forward."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import time

ROOT=Path('/var/tmp/boyjiang-spaceserve-revision-20261027')


def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as source:
        while block:=source.read(1024**2):
            value.update(block)
    return value.hexdigest()


def main():
    if not __debug__ or os.uname().nodename!='qjh000' or os.getuid()!=2147:
        raise RuntimeError('unexpected CPU model verification host/UID')
    from transformers import AutoTokenizer
    manifest_path=ROOT/'configs/relocated-inputs.json'
    manifest=json.loads(manifest_path.read_text())
    checked=[]
    prefixes=('models/','dataset/','src/SpaceServe/','envs/space/lib/python3.10/site-packages/vllm/')
    for row in manifest:
        if not row['path'].startswith(prefixes):
            continue
        path=ROOT/row['path']
        if 'sha256' in row:
            if path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:
                raise RuntimeError('model/data/runtime source changed: '+row['path'])
        elif path.readlink().as_posix()!=row['link'] or not path.resolve(strict=True).is_relative_to(ROOT):
            raise RuntimeError('relocated runtime link changed: '+row['path'])
        checked.append(row)
    tokenizer=AutoTokenizer.from_pretrained(str(ROOT/'models/Qwen2-VL-7B-Instruct'),trust_remote_code=True)
    dataset=json.loads((ROOT/'dataset/manifest.json').read_text())
    prompts={}
    for images in (1,4):
        prompt=tokenizer.apply_chat_template([{'role':'user','content':
            '<|vision_start|><|image_pad|><|vision_end|>'*images+dataset['prompt']}],
            tokenize=False,add_generation_prompt=True)
        prompts[str(images)]={'prompt':prompt,'sha256':hashlib.sha256(prompt.encode()).hexdigest(),
            'requests':[{'warmup':warm,'index':i,'images':[dataset['images'][(i*images+j)%20]['file'] for j in range(images)]}
                        for warm,count in ((True,20),(False,100)) for i in range(count)]}
    state={'passed':True,'verified_epoch':time.time(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
           'input_manifest_sha256':sha(manifest_path),'checked_files':checked,'frozen_prompts':prompts,
           'new_model_requests':0,'scope':'CPU input verification; no CUDA/model correctness approval'}
    with (ROOT/'evidence/MODEL_INPUTS_VERIFIED-attempt1.json').open('x') as output:
        json.dump(state,output,indent=2)
    print(json.dumps({'checked':len(checked),'prompt_shapes':2,'new_model_requests':0}))


if __name__=='__main__':
    main()
