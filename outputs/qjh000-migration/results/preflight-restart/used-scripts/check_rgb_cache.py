"""Check cache contents through a metadata route; never submit inference."""
import argparse
import datetime
import json
import pathlib
import urllib.request
from PIL import Image
from rgb_cache import cache_snapshot, dataset_paths

parser = argparse.ArgumentParser()
parser.add_argument('--urls', nargs='+', required=True)
parser.add_argument('--dataset', type=pathlib.Path, required=True)
parser.add_argument('--output', type=pathlib.Path, required=True)
args = parser.parse_args()
manifest = args.dataset / 'manifest.json'
expected_images = {}
for path in dataset_paths(manifest):
    with Image.open(path) as image:
        expected_images[path.name] = image.convert('RGB')
expected = cache_snapshot(manifest, expected_images)
records = []
for url in args.urls:
    with urllib.request.urlopen(url + '/repro/rgb-cache', timeout=20) as response:
        actual = json.load(response)
    assert actual['manifest_sha256'] == expected['manifest_sha256'], url
    assert actual['images'] == expected['images'], url
    records.append({'url': url, **actual})
result = {'passed': True, 'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'inference_requests': 0, 'records': records}
assert len({row['pid'] for row in records}) == len(records)
args.output.write_text(json.dumps(result, indent=2))
print(json.dumps({'passed': True, 'services': len(records), 'images_per_service': 20, 'inference_requests': 0}))
