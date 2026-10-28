"""Freeze only Git-pinned small code/config files into one run; never copy assets or grant a Gate."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import socket
import time

PREFIX = 'spaceserve/runtime'
REQUIRED = {'scripts/runtime_config.py','scripts/reproduction_paths.py','scripts/resource_guard.py',
            'scripts/booking_window.py','scripts/run_numeric.py','scripts/run_models.py',
            'scripts/run_formal.py','scripts/model_guard.py','scripts/formal_guard.py',
            'configs/schedule-v2.json','configs/input-pins-summary.json','configs/asset-content-pins.json',
            'configs/source-files.json'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(value):
    path = PurePosixPath(value)
    if (not isinstance(value,str) or not value or path.is_absolute() or '..' in path.parts
            or '\\' in value or re.match(r'^[A-Za-z]:',value) or path.as_posix()!=value or value=='.'):
        raise ValueError('Unsafe source/deployment member')
    return path


def plain_parents(path, base):
    if not path.is_relative_to(base): raise ValueError('Destination escapes run')
    for part in (path,*path.parents):
        if part.is_symlink(): raise ValueError('Linked source/run ancestor refused')


def validate_destination(root):
    parent = Path('/local/boyjiang/spaceserve/runs')
    if (socket.gethostname() != 'qjh003' or os.getuid() != 2147 or root.parent != parent
            or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,31}',root.name)
            or root.name == 'UNCONFIGURED'):
        raise ValueError('CPU deployment requires the approved project run on qjh003 UID2147')
    for path in (root, root.parent, root.parent.parent):
        if not path.is_dir() or path.stat().st_uid != os.getuid():
            raise ValueError('Destination must be an existing own real project/run directory')


def deploy(checkout, commit, root):
    checkout, root = Path(checkout).absolute(), Path(root).absolute()
    plain_parents(checkout, checkout); plain_parents(root, root)
    validate_destination(root)
    checkout = checkout.resolve(strict=True)
    if not re.fullmatch('[0-9a-f]{40}',commit): raise ValueError('Exact commit required')
    def git(*args):
        return subprocess.check_output(['git','-C',str(checkout),*args],timeout=60)
    if (git('rev-parse','HEAD').decode().strip()!=commit
            or git('status','--porcelain','--untracked-files=all').strip()):
        raise ValueError('Source is not the clean specified Git commit')
    source = checkout/PREFIX
    index_name = PREFIX+'/configs/source-files.json'
    index_bytes = git('show',commit+':'+index_name)
    if index_bytes != (source/'configs/source-files.json').read_bytes():
        raise ValueError('Source index differs from the committed version')
    members = json.loads(index_bytes)
    destinations = [item['path'] for item in members]
    if (len(destinations)!=len(set(destinations)) or len({m['source'] for m in members})!=len(members)
            or not REQUIRED<=set(destinations)):
        raise ValueError('Missing/duplicate runtime source members')
    receipt = root/'evidence/GIT_DEPLOYED.json'
    if receipt.exists() or any((root/'evidence'/name).exists() for name in (
            'NUMERIC_STARTED.json','MODELS_ATTEMPT1_STARTED.json','FORMAL_STARTED.json')):
        raise ValueError('Run already deployed or launched; do not overwrite')
    frozen = []
    for item in members:
        src, dst = str(relative(item['source'])), str(relative(item['path']))
        if (not src.startswith(PREFIX+'/') and src not in ('reproduction_paths.py','tests/test_reproduction_paths.py')):
            raise ValueError('Source outside the explicit project/common allowlist')
        original, target = checkout/src, root/dst
        plain_parents(original,checkout); plain_parents(target,root)
        raw = git('show',commit+':'+src)
        if original.read_bytes()!=raw or len(raw)>2*1024**2:
            raise ValueError('Source differs or asset/raw data accidentally included')
        if target.exists(): raise ValueError('Refuse existing frozen run member: '+dst)
        frozen.append((target,raw,{'path':dst,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'git_path':src}))
    # Validate every member before the first write. Failed/partial runs remain for diagnosis.
    for target,raw,row in frozen:
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream: stream.write(raw)
        if sha(target)!=row['sha256']: raise ValueError('Frozen bytes differ')
    rows = [{key:row[key] for key in ('path','bytes','sha256')} for _,_,row in frozen]
    manifest = root/'configs/runtime-extension-source-manifest.json'
    with manifest.open('x') as stream: json.dump(rows,stream,indent=2)
    state = {'commit':commit,'source_prefix':PREFIX,'checkout':str(checkout),'runtime_root':str(root),
        'source_manifest_sha256':sha(manifest),'files':[row for _,_,row in frozen],
        'source_index_sha256':hashlib.sha256(index_bytes).hexdigest(),'observed_ms':int(time.time()*1000),
        'scope':'Git code freeze only; not CPU/GPU/G2/G3 approval','new_model_requests':0,'grants_no_GPU':True}
    with receipt.open('x') as stream: json.dump(state,stream,indent=2)
    return state
