"""Materialize actual independent approvals after validating current CPU/resource evidence."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path('/var/tmp/boyjiang-epd-revision-20261026')
sys.path.insert(0, str(ROOT / 'scripts'))
from resource_guard import UUIDS, idle, remaining_owned, sha
from booking_window import require
from run_cells import host_snapshot

CODE = '9bb1a92b9864bb9ccd837a9258d7079f0dc98d559ab305c906d4bed6d27d4bbd'
assert Path(os.environ['EXP_ROOT']).resolve() == ROOT
assert sha(ROOT / 'configs/code-manifest.json') == CODE
for row in json.loads((ROOT / 'configs/code-manifest.json').read_text()):
    assert sha(ROOT / row['path']) == row['sha256'], row['path']
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == '838160b3-4eb7-4a24-accc-f7720e0ac78a'
cpu = json.loads((ROOT / 'evidence/C-off-target-cpu-passed.json').read_text())
assert cpu['passed'] and cpu['code_manifest_sha256'] == CODE
assert cpu['cpu_tests'] == 24 and cpu['real_alarm_tests'] == 1
assert cpu['raw_log_sha256'] == sha(ROOT / 'evidence/C-off-target-cpu.log')
require(fresh=True)
idle()
assert not remaining_owned()
host_snapshot(ROOT / 'evidence/post-model-fresh-before-C.json')
checkpoint = json.loads((ROOT / 'evidence/G3_PREFLIGHT_CHECKPOINT_APPROVED.json').read_text())
checkpoint_files = []
mapping = []
for row in checkpoint['bound_files']:
    preserved = 'evidence/model-producer-code-manifest.json' if row['path'] == 'configs/code-manifest.json' else row['path']
    path = ROOT / preserved
    assert sha(path) == row['sha256'], row['path']
    checkpoint_files.append(path)
    mapping.append({'original_path': row['path'], 'preserved_path': preserved, 'sha256': row['sha256']})
result = json.loads((ROOT / 'results/preflight-models/result.json').read_text())
assert result['passed'] and result['target_requests'] == 272 and result['reference_requests'] == 17
assert result['code_manifest_sha256'] == '49c2bc3feca347f0bfb5e2633cbc2e09fd30e4c747ee4a2d90edb63469466c2d'
assert not (ROOT / 'results/overhead').exists()
rows = json.loads((ROOT / 'configs/C-schedule.json').read_text())['rows']
assert len(rows) == 60 and all(row['mode'] == 'off' for row in rows)

def bindings(paths):
    return [{'path': str(path.relative_to(ROOT)), 'sha256': sha(path)} for path in sorted(set(paths))]

def save(name, state):
    with (ROOT / 'evidence' / name).open('x') as output:
        json.dump(state, output, indent=2)

common = {'passed': True, 'scope': 'C-off-only', 'code_manifest_sha256': CODE,
          'boot_id': result['boot_id'], 'gpu_uuids': UUIDS,
          'created_at_unix': time.time(), 'allowed_actions': ['performance'],
          'model_correctness_passed': True, 'lite_observation_approved': False,
          'lite_observation_passed': False, 'B_status': 'not_run_observation_preflight_failed',
          'formal_requests': 6000, 'warmup_requests': 1200,
          'shared_host_relative_observation_only': True,
          'numeric_producer_sha256': '710effcab0ecb34a563c826cfcc7ceee41cefe07c074b11c660e54333c00a6d0',
          'model_producer_sha256': result['code_manifest_sha256']}
review_paths = list((ROOT / 'evidence/reviews-C-off').glob('*.md'))
assert len(review_paths) == 6
save('C_SCOPE_APPROVED.json', {**common, 'independent_G1_G4': '/root/profile_plan_review',
    'bound_files': bindings(review_paths + [ROOT / 'configs/C-schedule.json', ROOT / 'evidence/C-off-fallback-code-delta.json'])})
save('checkpoint-90-consumer-mapping.json', {'reason': 'Versioned consumer manifest; original checkpoint remains unchanged',
    'producer_sha256': result['code_manifest_sha256'], 'consumer_sha256': CODE, 'files': mapping})
files = checkpoint_files
for folder in ('results/preflight-models', 'results/preflight-models-attempt0', 'results/preflight-numeric'):
    files.extend(path for path in (ROOT / folder).rglob('*') if path.is_file())
for name in ('G3_PREFLIGHT_CHECKPOINT_APPROVED.json', 'G3_NUMERICAL_APPROVED.json',
             'numeric-producer-code-manifest.json', 'model-producer-code-manifest.json',
             'model-attempt0-code-manifest.json', 'pre-resume-code-manifest.json',
             'C-off-fallback-code-delta.json', 'C-off-target-cpu-passed.json', 'C-off-target-cpu.log',
             'checkpoint-90-consumer-mapping.json',
             'frozen-request-protocol.json', 'checkpoint-resume-controller.log',
             'model-preflight-recheck-controller.log', 'post-model-fresh-before-C.json', 'C_SCOPE_APPROVED.json'):
    files.append(ROOT / 'evidence' / name)
files.extend(review_paths)
files.append(ROOT / 'configs/code-manifest.json')
save('G3_MODELS_APPROVED.json', {**common, 'independent_G3': '/root/numeric_g3_review',
    'bound_files': bindings(files)})
(ROOT / 'evidence/G2_CODE_APPROVED.json').write_text(json.dumps({
    'passed': True, 'code_manifest_sha256': CODE, 'allowed_actions': ['performance'],
    'independent_G2': '/root/profile_instrument_review', 'scope': 'C-off-only',
    'bound_files': bindings(review_paths + [ROOT / 'evidence/C-off-target-cpu-passed.json'])}, indent=2))
from resource_guard import code_identity, gate
assert code_identity('performance') == CODE
gate('G3_MODELS_APPROVED.json', CODE)
gate('C_SCOPE_APPROVED.json', CODE)
print(json.dumps({'C_off_authorized': True, 'code_manifest_sha256': CODE,
                  'B_not_run': True, 'lite_observation_passed': False,
                  'bound_files': len(bindings(files))}), flush=True)
