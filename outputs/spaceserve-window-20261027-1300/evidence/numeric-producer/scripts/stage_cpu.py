"""Copy frozen SpaceServe inputs to a new root; no Torch/CUDA/model imports."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

SOURCE = Path('/var/tmp/boyjiang-spaceserve-revision-20261027')
TARGET = Path('/var/tmp/boyjiang-spaceserve-window-20261027-1300')
MEMBERS = ('envs/space', 'models/Qwen2-VL-7B-Instruct', 'src/SpaceServe', 'src/mysmctrl',
           'dataset', 'build/libsmctrl.so', 'build/service_sm_probe.so')


def copied_target(root, target):
    if not target.is_relative_to(root):
        return False
    relative = target.relative_to(root)
    if any(part in ('.git', '__pycache__') for part in relative.parts):
        return False
    return any(target == root/member or ((root/member).is_dir() and target.is_relative_to(root/member))
               for member in MEMBERS)


def inventory(root):
    rows = []
    for member in MEMBERS:
        start = root / member
        if not start.exists() or start.is_symlink():
            raise RuntimeError('source member absent or symlink: ' + member)
        paths = [start] if start.is_file() else sorted(start.rglob('*'))
        for path in paths:
            relative = path.relative_to(root).as_posix()
            if '.git' in path.relative_to(start).parts or '__pycache__' in path.parts:
                continue
            if path.is_symlink():
                link = os.readlink(path)
                resolved = path.resolve(strict=True)
                allowed_python = relative in {f'envs/space/bin/{name}' for name in ('python','python3','python3.10')}
                if not copied_target(root, resolved) and not (allowed_python and resolved.is_relative_to('/usr/bin')):
                    raise RuntimeError('external source symlink refused: ' + relative)
                row = {'path': relative, 'link': link}
                if copied_target(root, resolved):
                    row['target_member'] = resolved.relative_to(root).as_posix()
                else:
                    row['system_interpreter'] = str(resolved)
                rows.append(row)
            elif path.is_file():
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    while block := stream.read(1024**2):
                        digest.update(block)
                rows.append({'path':relative,'bytes':path.stat().st_size,'sha256':digest.hexdigest()})
            elif not path.is_dir():
                raise RuntimeError('special source member refused: ' + relative)
    return rows


def stage(approval):
    if not __debug__ or os.uname().nodename != 'qjh000' or os.getuid() != 2147:
        raise RuntimeError('requires unoptimized owned qjh000 CPU deployment')
    gate = json.loads(approval.read_text())
    actual = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if gate.get('scope') != 'Space-CPU-stage-only' or gate.get('passed') is not True or gate.get('stage_sha256') != actual:
        raise RuntimeError('current independent G2 stage approval missing')
    if TARGET.exists() or TARGET.is_symlink() or SOURCE.is_symlink():
        raise RuntimeError('refuse existing destination or indirect source')
    before = inventory(SOURCE)
    required = sum(row.get('bytes',0) for row in before)
    if shutil.disk_usage(TARGET.parent).free < required * 2 + 10 * 1024**3:
        raise RuntimeError('insufficient independent-copy disk budget')
    TARGET.mkdir(mode=0o700)
    for name in ('evidence','configs','scripts','analysis','results','logs','tmp','cache','build'):
        (TARGET/name).mkdir(exist_ok=True)
    (TARGET/'evidence/staging-started.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source':str(SOURCE),'destination':str(TARGET),'required_bytes':required,'grants_no_GPU':True},indent=2))
    for member in MEMBERS:
        source, target = SOURCE/member, TARGET/member
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source,target,symlinks=True,ignore=shutil.ignore_patterns('.git','__pycache__'),
                            copy_function=lambda a,b: subprocess.run(['cp','--reflink=auto','--preserve=mode,timestamps','--',a,b],check=True))
        else:
            subprocess.run(['cp','--reflink=auto','--preserve=mode,timestamps','--',str(source),str(target)],check=True)
    expected = []
    for row in before:
        updated = dict(row)
        if 'target_member' in row and os.path.isabs(row['link']):
            destination = TARGET/row['path']
            link = os.path.relpath(TARGET/row['target_member'], destination.parent)
            if not destination.is_symlink() or os.readlink(destination) != row['link']:
                raise RuntimeError('copied link identity differs before relocation')
            destination.unlink()
            destination.symlink_to(link, target_is_directory=(SOURCE/row['target_member']).is_dir())
            updated['link'] = link
        expected.append(updated)
    copied, after = inventory(TARGET), inventory(SOURCE)
    if copied != expected or after != before:
        raise RuntimeError('copy mismatch or original inputs changed; preserve failed staging')
    # Symlink resolution must remain new-root-local except the system interpreter.
    for row in copied:
        if 'sha256' in row:
            a, b = (SOURCE/row['path']).stat(), (TARGET/row['path']).stat()
            if (a.st_dev,a.st_ino) == (b.st_dev,b.st_ino):
                raise RuntimeError('shared writable hardlink refused')
    (TARGET/'configs/staged-inputs.json').write_text(json.dumps(before,indent=2))
    (TARGET/'configs/relocated-inputs.json').write_text(json.dumps(copied,indent=2))
    result = {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'files':len(before),
              'bytes':required,'source_unchanged':True,'destination_verified':True,'new_GPU_requests':0,
              'status':'CPU_STAGED_only; G2 runtime and actual G3 still required'}
    (TARGET/'evidence/CPU_STAGED.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--approval',type=Path,required=True)
    stage(parser.parse_args().approval)
