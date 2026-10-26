"""Validate actual approvals and immutable prefix, then launch the one C continuation."""
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

if not __debug__:
    raise RuntimeError('optimized authorization refused')

ROOT = Path('/var/tmp/boyjiang-epd-revision-20261026')
sys.path.insert(0, str(ROOT / 'scripts'))
from resource_guard import UUIDS, idle, remaining_owned, sha, code_identity, gate
from booking_window import require
from run_cells import host_snapshot
from resume_performance import validate_prefix

OLD = '9bb1a92b9864bb9ccd837a9258d7079f0dc98d559ab305c906d4bed6d27d4bbd'
NEW = '01cab0ae49091effbd6bed8220fee96382d711f761ef7bcfa8652ad287da5ed0'
assert Path(os.environ['EXP_ROOT']).resolve() == ROOT
assert sha(ROOT / 'configs/code-manifest.json') == NEW
for row in json.loads((ROOT / 'configs/code-manifest.json').read_text()):
    path = ROOT / row['path']
    assert path.resolve().is_relative_to(ROOT) and sha(path) == row['sha256'], row['path']
require(fresh=True)
idle()
assert not remaining_owned()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == '838160b3-4eb7-4a24-accc-f7720e0ac78a'
assert not (ROOT / 'results/performance/RESUME_STARTED.json').exists()
assert not (ROOT / 'evidence/C-resume-launch.json').exists()
cpu = json.loads((ROOT / 'evidence/C-resume-target-cpu-passed.json').read_text())
assert cpu['passed'] and cpu['code_manifest_sha256'] == NEW and cpu['cpu_tests'] == 27 and cpu['real_alarm_tests'] == 1
assert cpu['raw_log_sha256'] == sha(ROOT / 'evidence/C-resume-target-cpu.log')
old_gate_path = ROOT / 'evidence/G3_MODELS_APPROVED.json'
old_gate = json.loads(old_gate_path.read_text())
assert old_gate['code_manifest_sha256'] == OLD and old_gate['scope'] == 'C-off-only'
assert len(old_gate['bound_files']) == 171
old_scope_path = ROOT / 'evidence/C_SCOPE_APPROVED.json'
assert json.loads(old_scope_path.read_text())['code_manifest_sha256'] == OLD

def preserve(source, destination):
    if destination.exists():
        assert destination.read_bytes() == source.read_bytes()
    else:
        with destination.open('xb') as output:
            output.write(source.read_bytes())

preserve(old_gate_path, ROOT / 'evidence/C-first-block-model-gate.json')
preserve(old_scope_path, ROOT / 'evidence/C-first-block-scope.json')
assert sha(ROOT / 'evidence/C-first-block-code-manifest.json') == OLD
relocations = {'configs/code-manifest.json': 'evidence/C-first-block-code-manifest.json',
               'evidence/C_SCOPE_APPROVED.json': 'evidence/C-first-block-scope.json'}
old_mapping = []
files = []
for row in old_gate['bound_files']:
    preserved = relocations.get(row['path'], row['path'])
    path = ROOT / preserved
    assert sha(path) == row['sha256'], row['path']
    old_mapping.append({'original_path': row['path'], 'preserved_path': preserved, 'sha256': row['sha256']})
    files.append(path)
assert sum(row['original_path'] != row['preserved_path'] for row in old_mapping) == 2
interruption = json.loads((ROOT / 'evidence/C-interruption-20261027-0018.json').read_text())
assert interruption['controller_exit_code'] is None and len(interruption['files']) == 152
failed_name = '010-b1-D-epd-off'
failed = ROOT / 'results/performance' / failed_name
archive = ROOT / 'results/failures/C-first-interruption' / failed_name
assert failed.resolve().parent == (ROOT / 'results/performance').resolve()
assert archive.resolve().is_relative_to(ROOT / 'results/failures')
for row in interruption['files']:
    path = ROOT / row['path']
    assert path.resolve().is_relative_to(ROOT) and sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
failed_files = [p for p in failed.rglob('*') if p.is_file()]
assert {p.relative_to(failed).as_posix() for p in failed_files} == {'rgb-before.json', 'logs/server-19810.log'}
assert not archive.exists()
archive.parent.mkdir(parents=True, exist_ok=True)
failed.rename(archive)
prefix_mapping = []
for row in interruption['files']:
    original = ROOT / row['path']
    path = archive / original.relative_to(failed) if original.is_relative_to(failed) else original
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    prefix_mapping.append({**row, 'original_path': row['path'], 'preserved_path': path.relative_to(ROOT).as_posix()})
    files.append(path)
assert sum(row['original_path'] != row['preserved_path'] for row in prefix_mapping) == 2
analysis = json.loads((ROOT / 'evidence/C-prefix-analysis.json').read_text())
assert analysis['complete'] is False and not analysis['intervals']
assert [row['schedule_index'] for row in analysis['cells'] if row['status'] == 'valid'] == list(range(10))
rows = json.loads((ROOT / 'configs/C-schedule.json').read_text())['rows']
prefix = dict(prefix_cells=10, remaining_cells=50, formal_completed=1000, warmup_completed=200,
              formal_remaining=5000, warmup_remaining=1000,
              prefix_names=[f'{i:03d}-b{r["block"]}-{r["load"]}-{r["system"]}-{r["mode"]}' for i, r in enumerate(rows[:10])])
validate_prefix(ROOT, prefix)
host_snapshot(ROOT / 'evidence/C-resume-fresh-resources.json')

def save(name, state):
    with (ROOT / 'evidence' / name).open('x') as output:
        json.dump(state, output, indent=2)

save('C-resume-history-mapping.json', {'old_171': old_mapping, 'original_152': prefix_mapping,
     'old_producer_sha256': OLD, 'new_consumer_sha256': NEW,
     'old_exit_code': None, 'old_cause': 'unknown', 'no_prefix_requests_repeated': True})
review_paths = [ROOT / 'evidence/reviews-C-resume' / name for name in (
    'g1-C-prefix-resume-subagent.md', 'g4-C-first-block-prefix-subagent.md',
    'g2-C-resume-subagent.md', 'g3-C-resume-consumer-subagent.md')]
assert all(path.is_file() for path in review_paths)
files.extend(review_paths)
for name in ('C-first-block-model-gate.json', 'C-first-block-scope.json', 'C-first-block-code-manifest.json',
             'C-resume-code-delta.json', 'C-resume-target-cpu.log', 'C-resume-target-cpu-passed.json',
             'C-interruption-20261027-0018.json', 'C-prefix-analysis.json', 'C-resume-history-mapping.json',
             'C-resume-fresh-resources.json'):
    files.append(ROOT / 'evidence' / name)
files.extend([ROOT / 'configs/code-manifest.json', ROOT / 'configs/C-schedule.json',
              ROOT / 'evidence/C-first-block-source/scripts/test_protocol.py'])

def bindings(paths):
    return [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p)} for p in sorted(set(paths))]

common = {**old_gate, 'code_manifest_sha256': NEW, 'allowed_actions': ['performance-resume'],
          'authorization_helper_sha256': sha(Path(__file__)), 'actual_review_files': bindings(review_paths),
          'created_at_unix': time.time(), 'scope': 'C-off-only', 'lite_observation_approved': False,
          'model_correctness_passed': True, 'C_prefix_producer_sha256': OLD,
          'old_controller_exit': None, 'old_controller_cause': 'unknown', 'one_C_continuation_only': True,
          'performance_execution': [{'indices': [0, 9], 'producer_sha256': OLD},
                                    {'indices': [10, 59], 'producer_sha256': NEW}]}
model = {**common, 'bound_files': bindings(files)}
old_gate_path.write_text(json.dumps(model, indent=2))
scope = {**common, 'independent_G1_G4': ['/root/profile_plan_review', '/root/numeric_g3_review'],
         'bound_files': bindings([old_gate_path, ROOT / 'evidence/C-resume-history-mapping.json', *review_paths])}
old_scope_path.write_text(json.dumps(scope, indent=2))
save('C_PREFIX_APPROVED.json', {**common, **prefix, 'bound_files': bindings([
    old_gate_path, old_scope_path, ROOT / 'evidence/C-prefix-analysis.json',
    ROOT / 'evidence/C-resume-history-mapping.json', *files])})
(ROOT / 'evidence/G2_CODE_APPROVED.json').write_text(json.dumps({
    'passed': True, 'code_manifest_sha256': NEW, 'allowed_actions': ['performance-resume'],
    'independent_G2': '/root/profile_instrument_review', 'scope': 'unique remaining 50 C off cells',
    'bound_files': bindings([ROOT / 'evidence/C-resume-target-cpu-passed.json', *review_paths])}, indent=2))
assert code_identity('performance-resume') == NEW
for name in ('G3_MODELS_APPROVED.json', 'C_SCOPE_APPROVED.json', 'C_PREFIX_APPROVED.json'):
    gate(name, NEW)
require(fresh=True)
idle()
assert not remaining_owned()
log_path = ROOT / 'evidence/C-resume-controller.log'
with log_path.open('xb') as log:
    child = subprocess.Popen([str(ROOT / 'envs/epd/bin/python'), '-B', '-u', str(ROOT / 'scripts/resume_performance.py')],
                             stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             env=dict(os.environ), start_new_session=True)
import psutil
launch = {'pid': child.pid, 'process_created': psutil.Process(child.pid).create_time(), 'uid': os.getuid(),
          'code_manifest_sha256': NEW, 'spawned_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'log': str(log_path), 'state': 'spawned; verify live marker and runtime separately',
          'prior_exit_code': None, 'only_remaining_cells': 50}
save('C-resume-launch.json', launch)
print(json.dumps({'C_resume_launched': True, **launch}), flush=True)
