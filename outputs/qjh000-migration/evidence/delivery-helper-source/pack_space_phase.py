"""Archive immutable formal evidence only at its G4 pause or final completion."""
if not __debug__:
    raise RuntimeError('verification requires Python without -O')

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1024**2):
            value.update(block)
    return value.hexdigest()


def run(phase):
    root = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
    formal = root / 'results/formal'
    if phase == 'points':
        assert (formal / 'POINTS_READY_FOR_G4').is_file() and not (formal / 'G4_POINTS_APPROVED').exists()
        assert not (formal / 'rest').exists()
    else:
        assert (formal / 'COMPLETED').is_file() and (formal / 'G4_POINTS_APPROVED').read_bytes() == (formal / 'points-manifest.sha256').read_bytes()
    analysis = root / f'analysis-output/space-{phase}.json'
    result = json.loads(analysis.read_text())
    assert result['passed'] and result['phase'] == phase
    assert result['formal_requests'] == (1800 if phase == 'points' else 5400)
    assert result['warmup_requests'] == (120 if phase == 'points' else 360)
    assert len(result['cases']) == (6 if phase == 'points' else 18)
    log_snapshot = root / f'logs/formal-{phase}-launch.log'
    if log_snapshot.exists():
        raise RuntimeError('phase log snapshot already exists; refuse overwrite')
    shutil.copyfile(root / 'logs/formal-launch.log', log_snapshot)
    files = list(formal.rglob('*'))
    files += [analysis, log_snapshot]
    required = [root / 'evidence' / name for name in ['formal-approved-code.sha256', 'formal-code-check.txt', 'formal-background-check.txt', 'gpu-memory-capacity.json', 'boot-id.txt', 'G2_FORMAL_APPROVED', 'G3_MODEL_APPROVED', 'SM_EFFECTIVE', 'memory-sampler-fix-adoption.json', 'installed-freeze.txt', 'model-migration.json', 'asset-migration.json', 'gpus-before.csv', 'topology.txt', 'tmpfiles-config.txt', 'disk-before.txt', 'environment-READY', 'pip-check.txt', 'dependency-import.txt', 'formal.pid', 'points-paused-mps.json', 'points-paused-mps.status.txt']]
    required += [root / 'analysis-output' / name for name in ['points-current-code-check.txt', 'points-payload-check.txt']]
    if phase == 'all':
        owner = json.loads((root / 'evidence/mps-owner.json').read_text())
        initial = json.loads((formal / 'mps-start.json').read_text())
        assert owner['state'] == 'stopped' and owner['token'] == initial['token']
        owner_snapshot = root / 'evidence/formal-mps-owner-after.json'
        if owner_snapshot.exists():
            raise RuntimeError('final MPS snapshot already exists; preserve and inspect')
        shutil.copyfile(root / 'evidence/mps-owner.json', owner_snapshot)
        required += [owner_snapshot, root / 'evidence/g4-points-approval.json',
                     root / 'evidence/formal-final-background-check.txt',
                     root / 'evidence/formal-final-target-gpu-processes.csv',
                     root / 'evidence/formal-final-source-revisions.json',
                     root / 'evidence/formal-final-SpaceServe.diff',
                     root / 'analysis-output/pre-rest-current-code-check.txt',
                     root / 'analysis-output/full-current-code-check.txt']
    assert all(path.is_file() for path in required)
    files += required
    files = sorted(path for path in files if path.is_file())
    assert all(not path.is_symlink() and path.resolve().is_relative_to(root) for path in files)
    manifest = {str(path.relative_to(root)): {'bytes': path.stat().st_size, 'sha256': digest(path)} for path in files}
    assert len(manifest) == len(files)
    archive = root / f'results/formal-{phase}-20261023.tar.gz'
    if archive.exists():
        raise RuntimeError('archive already exists; never overwrite a collected phase')
    with tarfile.open(archive, 'x:gz') as output:
        for path in files:
            output.add(path, arcname=str(path.relative_to(root)), recursive=False)
        blob = json.dumps(manifest, indent=2).encode()
        item = tarfile.TarInfo('phase-transfer-manifest.json')
        item.size = len(blob)
        output.addfile(item, io.BytesIO(blob))
    assert all(path.stat().st_size == manifest[str(path.relative_to(root))]['bytes'] and digest(path) == manifest[str(path.relative_to(root))]['sha256'] for path in files)
    receipt = {'phase': phase, 'sha256': digest(archive), 'bytes': archive.stat().st_size, 'payload_files': len(files), 'path': str(archive), 'source_postpack_unchanged': True}
    (root / f'evidence/formal-{phase}-transfer.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['points', 'all'])
    run(parser.parse_args().phase)
