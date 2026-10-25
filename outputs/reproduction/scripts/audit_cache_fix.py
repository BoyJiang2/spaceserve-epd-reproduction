"""Verify the paired RGB-cache correction without modifying raw measurements."""
import argparse
import hashlib
import io
import json
import pathlib
import tarfile
from PIL import Image
from audit_matrix import audit


def audit_host(root, host):
    directory = root / 'data/cache-fix' / host
    assert (directory / 'COMPLETED').exists()
    assert len((directory / 'gpu-processes-after.csv').read_text().splitlines()) == 1
    old = json.loads((root / 'evidence' / host / 'epd-runtime.json').read_text())
    assert (directory / 'boot-id.txt').read_text().strip() == old['boot_id']
    sources = json.loads((root / 'report/cache-fix-code-manifest.json').read_text())
    for item in sources:
        assert hashlib.sha256((directory / 'used-scripts' / item['file']).read_bytes()).hexdigest() == item['sha256'], item['file']
    expected = []
    with tarfile.open(root / 'data/dataset.tar.gz') as bundle:
        manifest_bytes = bundle.extractfile('dataset/manifest.json').read()
        manifest = json.loads(manifest_bytes)
        for item in manifest['images']:
            with Image.open(io.BytesIO(bundle.extractfile('dataset/' + item['file']).read())) as image:
                image = image.convert('RGB')
                expected.append({'file': item['file'], 'mode': image.mode, 'size': list(image.size),
                                 'rgb_sha256': hashlib.sha256(image.tobytes()).hexdigest()})
    assert len(expected) == 20
    matrices, correctness_count, snapshots = [], 0, 0
    suffix = '-qjh005' if host == 'qjh005' else ''
    for role in ('epd-h20', 'baseline-epd-h20'):
        matrix = directory / (role + suffix)
        assert {path.name for path in matrix.glob('images*-c*')} == {'images1-c1'}
        matrices.append(audit(matrix, low_load_only=True))
        runtime = json.loads((matrix / 'h20-runtime.json').read_text())
        assert len(runtime['workers']) == 3
        assert runtime['boot_id'] == old['boot_id'] and runtime['packages'] == old['packages']
        assert {worker['gpu_uuid'] for worker in runtime['workers']} == {worker['gpu_uuid'] for worker in old['workers']}
        expected_libraries = {path for worker in old['workers'] for path in worker['loaded_cublas_libraries']}
        assert all(len(worker['loaded_cublas_libraries']) == 2 and set(worker['loaded_cublas_libraries']) == expected_libraries for worker in runtime['workers'])
        config = json.loads((matrix / 'images1-c1/config.json').read_text())
        process_config = json.loads((matrix / 'runtime-config.json').read_text())
        server_pids = {server['pid'] for server in process_config['servers']}
        assert all(server['environment']['REPRO_RGB_MANIFEST'] for server in process_config['servers'])
        cache_pids = []
        for phase in ('before', 'after'):
            cache = json.loads((matrix / ('rgb-' + phase + '.json')).read_text())
            assert cache['passed'] and cache['inference_requests'] == 0
            records = cache['records']
            assert [record['url'] for record in records] == config['urls']
            assert len(records) == (3 if role.startswith('baseline') else 1)
            assert all(record['manifest_sha256'] == hashlib.sha256(manifest_bytes).hexdigest() and record['images'] == expected for record in records)
            pids = {record['pid'] for record in records}
            assert pids == server_pids
            cache_pids.append(pids)
            snapshots += len(records)
        assert cache_pids[0] == cache_pids[1]
        for label, count in (('standard', 7), ('c8', 8)):
            cases = json.loads((matrix / ('correctness-' + label + '.json')).read_text())
            assert len(cases) == count
            assert all(item['engine_check_passed'] and item['exact_processed_input_equal'] and item['exact_token_ids_equal'] for item in cases)
            assert all(item['target']['output_token_ids'] == item['reference']['output_token_ids'] for item in cases)
            assert all(item['target']['processed_prompt_token_ids'] == item['reference']['processed_prompt_token_ids'] for item in cases)
            assert len({item['target']['output'] for item in cases[:4]}) == 4
            correctness_count += len(cases)
    return {'host': host, 'passed': True, 'boot_id': old['boot_id'], 'formal_requests': 600,
            'warmup_requests': 40, 'correctness_cases': correctness_count,
            'cache_snapshots': snapshots, 'rgb_images_per_snapshot': 20,
            'scope': 'Baseline fixed correctness checks cover endpoint 0; RGB cache checks cover every serving endpoint',
            'matrices': matrices}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=pathlib.Path)
    args = parser.parse_args()
    result = [audit_host(args.root, host) for host in ('qjh003', 'qjh005')]
    (args.root / 'report/cache-fix-acceptance.json').write_text(json.dumps(result, indent=2))
    print(json.dumps([{key: value for key, value in row.items() if key != 'matrices'} for row in result], indent=2))
