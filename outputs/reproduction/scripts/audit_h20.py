"""Audit both H20 acceptance chains using archived native and model evidence."""
import argparse
import json
import pathlib
import re
from audit_matrix import audit


def audit_host(root, host):
    evidence = root / 'evidence' / host
    source = json.loads((evidence / 'native-source-manifest.json').read_text())
    assert source['commit'] == '9b111f710dfb4724072b603d626a1e4dad93ef1f'
    assert source['native_sources_unmodified'] and len(source['files']) >= 3
    assert all(len(item['sha256']) == 64 and len(item['git_blob']) == 40 for item in source['files'])
    expected_model = json.loads((root / 'configs/minicpm-model-manifest.json').read_text())
    actual_model = json.loads((evidence / 'model-manifest.json').read_text())
    assert [(item['name'], item['bytes'], item['sha256']) for item in expected_model['files']] == [(item['name'], item['bytes'], item['sha256']) for item in actual_model['files']]
    preflights = list(evidence.glob('preflight-*'))
    assert len(preflights) == 1
    preflight = preflights[0]
    assert (preflight / 'PASSED').exists()
    platform = json.loads((preflight / 'platform.json').read_text())
    assert not platform['unsupported_bare_metal_dma_iommu']
    peer = [json.loads(path.read_text()) for path in preflight.glob('cuda-peer-*.json')]
    assert {item['cuda_visible_devices'] for item in peer} == {'0,1', '1,0', '0,2', '2,0', '1,2', '2,1'}
    assert all(item['bytes'] == 16777216 and item['source_validated'] and item['data_equal'] and item['source_sha256'] == item['destination_sha256'] for item in peer)
    native = [json.loads(path.read_text()) for path in preflight.glob('kv-*.json')]
    assert {(item['source_gpu'], item['destination_gpu'], item['cache_shape'][2]) for item in native} == {(source, destination, blocks) for source in range(3) for destination in range(3) if source != destination for blocks in (2048, 24728)}
    assert all(item['source_validation']['source_validated'] and len(item['records']) == 3 and all(record['data_equal'] and record['gpu_ms'] > 0 for record in item['records']) for item in native)
    actual = json.loads((evidence / 'kv-actual-cache.json').read_text())
    sizes = set(map(int, re.findall(r'Num GPU Blocks: (\d+)', (evidence / 'logs/epd-epoch2.log').read_text())))
    assert sizes == {actual['cache_shape'][2]} and actual['source_validation']['source_validated']
    assert len(actual['records']) == 3 and all(record['data_equal'] for record in actual['records'])
    embedding = json.loads((evidence / 'embedding-ipc.json').read_text())
    assert (embedding['source_gpu'], embedding['destination_gpu'], embedding['cache_shape']) == (0, 1, [16, 64, 3584])
    assert embedding['source_validated'] and len(embedding['records']) == 3 and all(item['data_equal'] for item in embedding['records'])
    blas = [json.loads(line) for line in (evidence / 'blas-after.jsonl').read_text().splitlines()]
    assert blas[0]['cublas'] == '12.4.5.8' and sum(item.get('data_equal', False) for item in blas) == 4
    snapshots = [json.loads((evidence / name).read_text()) for name in ('epd-runtime.json', 'baseline-runtime.json')]
    assert all(item['boot_id'] == platform['boot_id'] and item['packages']['nvidia-cublas-cu12'] == '12.4.5.8' for item in snapshots)
    expected_uuids = {item['uuid'] for item in platform['devices']}
    assert all(len(item['workers']) == 3 and {worker['gpu_uuid'] for worker in item['workers']} == expected_uuids for item in snapshots)
    assert all(len(worker['loaded_cublas_libraries']) == 2 for item in snapshots for worker in item['workers'])
    correctness = []
    for label in ('baseline-reference', 'baseline-reference-c8', 'epd-epoch1', 'epd-epoch1-c8', 'epd-epoch2', 'epd-epoch2-c8'):
        records = json.loads((evidence / (label + '.json')).read_text())
        assert len(records) == (8 if label.endswith('-c8') else 7)
        assert all(item['engine_check_passed'] and item['exact_token_ids_equal'] and item['exact_processed_input_equal'] for item in records), label
        assert len({item['target']['output'] for item in records[:4]}) == 4
        correctness.extend(records)
    suffix = '-qjh005' if host == 'qjh005' else ''
    matrices = [audit(root / 'data/raw' / host / (role + suffix), host == 'qjh005') for role in ('epd-h20', 'baseline-epd-h20')]
    assert (evidence / (host + '-matrices-COMPLETED')).exists()
    return {'host': host, 'boot_id': platform['boot_id'], 'passed': True,
            'peer_directions': len(peer), 'native_kv_copies': sum(len(item['records']) for item in native) + 3,
            'actual_kv_cache_blocks': actual['cache_shape'][2],
            'embedding_copies': 3, 'blas_shapes': 4, 'correctness_cases': len(correctness),
            'formal_requests': sum(item['measured_requests'] for item in matrices), 'matrices': matrices}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=pathlib.Path)
    args = parser.parse_args()
    result = [audit_host(args.root, host) for host in ('qjh003', 'qjh005')]
    (args.root / 'report/h20-acceptance.json').write_text(json.dumps(result, indent=2))
    print(json.dumps([{key: value for key, value in host.items() if key != 'matrices'} for host in result], indent=2))
