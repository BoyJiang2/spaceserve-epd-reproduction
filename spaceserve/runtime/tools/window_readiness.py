#!/usr/bin/env python3
"""Pre-window readiness checklist for the SpaceServe formal matrix.

Read-only: opens files, writes nothing, starts nothing. Run it before booking a window
so that a missing G3 gate or an expired booking costs a minute instead of six hours.

Exit code 0 = static checks passed, 1 = at least one blocking finding.
This advisory does not replace fresh booking, idle/lock checks or runtime gates.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

# Each approval belongs to its producer, not to the final formal manifest.
REQUIRED_GATES = (
    ('G2_CODE_APPROVED.json', 'code', 'evidence/numeric-producer', None),
    ('G2_MODEL_CODE_APPROVED.json', 'model-code', '.', ['preflight-models']),
    ('G2_FORMAL_CODE_APPROVED.json', 'formal-code', '.', ['formal']),
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def inside(root, path):
    path = Path(path).resolve(strict=True)
    if not path.is_relative_to(Path(root).resolve(strict=True)):
        raise ValueError('path outside run root')
    return path


def verify_files(root, base, rows):
    base = inside(root, base)
    if not isinstance(rows, list) or not rows:
        raise ValueError('no bound_files evidence or manifest members')
    for row in rows:
        relative = row['path']
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
            raise ValueError('member path must be relative without parent traversal')
        target = inside(base, base / relative)
        if not target.is_file() or sha(target) != row['sha256']:
            raise ValueError('bound file changed: ' + row['path'])


def check_gate(root, name, code_sha, boot_id, gpu_uuids,
               manifest=None, archive=None, allowed_actions=None):
    """Check G2 producer members or G3 bound evidence with their own identity."""
    try:
        path = inside(root, Path(root) / 'evidence' / name)
        state = load(path)
        if state.get('passed') is not True:
            raise ValueError('passed is not true')
        if state.get('code_manifest_sha256') != code_sha:
            raise ValueError('bound to another code manifest')
        if state.get('boot_id') != boot_id:
            raise ValueError('boot_id differs from this host')
        if state.get('gpu_uuids') != gpu_uuids:
            raise ValueError('gpu_uuids differ from project scope')
        if allowed_actions is not None and state.get('allowed_actions') != allowed_actions:
            raise ValueError('allowed_actions differ from consumer')
        if manifest is None:
            verify_files(root, root, state.get('bound_files'))
        else:
            verify_files(root, archive, load(inside(root, manifest)))
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        return {'check': name, 'ok': False, 'detail': 'unreadable: %r' % (error,)}
    return {'check': name, 'ok': True, 'detail': 'bound'}


def check_model_consumer(root, code_sha):
    path = Path(root) / 'evidence' / 'G3_MODEL_FORMAL_CONSUMER.json'
    if not path.is_file():
        return {'check': 'formal-consumer-scope', 'ok': False, 'detail': 'G3_MODEL_FORMAL_CONSUMER.json missing'}
    try:
        state = load(inside(root, path))
    except (OSError, ValueError, TypeError) as error:
        return {'check': 'formal-consumer-scope', 'ok': False, 'detail': repr(error)}
    if not isinstance(state, dict):
        return {'check': 'formal-consumer-scope', 'ok': False, 'detail': 'invalid gate object'}
    if state.get('scope') != 'Space-model-preflight-for-formal':
        return {'check': 'formal-consumer-scope', 'ok': False, 'detail': 'unexpected scope %r' % (state.get('scope'),)}
    if state.get('formal_data_approved') is not False:
        return {'check': 'formal-consumer-scope', 'ok': False, 'detail': 'reviewer approved formal data; this gate must stay False'}
    return {'check': 'formal-consumer-scope', 'ok': True, 'detail': 'scope pinned'}


def check_booking(project, now_ms, minutes_per_cell, cells):
    booking = project.get('booking') or {}
    if not isinstance(booking, dict):
        return {'check': 'booking', 'ok': False, 'detail': 'invalid booking object'}
    start, end = booking.get('start_ms'), booking.get('end_ms')
    estimate = int(minutes_per_cell * 60 * 1000 * cells) + 900 * 1000
    if not isinstance(start, int) or not isinstance(end, int) or end <= start:
        return {'check': 'booking', 'ok': False, 'detail': 'no usable booking in project.json'}
    if now_ms >= end:
        return {'check': 'booking', 'ok': False, 'detail': 'booking already ended', 'end_ms': end}
    if now_ms + estimate > end:
        return {'check': 'booking', 'ok': False,
                'detail': 'remaining window shorter than estimate',
                'remaining_s': (end - now_ms) // 1000, 'estimate_s': estimate // 1000}
    return {'check': 'booking', 'ok': True,
            'detail': 'window covers estimate', 'remaining_s': (end - now_ms) // 1000,
            'estimate_s': estimate // 1000}


def evaluate(root, now_ms=None, minutes_per_cell=5.5):
    root = Path(root)
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    findings = []

    project_path = root / 'configs/project.json'
    if not project_path.is_file():
        return {'ready': False, 'findings': [{'check': 'project', 'ok': False, 'detail': 'configs/project.json missing'}]}
    try:
        project = load(inside(root, project_path))
        if not isinstance(project, dict):
            raise ValueError('project must be an object')
    except (OSError, ValueError, TypeError) as error:
        return {'ready': False, 'findings': [{'check': 'project', 'ok': False, 'detail': repr(error)}]}
    if project.get('state') != 'approved_scope':
        findings.append({'check': 'project', 'ok': False, 'detail': 'state is %r' % (project.get('state'),)})
    gpu_uuids = project.get('gpu_uuids')
    if not isinstance(gpu_uuids, list) or len(gpu_uuids) != 1:
        findings.append({'check': 'project', 'ok': False, 'detail': 'gpu_uuids must pin exactly one device'})
        gpu_uuids = gpu_uuids or []

    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    producer_shas = {}
    for name, producer, archive, actions in REQUIRED_GATES:
        manifest = root / ('configs/' + producer + '-manifest.json')
        try:
            code_sha = sha(inside(root, manifest))
            producer_shas[producer] = code_sha
            findings.append(check_gate(root, name, code_sha, boot_id, gpu_uuids,
                                       manifest, root / archive, actions))
        except (OSError, ValueError) as error:
            findings.append({'check': name, 'ok': False, 'detail': repr(error)})
    findings.append(check_gate(root, 'G3_MODEL_FORMAL_CONSUMER.json',
                               producer_shas.get('model-code'), boot_id, gpu_uuids))
    findings.append(check_model_consumer(root, producer_shas.get('model-code')))

    schedule_path = root / 'configs/schedule-v2.json'
    cells = 0
    try:
        schedule = load(inside(root, schedule_path))
        if not isinstance(schedule, dict) or not isinstance(schedule.get('cells'), list):
            raise ValueError('schedule must contain a cells list')
        rows = schedule['cells']
        if any(not isinstance(row, dict) or
               any(type(row.get(key)) is not int or row[key] < 0 for key in ('requests', 'warmup'))
               for row in rows):
            raise ValueError('schedule cells require nonnegative integer requests and warmup')
        cells = len(rows)
        requests = sum(row['requests'] for row in rows)
        warmups = sum(row['warmup'] for row in rows)
        ok = cells == 54 and requests == 5400 and warmups == 1080
        findings.append({'check': 'schedule', 'ok': ok, 'cells': cells, 'formal': requests,
                         'warmup': warmups, 'sha256': sha(schedule_path)})
    except (OSError, ValueError, TypeError) as error:
        findings.append({'check': 'schedule', 'ok': False, 'detail': repr(error)})

    for name in ('scripts/start_server.sh', 'build/libsmctrl.so', 'scripts/benchmark.py'):
        path = root / name
        findings.append({'check': 'file:' + name, 'ok': path.is_file(), 'detail': 'present' if path.is_file() else 'missing'})

    findings.append(check_booking(project, now_ms, minutes_per_cell, cells or 54))

    done, pending, blocked = [], None, []
    if (root / 'results/formal').is_dir():
        findings.append({'check': 'results', 'ok': True, 'detail': 'results/formal exists; use --resume'})
    return {'ready': all(item['ok'] for item in findings), 'now_ms': now_ms,
            'code_manifest_sha256': producer_shas.get('formal-code'), 'findings': findings,
            'scope': 'static advisory; runtime resource and execution checks still required'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True, help='run root (contains configs/, evidence/, scripts/)')
    parser.add_argument('--now-ms', type=int, help='override clock for a dry rehearsal')
    parser.add_argument('--minutes-per-cell', type=float, default=5.5)
    parser.add_argument('--output', type=Path, help='optional JSON report path')
    args = parser.parse_args()
    report = evaluate(args.root, args.now_ms, args.minutes_per_cell)
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text + '\n')
    return 0 if report['ready'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
