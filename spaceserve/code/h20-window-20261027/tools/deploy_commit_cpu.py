"""Deploy already-reviewed bytes from a clean, exact Git commit; never starts GPU work."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess

ROOT=Path('/var/tmp/boyjiang-spaceserve-window-20261027-1300')
PREFIX='spaceserve/code/h20-window-20261027'
SOURCE_SHA='d47327211a2dc79f7e74ffe45ef1e6bf0511049433eea5625b52b6bc9df3c819'
DEPLOYMENT_SHA='e1cfc507451790013b84d57c05e1d7208fff3b5ed1d824d38ccdca4fcbddf998'
STATIC_CONFIGS={'configs/'+name for name in ('runtime-extension-source-manifest.json',
    'schedule-v2.json','input-pins-summary.json','expected-staged-version.json','relocated-inputs.json')}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deploy(checkout,commit,root):
    if not re.fullmatch('[0-9a-f]{40}',commit):raise RuntimeError('exact commit required')
    def git(*args):
        return subprocess.check_output(['git','-C',str(checkout),*args],text=True).strip()
    if git('rev-parse','HEAD')!=commit or git('status','--porcelain','--untracked-files=all'):
        raise RuntimeError('checkout is not the clean specified commit')
    if root.is_symlink() or any((root/'evidence'/name).exists() for name in
                               ('MODELS_ATTEMPT1_STARTED.json','FORMAL_STARTED.json')):
        raise RuntimeError('refuse deployment into launched or linked root')
    source=checkout/PREFIX
    inventory=source/'configs/deployment-files.json'
    rows=json.loads(inventory.read_text())
    if sha(inventory)!=DEPLOYMENT_SHA or len(rows)!=61 or len({r['path'] for r in rows})!=61:
        raise RuntimeError('reviewed deployment membership differs')
    if sha(source/'configs/runtime-extension-source-manifest.json')!=SOURCE_SHA:
        raise RuntimeError('reviewed source manifest differs')
    sources=json.loads((source/'configs/runtime-extension-source-manifest.json').read_text())
    if (len(sources)!=56 or {r['path'] for r in rows}!={r['path'] for r in sources}|STATIC_CONFIGS
            or any(r not in rows for r in sources)):
        raise RuntimeError('deployment omits or changes reviewed source/static configuration')
    receipt=root/'evidence/GIT_DEPLOYED.json'
    if (any(part.is_symlink() for part in (receipt,*receipt.parents) if part.is_relative_to(root))
            or not receipt.resolve(strict=False).is_relative_to(root.resolve()) or receipt.exists()):
        raise RuntimeError('refuse linked, escaping or existing deployment proof')
    for row in rows:
        relative=Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts:raise RuntimeError('unsafe member')
        p=source/relative;t=root/relative
        if (p.is_symlink() or not p.resolve(strict=True).is_relative_to(source.resolve())
                or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']):
            raise RuntimeError('Git source differs: '+row['path'])
        raw=subprocess.check_output(['git','-C',str(checkout),'show',commit+':'+PREFIX+'/'+row['path']])
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise RuntimeError('commit blob differs')
        # This operation may only redeploy byte-identical reviewed runtime inputs.
        if (any(part.is_symlink() for part in (t,*t.parents) if part.is_relative_to(root))
                or not t.resolve(strict=True).is_relative_to(root.resolve()) or t.stat().st_nlink!=1
                or sha(t)!=row['sha256']):
            raise RuntimeError('runtime differs from reviewed commit; new review needed: '+row['path'])
    for row in rows:
        p=source/row['path'];t=root/row['path']
        shutil.copyfile(p,t)
        if sha(t)!=row['sha256']:raise RuntimeError('deployed bytes differ')
    state={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commit':commit,
           'source_prefix':PREFIX,'checkout':str(checkout),'runtime_root':str(root),
           'files':rows,'source_manifest_sha256':SOURCE_SHA,
           'scope':'code deployment only; runtime approvals and booking remain independent',
           'new_model_requests':0,'grants_no_GPU':True}
    with receipt.open('x') as f:json.dump(state,f,indent=2)
    return state


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--checkout',type=Path,required=True)
    parser.add_argument('--commit',required=True);args=parser.parse_args()
    if not __debug__ or socket.gethostname()!='qjh000' or os.getuid()!=2147:
        raise RuntimeError('wrong target host/UID')
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from resource_guard import remaining_owned,idle
    from booking_window import require
    require(fresh=True)
    if remaining_owned():raise RuntimeError('owned task exists; no deployment')
    idle()
    print(json.dumps({'deployed':len(deploy(args.checkout,args.commit,ROOT)['files']),
                      'commit':args.commit,'new_model_requests':0}))
