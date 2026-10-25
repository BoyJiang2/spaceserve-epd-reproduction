"""Inventory public wheel metadata in the user's existing pip HTTP cache; read-only."""
from pathlib import Path
import json
import zipfile

root = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
records = []
for path in Path('/home/boyjiang/.cache/pip').rglob('*'):
    if not path.is_file() or path.stat().st_size < 100000 or not zipfile.is_zipfile(path):
        continue
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith('.dist-info/METADATA')]
        if len(names) != 1:
            continue
        metadata = archive.read(names[0]).decode('utf-8')
        name, version = [next(line.split(': ', 1)[1] for line in metadata.splitlines() if line.startswith(key + ': ')) for key in ['Name', 'Version']]
        wheel = archive.read(names[0].rsplit('/', 1)[0] + '/WHEEL').decode('utf-8')
        records.append({'name': name, 'version': version, 'body_path': str(path), 'bytes': path.stat().st_size,
                        'tags': [line[5:] for line in wheel.splitlines() if line.startswith('Tag: ')]})
(root / 'evidence/existing-pip-wheel-inventory.json').write_text(json.dumps(records, indent=2))
print(json.dumps({'wheels': len(records), 'packages': [(item['name'], item['version']) for item in records]}, indent=2))
