"""Preserve the original numeric proof bytes before mutable model-phase state changes."""
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT=Path('/var/tmp/boyjiang-spaceserve-window-20261027-1300')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(root):
    original=root/'evidence/G3_NUMERICAL_APPROVED.json'
    gate=json.loads(original.read_text())
    rows=gate['bound_files']+[{'path':'evidence/G3_NUMERICAL_APPROVED.json','bytes':original.stat().st_size,'sha256':sha(original)}]
    if len({row['path'] for row in rows})!=len(rows):
        raise RuntimeError('duplicate original numeric proof path')
    for row in rows:
        relative=Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix()!=row['path']:
            raise RuntimeError('unsafe original numeric proof path')
        source=root/row['path']
        if not source.resolve(strict=True).is_relative_to(root) or source.is_symlink() or source.stat().st_size!=row['bytes'] or sha(source)!=row['sha256']:
            raise RuntimeError('original numeric proof no longer matches: '+row['path'])
    archive=root/'evidence/numeric-producer'
    archive.mkdir(exist_ok=False)
    mapping=[]
    for row in rows:
        target=archive/row['path']
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/row['path'],target)
        if sha(target)!=row['sha256'] or sha(root/row['path'])!=row['sha256']:
            raise RuntimeError('numeric archive/source changed during copy')
        mapping.append({**row,'archive_path':target.relative_to(root).as_posix()})
    receipt={'scope':'CPU-numeric-proof-archive-only','producer_sha256':gate['producer_sha256'],
             'original_gate_sha256':sha(original),'mapping':mapping,'grants_no_GPU_or_G3':True}
    with (root/'evidence/numeric-producer-path-mapping.json').open('x') as output:
        json.dump(receipt,output,indent=2)
    return receipt


if __name__=='__main__':
    if not __debug__ or os.uname().nodename!='qjh000' or os.getuid()!=2147:
        raise RuntimeError('unexpected numeric archive host/UID')
    result=freeze(ROOT)
    print(json.dumps({'archived':len(result['mapping']),'producer':result['producer_sha256'],'grants_no_G3':True}))
