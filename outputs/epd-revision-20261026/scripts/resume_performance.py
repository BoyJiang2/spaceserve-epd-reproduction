"""Once-only continuation of the frozen C schedule after the accepted first block."""
import json
import os
from pathlib import Path
import time
import uuid

from resource_guard import ROOT, exclusive, gate, code_identity, sha
from run_cells import services, benchmark


def validate_prefix(root, checkpoint):
    budget = (checkpoint.get('prefix_cells'), checkpoint.get('remaining_cells'),
              checkpoint.get('formal_completed'), checkpoint.get('warmup_completed'),
              checkpoint.get('formal_remaining'), checkpoint.get('warmup_remaining'))
    if budget != (10, 50, 1000, 200, 5000, 1000):
        raise RuntimeError('resume budget differs from the single approved checkpoint')
    schedule = root / 'configs/C-schedule.json'
    if sha(schedule) != '8d3d2b1aa8ab1ab76b4880f9a93016d9ff14b3b537f747c0acfd022f6965504e':
        raise RuntimeError('frozen C schedule changed')
    rows = json.loads(schedule.read_text())['rows']
    if len(rows) != 60 or any(row['mode'] != 'off' for row in rows):
        raise RuntimeError('C is not the original 60 off cells')
    destination = root / 'results/performance'
    names = [f'{index:03d}-b{row["block"]}-{row["load"]}-{row["system"]}-{row["mode"]}' for index, row in enumerate(rows)]
    if checkpoint.get('prefix_names') != names[:10] or {p.name for p in destination.iterdir() if p.is_dir()} != set(names[:10]):
        raise RuntimeError('existing cells are not the exact approved prefix')
    if (destination / 'COMPLETED').exists() or (destination / 'RESUME_STARTED.json').exists():
        raise RuntimeError('continuation already started or phase already complete')
    for index in range(10):
        if json.loads((destination / names[index] / 'COMPLETED').read_text()) != rows[index]:
            raise RuntimeError('accepted prefix marker changed')
    return destination, rows, names


def write_exit(root, status):
    directory = root / 'evidence/C-resume-exits'
    directory.mkdir(exist_ok=True)
    with (directory / (status['controller_id'] + '.json')).open('x') as output:
        json.dump(status, output, indent=2)
    marker = root / 'results/performance/RESUME_STARTED.json'
    if marker.exists():
        owner = json.loads(marker.read_text())
        if owner.get('controller_id') == status['controller_id'] and owner.get('pid') == status['pid']:
            with (root / 'evidence/C-resume-exit.json').open('x') as output:
                json.dump(status, output, indent=2)


def main(controller_id):
    with exclusive('performance-resume') as code:
        model = gate('G3_MODELS_APPROVED.json', code)
        scope = gate('C_SCOPE_APPROVED.json', code)
        checkpoint = gate('C_PREFIX_APPROVED.json', code)
        if (model.get('model_correctness_passed') is not True or
                model.get('lite_observation_approved') is not False or
                scope.get('scope') != 'C-off-only' or scope.get('lite_observation_approved') is not False):
            raise RuntimeError('off-only model and failure-fallback scope required')
        destination, rows, names = validate_prefix(ROOT, checkpoint)
        import psutil
        started = {'controller_id': controller_id, 'pid': os.getpid(), 'uid': os.getuid(), 'process_created': psutil.Process().create_time(),
                   'started_unix': time.time(), 'code_manifest_sha256': code, 'new_cells': 50,
                   'formal_remaining': 5000, 'warmup_remaining': 1000,
                   'prior_controller_exit': None, 'original_prefix_not_repeated': True}
        with (destination / 'RESUME_STARTED.json').open('x') as output:
            json.dump(started, output, indent=2)
        for index in range(10, 60):
            row = rows[index]
            folder = destination / names[index]
            print(json.dumps({'starting': str(folder), 'row': row, 'resume_same_C_schedule': True}), flush=True)
            with services(row['system'], row['mode'], folder) as (urls, env, servers):
                benchmark(folder, row, urls, env, servers)
        if code_identity() != code:
            raise RuntimeError('consumer code changed during continuation')
        with (destination / 'COMPLETED').open('x') as output:
            json.dump({'code_manifest_sha256': code, 'schedule_sha256': sha(ROOT / 'configs/C-schedule.json'),
                       'resumed_after_first_block': True, 'preserved_formal_requests': 1000,
                       'new_formal_requests': 5000, 'prior_controller_exit': None}, output, indent=2)


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('optimized continuation refused')
    status = {'controller_id': uuid.uuid4().hex, 'pid': os.getpid(), 'started_unix': time.time(), 'exit_code': None}
    try:
        main(status['controller_id'])
    except BaseException as error:
        status.update(exit_code=1, error_type=type(error).__name__, error=str(error))
        raise
    else:
        status['exit_code'] = 0
    finally:
        status['finished_unix'] = time.time()
        write_exit(ROOT, status)
