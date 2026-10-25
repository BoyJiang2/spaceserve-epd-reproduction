"""Stage the complete CP310 cache separately from the active UV cache."""
import hashlib
import json
from pathlib import Path
import tarfile
import time
import urllib.request

ROOT = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
SOURCE = 'http://127.0.0.1:18673/'  # Windows SSH relay; source HTTP is also localhost only.
EXPECTED = {
    'cache.tar.gz': '31943c861ed283ad6e95f87ef53d954d84526c8f3777c91293d40303626b0e9f',
    'uv': 'b65f23a420c4acc96427efb30e5ed9bc0f7e25d2d712000f6ede77c1a0de5f46',
}


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(8 * 1024**2):
            sha.update(data)
    return sha.hexdigest()


def main():
    target = ROOT / 'tmp/sapphire-cache'
    target.mkdir(exist_ok=True)
    records = []
    for name, expected in EXPECTED.items():
        path = target / name
        start = time.monotonic()
        if not path.exists():
            partial = path.with_suffix(path.suffix + '.partial')
            with urllib.request.urlopen(SOURCE + name, timeout=180) as incoming, partial.open('wb') as outgoing:
                while data := incoming.read(8 * 1024**2):
                    outgoing.write(data)
            if digest(partial) != expected:
                raise RuntimeError('transferred source digest differs: ' + name)
            partial.replace(path)
        if digest(path) != expected:
            raise RuntimeError('cached source digest differs: ' + name)
        records.append({'source_host': 'sapphire1', 'source_root': '/mnt/data/boyjiang-spaceserve-epd',
                        'asset': name, 'sha256': expected, 'bytes': path.stat().st_size,
                        'verified_after_s': time.monotonic() - start})
        print(json.dumps(records[-1]), flush=True)
    destination = ROOT / 'cache-sapphire'
    destination.mkdir(exist_ok=True)
    with tarfile.open(target / 'cache.tar.gz') as archive:
        for item in archive.getmembers():
            lexical = destination / item.name
            if not lexical.resolve().is_relative_to(destination):
                raise RuntimeError('unsafe cache member')
            if item.issym() and (Path(item.linkname).is_absolute() or not (lexical.parent / item.linkname).resolve().is_relative_to(destination)):
                raise RuntimeError('unsafe cache symlink')
            if item.islnk() and not (destination / item.linkname).resolve().is_relative_to(destination):
                raise RuntimeError('unsafe cache hardlink')
            if not (item.isfile() or item.isdir() or item.issym() or item.islnk()):
                raise RuntimeError('unexpected special cache member')
        archive.extractall(destination)
    tool = ROOT / 'envs/uv-sapphire'
    tool.write_bytes((target / 'uv').read_bytes())
    tool.chmod(0o700)
    (ROOT / 'evidence/sapphire-cache-migration.json').write_text(json.dumps(records, indent=2))
    (ROOT / 'evidence/sapphire-cache-READY').write_text('separate cache; SHA checked; UV 0.12.5\n')
    print('Separate complete cache staged; no active environment/cache changed', flush=True)


if __name__ == '__main__':
    main()
