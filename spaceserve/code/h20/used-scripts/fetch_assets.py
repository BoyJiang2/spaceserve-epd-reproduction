"""Transfer fixed code and completed public dependency caches, checking source SHA."""
import hashlib
import json
from pathlib import Path
import tarfile
import time
import urllib.error
import urllib.request

root = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
source = 'http://172.31.35.34:18670/'
target = root / 'tmp/migration-assets'
target.mkdir(parents=True, exist_ok=True)
records = []


def stream_digest(stream):
    value = hashlib.sha256()
    while data := stream.read(8 * 1024**2):
        value.update(data)
    return value.hexdigest()


def fetch(name):
    expected = urllib.request.urlopen(source + name + '.sha256', timeout=15).read().decode().split()[0]
    path = target / name
    sha = hashlib.sha256()
    if path.exists():
        with path.open('rb') as stream:
            while data := stream.read(8 * 1024**2):
                sha.update(data)
    else:
        with urllib.request.urlopen(source + name, timeout=120) as response, path.open('wb') as stream:
            while data := response.read(8 * 1024**2):
                stream.write(data)
                sha.update(data)
    if sha.hexdigest() != expected:
        raise RuntimeError('transfer SHA mismatch: ' + name)
    if name != 'uv':
        with tarfile.open(path) as archive:
            members = []
            for item in archive.getmembers():
                lexical = root / item.name
                destination = lexical.resolve()
                if not destination.is_relative_to(root):
                    raise RuntimeError('unsafe tar destination')
                if item.issym() and (Path(item.linkname).is_absolute() or not (lexical.parent / item.linkname).resolve().is_relative_to(root)):
                    raise RuntimeError('unsafe tar symlink')
                if item.islnk() and not (root / item.linkname).resolve().is_relative_to(root):
                    raise RuntimeError('unsafe tar hardlink')
                if not (item.isfile() or item.isdir() or item.issym() or item.islnk()):
                    raise RuntimeError('unexpected tar special file')
                if item.isfile() and destination.is_file() and destination.stat().st_size == item.size:
                    with destination.open('rb') as current, archive.extractfile(item) as incoming:
                        if stream_digest(current) == stream_digest(incoming):
                            continue  # Preserve identical read-only Git packs and completed cache payloads on retry.
                members.append(item)
            archive.extractall(root, members=members)
    else:
        destination = root / 'envs/uv'
        path.replace(destination)
        destination.chmod(0o700)
    record = {'asset': name, 'source_host': 'qjh005', 'bytes': path.stat().st_size if path.exists() else (root / 'envs/uv').stat().st_size, 'sha256': expected}
    records.append(record)
    print(json.dumps(record), flush=True)
    (root / 'evidence/asset-migration.json').write_text(json.dumps(records, indent=2))


for name in ['uv', 'space-source.tar.gz', 'dataset.tar.gz']:
    fetch(name)
for attempt in range(360):
    try:
        urllib.request.urlopen(source + 'cache-READY', timeout=5).close()
        break
    except (urllib.error.URLError, TimeoutError):
        time.sleep(5)
else:
    raise RuntimeError('completed dependency cache snapshot not available')
for name in ['old-uv-cache.tar', 'space-uv-cache.tar']:
    fetch(name)
(root / 'evidence/assets-READY').write_text('SHA-checked source, data, uv and completed cache snapshots\n')
