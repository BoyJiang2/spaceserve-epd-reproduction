"""Copy the already pinned public 7B files over the private network, checking bytes/SHA."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import urllib.request

root = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
source = 'http://172.31.35.34:18670/model/'
manifest_bytes = urllib.request.urlopen(source + 'download_manifest.json', timeout=15).read()
manifest = json.loads(manifest_bytes)
expected = json.loads((root / 'configs/qwen7b-model-original-pin.json').read_text())
if manifest['repo'] != 'Qwen/Qwen2-VL-7B-Instruct' or [(item['name'], item['bytes'], item['sha256']) for item in manifest['files']] != [(item['name'], item['bytes'], item['sha256']) for item in expected['files']]:
    raise RuntimeError('source model differs from user-approved pin')
target = root / 'models/Qwen2-VL-7B-Instruct'
target.mkdir(exist_ok=True)


def copy(item):
    path = target / item['name']
    if not path.resolve().is_relative_to(target.resolve()):
        raise RuntimeError('unexpected model destination')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with path.open('rb') as stream:
            sha = hashlib.sha256()
            while data := stream.read(8 * 1024**2):
                sha.update(data)
        if path.stat().st_size == item['bytes'] and sha.hexdigest() == item['sha256']:
            return item
        raise RuntimeError('existing model file differs; preserve and inspect')
    partial = path.with_name(path.name + '.partial')
    sha, size = hashlib.sha256(), 0
    with urllib.request.urlopen(source + item['name'], timeout=120) as response, partial.open('wb') as stream:
        while data := response.read(8 * 1024**2):
            stream.write(data)
            sha.update(data)
            size += len(data)
    if size != item['bytes'] or sha.hexdigest() != item['sha256']:
        raise RuntimeError('model copy failed integrity: ' + item['name'])
    partial.replace(path)
    print(json.dumps({'file': item['name'], 'bytes': size, 'sha256': sha.hexdigest()}), flush=True)
    return item


started = time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(copy, manifest['files']))
(target / 'download_manifest.json').write_bytes(manifest_bytes)
(root / 'evidence/model-migration.json').write_text(json.dumps({'passed': True, 'source_host': 'qjh005',
    'source_root': '/local/boyjiang/spaceserve-h20-7b-20261023/models/Qwen2-VL-7B-Instruct', 'target_host': 'qjh000',
    'target': str(target), 'files': manifest['files'], 'elapsed_s': time.monotonic() - started}, indent=2))
print(json.dumps({'passed': True, 'files': len(manifest['files']), 'elapsed_s': time.monotonic() - started}), flush=True)
