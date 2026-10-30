#!/usr/bin/env python3
"""Pre-window readiness checklist for the SpaceServe formal matrix.

Read-only: opens files, writes nothing, starts nothing. Run it before booking a window
so that a missing G3 gate or an expired booking costs a minute instead of six hours.

Exit code 0 = ready, 1 = at least one blocking finding.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

# Gates consumed by formal_guard.exclusive_formal(), in the order it needs them.
REQUIRED_GATES = (
    'G2_CODE_APPROVED.json',
    'G2_FORMAL_CODE_APPROVED.json',
    'G2_MODEL_CODE_APPROVED.json',
    'G3_NUMERICAL_APPROVED.json',
    'G3_MODEL_FORMAL_CONSUMER.json',
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def check_gate(root, name, code_sha, boot_id, gpu_uuids):
    """Mirror formal_guard.gate(): a gate is usable only if bound to this code/boot/GPU."""
    path = Path(root) / 'evidence' / name
    if not path.is_file():
        return {'check': name, 'ok': False, 'detail': 'missing'}
    try:
        state = load(path)
    except ValueError as error:
        return {'check': name, 'ok': False, 'detail': 'unreadable: %r' % (error,)}
    if state.get('passed') is not True:
        return {'check': name, 'ok': False, 'detail': 'passed is not true'}
    if state.get('code_manifest_sha256') != code_sha:
        return {'check': name, 'ok': False, 'detail': 'bound to another code manifest'}
    if state.get('boot_id') != boot_id:
        return {'check': name, 'ok': False, 'detail': 'boot_id differs from this host'}
    if state.get('gpu_uuids') != gpu_uuids:
        return {'check': name, 'ok': False, 'detail': 'gpu_uuids differ from project scope'}
    if not state.get('bound_files'):
        return {'check': name, 'ok': False, 'detail': 'no bound_files evidence'}
    for row in state['bound_files']:
        target = Path(root) / row['path']
        if not target.is_file() or sha(target) != row['sha256']:
            return {'check': name, 'ok': False, 'detail': 'bound file changed: ' + row['path']}
    return {'check': name, 'ok': True, 'detail': 'bound'}


def check_model_consumer(root, code_sha):
    path = Path(root) / 'evidence' / 'G3_MODEL_FORMAL_CONSUMER.json'
    if not path.is_file():
        return {'check': 'formal-consumer-scope', 'ok': False, 'detail': 'G3_MODEL_FORMAL_CONSUMER.json missing'}
    state = load(path)
    if state.get('scope') != 'Space-model-preflight-for-formal':
        return {'check': 'formal-consumer-scope', 'ok': False, 'detail': 'unexpected scope %r' % (state.get('scope'),)}
    if state.get('formal_data_approved') is not False:
        return {'check': 'formal-consumer-scope', 'ok': False, 'detail': 'reviewer approved formal data; this gate must stay False'}
    return {'check': 'formal-consumer-scope', 'ok': True, 'detail': 'scope pinned'}


def check_booking(project, now_ms, minutes_per_cell, cells):
    booking = project.get('booking') or {}
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
    project = load(project_path)
    if project.get('state') != 'approved_scope':
        findings.append({'check': 'project', 'ok': False, 'detail': 'state is %r' % (project.get('state'),)})
    gpu_uuids = project.get('gpu_uuids')
    if not isinstance(gpu_uuids, list) or len(gpu_uuids) != 1:
        findings.append({'check': 'project', 'ok': False, 'detail': 'gpu_uuids must pin exactly one device'})
        gpu_uuids = gpu_uuids or []

    manifest = root / 'configs/formal-code-manifest.json'
    if not manifest.is_file():
        return {'ready': False, 'findings': findings + [{'check': 'manifest', 'ok': False, 'detail': 'formal-code-manifest.json missing'}]}
    code_sha = sha(manifest)
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()

    for name in REQUIRED_GATES:
        findings.append(check_gate(root, name, code_sha, boot_id, gpu_uuids))
    findings.append(check_model_consumer(root, code_sha))

    schedule_path = root / 'configs/schedule-v2.json'
    if not schedule_path.is_file():
        findings.append({'check': 'schedule', 'ok': False, 'detail': 'configs/schedule-v2.json missing'})
        cells = 0
    else:
        schedule = load(schedule_path)
        cells = len(schedule.get('cells', []))
        requests = sum(row.get('requests', 0) for row in schedule.get('cells', []))
        warmups = sum(row.get('warmup', 0) for row in schedule.get('cells', []))
        ok = cells == 54 and requests == 5400 and warmups == 1080
        findings.append({'check': 'schedule', 'ok': ok, 'cells': cells, 'formal': requests,
                         'warmup': warmups, 'sha256': sha(schedule_path)})

    for name in ('scripts/start_server.sh', 'build/libsmctrl.so', 'scripts/benchmark.py'):
        path = root / name
        findings.append({'check': 'file:' + name, 'ok': path.is_file(), 'detail': 'present' if path.is_file() else 'missing'})

    findings.append(check_booking(project, now_ms, minutes_per_cell, cells or 54))

    done, pending, blocked = [], None, []
    if (root / 'results/formal').is_dir():
        findings.append({'check': 'results', 'ok': True, 'detail': 'results/formal exists; use --resume'})
    return {'ready': all(item['ok'] for item in findings), 'now_ms': now_ms,
            'code_manifest_sha256': code_sha, 'findings': findings}


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
