"""Verify shared assets and freeze small code once per actual run; no model/GPU action."""
import hashlib
import json
import os
from pathlib import Path
import socket
import shutil
import sys
import time

MEMBERS = ('envs/space','models/Qwen2-VL-7B-Instruct','src/SpaceServe','src/mysmctrl',
           'dataset','build/libsmctrl.so','build/service_sm_probe.so')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024**2): digest.update(block)
    return digest.hexdigest()


def copied_target(root, target):
    """Only members included in the asset inventory may be internal link targets."""
    try: relative = target.relative_to(root)
    except ValueError: return False
    return ('.git' not in relative.parts and '__pycache__' not in relative.parts
            and any(relative == Path(member) or Path(member) in relative.parents for member in MEMBERS))


def inventory(root):
    root = Path(root)
    if root.is_symlink(): raise ValueError('Asset root must be a real project directory')
    rows = []
    for member in MEMBERS:
        start = root/member
        for ancestor in (start,*start.parents):
            if ancestor.is_symlink(): raise ValueError('Linked top-level asset ancestry refused: '+member)
            if ancestor == root: break
        if not start.exists() or start.is_symlink(): raise ValueError('Missing/linked top-level asset: '+member)
        for path in ([start] if start.is_file() else sorted(start.rglob('*'))):
            relative = path.relative_to(root).as_posix()
            if '.git' in path.relative_to(start).parts or '__pycache__' in path.parts: continue
            if path.lstat().st_uid != os.getuid(): raise ValueError('Foreign-owned project asset: '+relative)
            if path.is_symlink():
                target = path.resolve(strict=True)
                interpreter = relative in {f'envs/space/bin/{name}' for name in ('python','python3','python3.10')}
                if not copied_target(root.resolve(), target) and not (interpreter and target.is_relative_to('/usr/bin')):
                    raise ValueError('Asset link escapes project: '+relative)
                row = {'path':relative,'link':os.readlink(path)}
                if target.is_relative_to(root.resolve()): row['target_member']=target.relative_to(root.resolve()).as_posix()
                else: row['system_interpreter']=str(target)
                rows.append(row)
            elif path.is_file(): rows.append({'path':relative,'bytes':path.stat().st_size,'sha256':sha(path)})
            elif not path.is_dir(): raise ValueError('Special asset file refused')
    return rows


def prepare(layout, commit, configuration):
    if (not __debug__ or socket.gethostname()!=layout.config['host'] or os.getuid()!=layout.config['uid']
            or not layout.config.get('run_id')):
        raise ValueError('CPU prepare requires the exact host/UID and a real independent run ID')
    root, assets = layout.run_root, layout.assets_root
    for path in (root, *root.parents, assets, *assets.parents):
        if path.is_symlink(): raise ValueError('Linked project/run ancestry refused')
        if path.exists() and path.is_relative_to(layout.project_root) and path.stat().st_uid != os.getuid():
            raise ValueError('Foreign-owned project/run ancestry refused')
    if root.exists(): raise ValueError('Do not overwrite or retry an existing run')
    recorded = assets/'manifest.json'
    expected = json.loads(recorded.read_text())
    before = inventory(assets)
    if expected != before: raise ValueError('Shared assets differ from the migration manifest')
    pins = json.loads((layout.code_root/'configs/asset-content-pins.json').read_text())
    by_path = {row['path']:row for row in before}
    protected = ('models/','dataset/','src/SpaceServe/','src/mysmctrl/','build/',
                 'envs/space/lib/python3.10/site-packages/vllm/')
    actual = [row for row in before if row['path'].startswith(protected)]
    if {row['path']:row for row in actual} != {row['path']:row for row in pins}:
        raise ValueError('Model/data/framework/compiled content differs from the approved assets')
    root.mkdir(mode=0o700,parents=True)
    for name in ('configs','evidence','scripts','tools','results','logs','tmp','analysis','build'):
        (root/name).mkdir()
    with (root/'evidence/preparation-started.json').open('x') as stream:
        json.dump({'observed_ms':int(time.time()*1000),'source_commit':commit,
            'asset_manifest_sha256':sha(recorded),'source_configuration_sha256':sha(Path(configuration)),
            'scope':'CPU preparation only; preserve this partial run on failure'},stream,indent=2)
    sys.path.insert(0,str(layout.code_root/'tools'))
    from deploy_commit_cpu import deploy
    deployment = deploy(layout.checkout,commit,root)
    # Only these small compiled experiment libraries are frozen, never models or environments.
    for name in ('build/libsmctrl.so','build/service_sm_probe.so'):
        shutil.copyfile(assets/name,root/name)
        if sha(root/name)!=by_path[name]['sha256']: raise ValueError('Frozen binary differs from assets')
    # Asset files are never copied into this run.
    with (root/'configs/asset-inputs.json').open('x') as stream: json.dump(before,stream,indent=2)
    frozen = {**layout.config,'source_commit':commit,
        'source_manifest_sha256':deployment['source_manifest_sha256'],
        'asset_manifest_sha256':sha(root/'configs/asset-inputs.json')}
    with (root/'configs/project.json').open('x') as stream: json.dump(frozen,stream,indent=2)
    if inventory(assets)!=before: raise ValueError('Assets changed during CPU code preparation')
    result = {'observed_ms':int(time.time()*1000),'status':'CPU_PREPARED_only; actual_GPU_Gates_still_required',
        'commit':commit,'files':len(before),'bytes':sum(row.get('bytes',0) for row in before),
        'source_unchanged':True,'destination_verified':True,'shared_assets':True,
        'asset_manifest_sha256':frozen['asset_manifest_sha256'],'source_manifest_sha256':deployment['source_manifest_sha256'],
        'new_GPU_requests':0,'grants_no_GPU':True}
    with (root/'evidence/CPU_STAGED.json').open('x') as stream: json.dump(result,stream,indent=2)
    print(json.dumps(result))
    return result
