"""Release only the failed CPU unit's registered processes; preserve its failure."""
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

p = json.load(sys.stdin)
root = Path('/local/boyjiang/epd')
repo = root/'repo'
folder = root/'runs/cpu-full4-20261031-once-27180'
a = p['approval']
review = base64.b64decode(p['review'])
parameters_raw = base64.b64decode(p['parameters'])
assert a['passed'] is True and a['blocking'] == 0
assert hashlib.sha256(review).hexdigest() == a['review_sha256']
assert hashlib.sha256(parameters_raw).hexdigest() == a['parameters_sha256']
cfg = json.loads(parameters_raw)
assert a['scope'] == 'EPD-failed-CPU-full4-cleanup-20261031'
assert os.uname().nodename == 'qjh003' and os.getuid() == 2147
assert os.sched_getaffinity(0) == {50} and os.getpriority(os.PRIO_PROCESS, 0) == 10
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == '65f52a67-afe4-4919-8646-4694255b48ee'
guard = base64.b64decode(p['booking_guard'])
assert hashlib.sha256(guard).hexdigest() == a['booking_guard_sha256']
pure = {'__name__': 'published_CPU_clearance'}
exec(compile(guard, '<Git21d4-CPU-clearance>', 'exec'), pure)
lease = pure['acquire_cpu50']()
started = time.monotonic()
cancelled = []
old = {n: signal.getsignal(n) for n in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM)}
for n in old:
    signal.signal(n, lambda number, frame: cancelled.append(number))

def check():
    if cancelled or time.monotonic()-started >= 90:
        raise TimeoutError('bounded CPU cleanup cancelled or expired')
    pure['validate'](p['booking'], int(time.time()*1000), 120)

check()
def owned_bytes(path):
    assert path.resolve(strict=True).is_relative_to(root) and path.is_file()
    for part in (path, *path.parents):
        assert not part.is_symlink()
        if part.is_relative_to(root):
            assert part.stat().st_uid == 2147
    return path.read_bytes()

for directory in (root, repo, folder, root/'staging'):
    for part in (directory, *directory.parents):
        assert not part.is_symlink()
        if part.is_relative_to(root):
            assert part.is_dir() and part.stat().st_uid == 2147
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'], timeout=10).decode().strip() == cfg['runtime_commit']
assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=all'], timeout=10).strip()
manifest = root/'staging/cpu-full4-deployment-20261031/deployed-files.json'
assert hashlib.sha256(owned_bytes(manifest)).hexdigest() == cfg['deployed_manifest_sha256']
for row in json.loads(owned_bytes(manifest)):
    path = repo/row['path']
    assert not path.is_symlink() and path.stat().st_uid == 2147
    data = owned_bytes(path)
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
journal = folder/'lifecycle.jsonl'
raw = owned_bytes(journal)
assert hashlib.sha256(raw).hexdigest() == cfg['journal_sha256']
known = {}
for line in raw.splitlines():
    event = json.loads(line)
    if event['event'] in ('head_process_registered','head_descendant_registered','head_descendant_verified'):
        identity = event['observation_before']['identity']
        known[identity['pid']] = identity
assert {str(pid): identity['proc_start_ticks'] for pid, identity in known.items()} == cfg['known_start_ticks']
assert len(known) == 18 and cfg['allow_KILL_fallback_for_verified_registered_only'] is True
sys.path.insert(0, str(repo/'epd/runtime'))
from numeric_cpu_lifecycle import terminate, Diagnostic
from numeric_descendants import HeadProc
from numeric_cpu_receipts import publish
proc = HeadProc()
stage = root/'staging/cpu-full4-cleanup-20261031'
assert not os.path.lexists(stage)
stage.mkdir(mode=0o700)

def record(event, **values):
    with (stage/'cleanup.jsonl').open('a', encoding='utf8') as out:
        out.write(json.dumps(dict(event=event, monotonic_s=time.monotonic(), **values))+'\n')
        out.flush(); os.fsync(out.fileno())

obj = Diagnostic.__new__(Diagnostic)
obj.root, obj.run_id, obj.uid, obj.proc = root, cfg['run_id'], 2147, proc
obj.record, obj.check = record, check
state = dict(exit_code=1, CPU_validation_passed=False, full4_passed=False,
             original_failed_batch_preserved=True, new_GPU_requests=0, new_Ray_head_started=False)
publish(stage/'claim.json', dict(scope=a['scope'], review_sha256=a['review_sha256'],
                               booking=p['booking'], parameters_sha256=a['parameters_sha256']))
try:
    selected = obj.leftovers()
    assert all(row['identity']['pid'] in known for row in selected), 'unknown scope process; no signal'
    for name, expected in cfg['wal_sha256'].items():
        assert hashlib.sha256(owned_bytes(folder/name)).hexdigest() == expected
    from numeric_cpu_ray import load_cpu_ray
    from numeric_gcs import GCSActorReader
    package = Path(json.loads(owned_bytes(folder/'config.json'))['ray_package'])
    ray, facts = load_cpu_ray(package)
    assert not ray.is_initialized()
    reader = GCSActorReader.connect('127.0.0.2:27180', package, record, check)
    try:
        for row in cfg['actors']:
            current = reader.read(row['expected'], started+90)
            assert current['state'] == 'DEAD' and current['pid'] == row['identity']['pid']
            assert not proc.exists(row['identity']['pid'])
    finally:
        reader.close()
    drivers = [identity for identity in known.values() if any(arg.endswith('/numeric_cpu_driver.py') for arg in identity['argv'])]
    assert len(drivers) == 4 and all(not proc.exists(row['pid']) for row in drivers)
    record('CPU_four_actors_DEAD_and_drivers_absent')
    ordered = sorted(known.values(), key=lambda row: (Path(row['exe']).name != 'raylet', row['pid']))
    assert sum(Path(row['exe']).name == 'raylet' for row in ordered) == 1
    for identity in ordered:
        check()
        outcome = terminate(identity, proc, record, check)
        record('CPU_cleanup_outcome', pid=identity['pid'], outcome=outcome)
        deadline = min(started+90, time.monotonic()+5)
        while proc.exists(identity['pid']):
            check()
            if time.monotonic() >= deadline:
                raise RuntimeError('registered process absence unconfirmed')
            time.sleep(.05)
    assert not obj.leftovers() and all(not proc.exists(pid) for pid in known)
    assert owned_bytes(journal) == raw
    for name, expected in cfg['wal_sha256'].items():
        assert hashlib.sha256(owned_bytes(folder/name)).hexdigest() == expected
    state.update(exit_code=0, registered_PIDs_absent=sorted(known), same_run_scope_processes=[], CPU_resources_released=True)
except BaseException as error:
    state['error'] = repr(error)
    raise
finally:
    state.update(finished_ms=int(time.time()*1000), elapsed_seconds=time.monotonic()-started)
    publish(stage/'terminal.json', state)
    print(json.dumps(state), flush=True)
    for number, handler in old.items():
        signal.signal(number, handler)
