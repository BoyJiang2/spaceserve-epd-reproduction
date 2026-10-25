import json, sys
import release_assets
from upload_buffered_asset import connection
if not __debug__:
    raise RuntimeError('verification requires Python without -O')
name = sys.argv[1]
assert name in {'reproduction.zip', 'reproduction-peer-diagnostic.zip', 'reproduction-review-pending.zip'}
base = release_assets.WORK
items = json.loads((base / 'assets-for-upload.json').read_text())
assert len(items) == 7
selected = [x for x in items if x['name'] == name]
assert len(selected) == 1
worker = base / 'historical-workers' / name
worker.mkdir(parents=True, exist_ok=True)
(worker / 'assets-for-upload.json').write_text(json.dumps(selected), encoding='utf-8')
release_assets.WORK = worker
release_assets.UPLOAD_CONNECTION = connection
release_assets.run('upload')
