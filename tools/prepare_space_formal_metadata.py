"""CPU-only transfer of independently approved model proof and formal manifest freeze."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys

R = Path('/local/boyjiang/spaceserve/runs/space-20261031-0000')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def checked(path, size, expected):
    assert not path.is_symlink() and path.resolve(strict=True).is_relative_to(R)
    data = path.read_bytes()
    assert len(data) == size and digest(data) == expected, str(path)
    return data

def install(path, data):
    with path.open('xb') as stream:
        stream.write(data)
    return {'path': path.relative_to(R).as_posix(), 'bytes': len(data), 'sha256': digest(data)}

def main(payload):
    assert os.getuid() == 2147 and os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    review = json.loads(base64.b64decode(payload['review_json']))
    assert review['passed'] is True and review['blocking'] == 0
    assert review['producer_model_code_manifest_sha256'] == '707dee09621845e0cf460fcd90c7d619acda6896a57c30dd9d10ad5855b189cd'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == review['boot_id']
    assert review['gpu_uuids'] == ['GPU-c005197e-747d-2dc8-b77b-b123b41efd75']
    state = json.loads((R/'evidence/model-closed1-terminal.json').read_bytes())
    assert state['released'] and state['owned_processes'] == [] and state['MPS']['state'] == 'stopped'
    manifest_path = R/'configs/model-code-manifest.json'
    manifest_raw = checked(manifest_path, manifest_path.stat().st_size,
                           review['producer_model_code_manifest_sha256'])
    for row in json.loads(manifest_raw):
        checked(R/row['path'], row['bytes'], row['sha256'])
    sys.path[:0] = [str(R/'scripts'), str(R/'tools')]
    from resource_guard import remaining_owned
    assert remaining_owned() == []
    mapping = review['proposed_mapping']
    assert len(mapping) == 278
    targets = ['evidence/G3_MODEL_APPROVED.json', 'reviews/G3-model-actual.md',
               'evidence/model-producer-path-mapping.json', 'evidence/G3_MODEL_FORMAL_CONSUMER.json',
               'configs/formal-code-manifest.json', 'reviews/G3-model-formal-consumer.md']
    copies = [row for row in mapping if row['operation'] == 'copy-mutable-log-open-x']
    assert {row['source_path'] for row in copies} == {'logs/mps/control.log', 'logs/mps/server.log'}
    targets += [row['consumer_path'] for row in copies]
    assert len(set(targets)) == len(targets)
    assert all(not (R/name).exists() and not (R/name).is_symlink() for name in targets)
    for row in mapping:
        checked(R/row['source_path'], row['bytes'], row['sha256'])
    g3_json = base64.b64decode(payload['g3_json']); g3_md = base64.b64decode(payload['g3_md'])
    assert digest(g3_json) == review['source_model_G3_json_sha256']
    assert digest(g3_md) == review['source_model_G3_review_sha256']
    for row in copies:
        install(R/row['consumer_path'], checked(R/row['source_path'], row['bytes'], row['sha256']))
    bound = []
    for row in mapping:
        checked(R/row['consumer_path'], row['bytes'], row['sha256'])
        bound.append({'path': row['consumer_path'], 'bytes': row['bytes'], 'sha256': row['sha256']})
    bound += [install(R/'evidence/G3_MODEL_APPROVED.json', g3_json), install(R/'reviews/G3-model-actual.md', g3_md)]
    mapping_data = (json.dumps({'producer_model_code_manifest_sha256': review['producer_model_code_manifest_sha256'],
                    'source_model_G3_json_sha256': digest(g3_json), 'source_model_G3_md_sha256': digest(g3_md),
                    'mapping': mapping}, indent=2)+'\n').encode()
    bound.append(install(R/'evidence/model-producer-path-mapping.json', mapping_data))
    consumer_review = base64.b64decode(payload['review_md'])
    assert digest(consumer_review) == review['review_sha256']
    bound.append(install(R/'reviews/G3-model-formal-consumer.md', consumer_review))
    consumer = dict(passed=True, scope='Space-model-preflight-for-formal',
                    formal_data_approved=False, formal_execution_approved=False,
                    code_manifest_sha256=review['producer_model_code_manifest_sha256'],
                    boot_id=review['boot_id'], gpu_uuids=review['gpu_uuids'], bound_files=bound,
                    original_model_G3_review_sha256=review['source_model_G3_review_sha256'],
                    consumer_eligibility_review_sha256=review['review_sha256'])
    installed = install(R/'evidence/G3_MODEL_FORMAL_CONSUMER.json', (json.dumps(consumer, indent=2)+'\n').encode())
    from prepare_manifest import freeze
    frozen = freeze('formal')
    from resource_guard import code_identity, gate
    from model_guard import model_code
    assert code_identity(None) == '9580a769b640597ebd0b0f5f69276a26578470ec53e03fa0597fdd2d81ecccc3'
    assert model_code() == consumer['code_manifest_sha256']
    gate('G3_MODEL_FORMAL_CONSUMER.json', model_code())
    print(json.dumps({'consumer': installed, 'formal_manifest': frozen, 'copied_bytes': sum(row['bytes'] for row in copies),
                      'bound_files': len(bound), 'new_GPU_requests': 0, 'formal_started': False,
                      'G2_FORMAL_CODE_APPROVED_installed': False}))

if __name__ == '__main__':
    main(json.loads(sys.stdin.buffer.read()))
