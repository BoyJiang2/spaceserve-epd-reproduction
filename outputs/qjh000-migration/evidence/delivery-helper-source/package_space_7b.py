"""Package the completed SpaceServe batch, preserving every earlier sealed batch."""
if not __debug__:
    raise RuntimeError('verification requires Python without -O')

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / 'outputs/qjh000-migration'
SEALED = [('reproduction', 969, 'reproduction-h20.zip', '3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38'),
          ('epd-followup', 58, 'epd-followup.zip', 'd155537944ea9095f2b1eecbd3780f57a611100aa9701b5e5617f4137d38a3f9'),
          ('epd-profile-a', 479, 'epd-profile-a.zip', 'f7a35baf1c7e0e13ea1b1df65d4436efff199c5b21c876198289fbbfb2a1c094')]


def digest(source):
    value = hashlib.sha256()
    while block := source.read(1024**2):
        value.update(block)
    return value.hexdigest()


def sha(path):
    with path.open('rb') as source:
        return digest(source)


def payloads(folder):
    return sorted(path for path in folder.rglob('*') if path.is_file() and path != folder / 'SHA256SUMS'
                  and '__pycache__' not in path.parts and path.suffix != '.pyc')


def manifest_records(text, name):
    records = {}
    for line in text.splitlines():
        expected, filename = line.split('  ', 1)
        relative = PurePosixPath(filename)
        if relative.parts[0] == name:
            relative = PurePosixPath(*relative.parts[1:])
        assert relative.parts and not relative.is_absolute() and '..' not in relative.parts
        assert relative.as_posix() not in records
        records[relative.as_posix()] = expected
    return records


def verify_sealed_batch(folder, archive_path, expected_count, expected_sha):
    assert sha(archive_path) == expected_sha
    records = manifest_records((folder / 'SHA256SUMS').read_text(encoding='utf-8'), folder.name)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        manifests = [name for name in ['SHA256SUMS', folder.name + '/SHA256SUMS'] if name in names]
        assert len(manifests) == 1 and len(names) == len(set(names))
        manifest_name = manifests[0]
        prefix = manifest_name.removesuffix('SHA256SUMS')
        fixed_records = manifest_records(archive.read(manifest_name).decode('utf-8'), folder.name)
        assert records == fixed_records and len(records) == expected_count
        assert set(names) == {prefix + name for name in records} | {manifest_name}
        for name, expected in records.items():
            with archive.open(prefix + name) as source:
                assert digest(source) == expected
    current = {path.relative_to(folder).as_posix(): path for path in payloads(folder)}
    assert set(current) == set(records)
    assert all(not path.is_symlink() and sha(path) == records[name] for name, path in current.items())


def verify_sealed():
    result = []
    for name, expected_count, zip_name, expected_sha in SEALED:
        verify_sealed_batch(ROOT / 'outputs' / name, ROOT / 'outputs' / zip_name, expected_count, expected_sha)
        result.append({'directory': name, 'payload_files': expected_count, 'zip': zip_name, 'fixed_zip_sha256': expected_sha, 'directory_bound_to_fixed_zip_manifest_and_payloads': True, 'passed': True})
    return result


def run(kind):
    status = json.loads((DELIVERY / 'status.json').read_text(encoding='utf-8'))
    result = json.loads((DELIVERY / 'report/space-all.json').read_text())
    assert result['passed'] and result['formal_requests'] == 5400 and result['warmup_requests'] == 360 and len(result['cases']) == 18
    assert (DELIVERY / 'results/formal/COMPLETED').is_file()
    assert status['gates']['G4_full'].startswith('APPROVE')
    if kind == 'final':
        assert status['gates']['G5'].startswith('APPROVE')
    sealed = verify_sealed()
    files = payloads(DELIVERY)
    assert all(not path.is_symlink() for path in files)
    hashes = {path.relative_to(DELIVERY).as_posix(): sha(path) for path in files}
    manifest = DELIVERY / 'SHA256SUMS'
    manifest.write_text(''.join(value + '  ' + name + '\n' for name, value in hashes.items()), encoding='utf-8')
    stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    temporary = ROOT / 'work' / f'space-7b-{kind}-{stamp}.zip'
    assert not temporary.exists()
    prefix = DELIVERY.name + '/'
    with zipfile.ZipFile(temporary, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True, strict_timestamps=False) as archive:
        for path in [*files, manifest]:
            compression = zipfile.ZIP_STORED if path.suffix in {'.gz', '.so'} else zipfile.ZIP_DEFLATED
            archive.write(path, prefix + path.relative_to(DELIVERY).as_posix(), compress_type=compression)
    with zipfile.ZipFile(temporary) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) and set(names) == {prefix + name for name in hashes} | {prefix + 'SHA256SUMS'}
        for name, expected in hashes.items():
            with archive.open(prefix + name) as source:
                assert digest(source) == expected  # Full reads also validate each entry's CRC.
        assert archive.read(prefix + 'SHA256SUMS') == manifest.read_bytes()
    assert {path.relative_to(DELIVERY).as_posix(): sha(path) for path in payloads(DELIVERY)} == hashes
    final_path = ROOT / 'outputs/spaceserve-7b-h20.zip' if kind == 'final' else temporary
    if kind == 'final':
        assert final_path.parent.resolve() == (ROOT / 'outputs').resolve() and not final_path.exists()
        temporary.replace(final_path)
    receipt = {'kind': kind, 'passed': True, 'archive': str(final_path), 'bytes': final_path.stat().st_size, 'sha256': sha(final_path), 'payload_files': len(hashes), 'zip_entries': len(hashes) + 1, 'source_and_archive_all_payloads_match': True, 'full_entry_crc_reads_passed': True, 'sealed_batches': sealed}
    receipt_path = ROOT / 'outputs/spaceserve-7b-h20-integrity.json' if kind == 'final' else temporary.with_suffix('.integrity.json')
    assert not receipt_path.exists()
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    if kind == 'final':
        (ROOT / 'outputs/spaceserve-7b-h20.zip.sha256').write_text(receipt['sha256'] + '  spaceserve-7b-h20.zip\n', encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['candidate', 'final'])
    run(parser.parse_args().kind)
