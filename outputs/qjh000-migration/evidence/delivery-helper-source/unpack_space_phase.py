"""Verify archive/CRC and every payload hash before copying measured evidence."""
if not __debug__:
    raise RuntimeError('verification requires Python without -O')

import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile


def digest_stream(source):
    value = hashlib.sha256()
    while block := source.read(1024**2):
        value.update(block)
    return value.hexdigest()


def destination_for(target, name):
    relative = PurePosixPath(name)
    if ('\\' in name or ':' in name or '\x00' in name or not relative.parts
            or relative.is_absolute() or '..' in relative.parts or relative.as_posix() != name):
        raise RuntimeError('unsafe destination: ' + repr(name))
    destination = target.joinpath(*relative.parts)
    if not destination.resolve().is_relative_to(target.resolve()):
        raise RuntimeError('destination escapes target: ' + repr(name))
    return destination


def run(phase):
    root = Path(__file__).resolve().parents[1]
    target = root / 'outputs/qjh000-migration'
    archive_path = root / f'work/formal-{phase}-20261023.tar.gz'
    receipt = json.loads((target / f'evidence/formal-{phase}-transfer.json').read_text())
    with archive_path.open('rb') as source:
        assert digest_stream(source) == receipt['sha256']
    assert archive_path.stat().st_size == receipt['bytes']
    with gzip.open(archive_path, 'rb') as source:
        while source.read(1024**2):
            pass
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        assert all(item.isfile() for item in members)
        names = [item.name for item in members]
        assert len(names) == len(set(names))
        manifest = json.loads(archive.extractfile('phase-transfer-manifest.json').read())
        assert set(names) == set(manifest) | {'phase-transfer-manifest.json'}
        assert len(manifest) == receipt['payload_files']
        for item in members:
            if item.name == 'phase-transfer-manifest.json':
                continue
            relative = PurePosixPath(item.name)
            if relative.is_absolute() or '..' in relative.parts or not relative.parts or relative.parts[0] not in {'results', 'logs', 'evidence', 'analysis-output'}:
                raise RuntimeError('unexpected transfer member: ' + item.name)
            destination_for(target, item.name)
            expected = manifest[item.name]
            with archive.extractfile(item) as source:
                assert item.size == expected['bytes'] and digest_stream(source) == expected['sha256']
        for item in members:
            if item.name == 'phase-transfer-manifest.json':
                continue
            destination = destination_for(target, item.name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination = destination_for(target, item.name)
            if destination.exists():
                with destination.open('rb') as source:
                    existing = digest_stream(source)
                if existing != manifest[item.name]['sha256']:
                    raise RuntimeError('refuse to overwrite different local evidence: ' + str(destination))
                continue
            with archive.extractfile(item) as source, destination.open('xb') as output:
                shutil.copyfileobj(source, output)
        destination_for(target, 'report').mkdir(exist_ok=True)
        analysis_source = destination_for(target, f'analysis-output/space-{phase}.json')
        analysis_target = destination_for(target, f'report/space-{phase}.json')
        if analysis_target.exists() and analysis_target.read_bytes() != analysis_source.read_bytes():
            raise RuntimeError('refuse to overwrite different analysis JSON')
        analysis_target.write_bytes(analysis_source.read_bytes())
        destination_for(target, f'evidence/formal-{phase}-payload-sha.json').write_text(json.dumps(manifest, indent=2))
    result = {**receipt, 'local_sha_crc_and_payloads_verified': True}
    destination_for(target, f'evidence/formal-{phase}-local-integrity.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['points', 'all'])
    run(parser.parse_args().phase)
