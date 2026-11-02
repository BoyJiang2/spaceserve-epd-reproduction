"""Execute two selected sessions under one already admitted, non-refundable Claim."""
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import sys
import threading
import time

from live_evidence import snapshot, write_exclusive
from preflight_controller import execute_claimed
from preflight_guard import booking_remaining, digest
from selected_unit import SESSIONS, session_batches


def clock_point():
    return {'observed_ms': int(time.time() * 1000), 'monotonic_s': time.perf_counter()}


def released_session(config, inputs, deployed, backend, proc, output, report):
    """Observe actual absence after session end, before taking the release snapshot."""
    if report['state'] != 'released' or report['failure'] is not None or report['errors']:
        raise ValueError('Previous selected session failed or release is unconfirmed')
    manifest = json.loads((output / 'endpoints.json').read_bytes())
    apis = [service['api_identity'] for service in manifest['services']]
    owned = {(item['identity']['pid'], item['identity']['proc_start_ticks']): item
             for item in report['cleanup']}
    if not owned or any(item['state'] != 'gone' for item in owned.values()):
        raise ValueError('Original owned process cleanup is incomplete')
    if any((api['pid'], api['proc_start_ticks']) not in owned for api in apis):
        raise ValueError('API is missing from actual owned cleanup')
    if proc.boot() != deployed['boot_id']:
        raise ValueError('Boot changed before release observation')
    exits = []
    for (pid, ticks), item in owned.items():
        # An unreadable cwd/status is not proof that the process directory is gone.
        try:
            os.stat('/proc/' + str(pid), follow_symlinks=False)
        except FileNotFoundError:
            exits.append({'pid': pid, 'proc_start_ticks': ticks, 'state': 'not_present', **clock_point()})
        else:
            raise ValueError('Original PID still exists or has been reused; no restart')
    write_exclusive(output / 'process-exit-observations.json', exits)
    release = snapshot(config, inputs['run_id'], deployed, backend, proc)
    release['api_exit_observations'] = [item for item in exits
        if (item['pid'], item['proc_start_ticks']) in {(api['pid'], api['proc_start_ticks']) for api in apis}]
    write_exclusive(output / 'release.json', release)
    if any(gpu['processes'] or gpu['used_bytes'] > config['max_idle_bytes'] for gpu in release['gpus'].values()):
        raise ValueError('Actual GPU release is unconfirmed; no restart')
    return manifest, release


def archive_endpoints(config, inputs, output, manifest):
    """Retain the exact released sidecars so restart cannot consume stale endpoints."""
    folder = Path(config['root']) / 'runtime/endpoints'
    expected, prepared = {}, []
    for service in manifest['services']:
        api = service['api_identity']
        name = f"{inputs['run_id']}-{api['pid']}-{api['proc_start_ticks']}.json"
        if name in expected:
            raise ValueError('Duplicate API endpoint identity')
        expected[name] = service
    if {path.name for path in folder.glob(inputs['run_id'] + '-*.json')} != set(expected):
        raise ValueError('Unexpected or missing same-RUNID endpoint sidecar; do not move')
    for name, service in expected.items():
        path = folder / name
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as file:
            info = os.fstat(file.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != config['uid']:
                raise ValueError('Unknown endpoint file type/owner')
            raw = file.read()
        envelope = json.loads(raw)
        if (envelope['services'] != [service]
                or any(envelope.get(key) != value for key, value in manifest.items() if key != 'services')):
            raise ValueError('Released endpoint sidecar differs from actual manifest')
        prepared.append((path, info, raw))
    archive = output / 'released-endpoints'
    archive.mkdir(mode=0o700, exist_ok=False)
    rows = []
    for path, original, raw in prepared:
        current = path.lstat()
        if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (
                original.st_dev, original.st_ino, original.st_size, original.st_mtime_ns):
            raise ValueError('Endpoint changed before archival; no restart')
        target = archive / path.name
        # link is exclusive, unlike rename which could overwrite an existing artifact.
        os.link(path, target, follow_symlinks=False)
        if target.read_bytes() != raw:
            raise ValueError('Archived endpoint bytes changed; no restart')
        path.unlink()
        rows.append({'original': str(path), 'archive': str(target), 'bytes': len(raw),
                     'sha256': hashlib.sha256(raw).hexdigest()})
    write_exclusive(output / 'endpoint-relocation.json', rows)


def execute_sessions(config, inputs, deployed, spec, claim, backend, proc, output, active, booking_provider):
    """Caller owns both locks, admission and Claim; provider returns fresh raw API receipts."""
    session_batches(spec, 'cold')
    claim.verify_reservation()
    if digest(spec) != claim.execution_sha256:
        raise ValueError('Selected execution differs from the full original Claim')
    if json.loads(active.read_bytes()) != {'state': 'claimed', 'claim': claim.reservation_receipt,
                                          'run_id': inputs['run_id']}:
        raise ValueError('Global controller must remain claimed across both sessions')
    sessions, failure, cancelled = {}, None, threading.Event()
    previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    for number in previous:
        signal.signal(number, lambda number, frame: cancelled.set())
    try:
        for name in SESSIONS:
            claim.verify_reservation()
            if cancelled.is_set() or time.perf_counter() >= claim.deadline - config['cleanup_seconds']:
                raise TimeoutError('Selected unit cancelled or cleanup reserve reached')
            booking = booking_provider(name, cancelled)
            now_ms = int(time.time() * 1000)
            if booking_remaining(booking, config, now_ms) * 1000 < claim.timing['deadline_utc_ms'] - now_ms:
                raise ValueError('Fresh booking cannot cover the remaining original Claim')
            claim.check()
            if cancelled.is_set() or time.perf_counter() >= claim.deadline - config['cleanup_seconds']:
                raise TimeoutError('Selected unit cancelled during booking handoff')
            target = output / name
            target.mkdir(mode=0o700, exist_ok=False)
            write_exclusive(target / 'booking.json', booking)
            start = clock_point()
            view = {**spec, 'client_argv': [sys.executable, '-B', str(Path(__file__).with_name('selected_client.py')),
                '--execution', str(output / 'execution.json'), '--unit-runtime', str(target / 'client-runtime.json'),
                '--unit-output', str(target), '--session', name]}
            # Only the per-session active file is writable by execute_claimed's finally.
            report = execute_claimed(config, inputs, deployed, view, claim, backend, proc, target,
                                     target / 'active.json', cancelled=cancelled)
            end = clock_point()
            session = {'run_id': inputs['run_id'], 'start_utc_ms': start['observed_ms'],
                'start_monotonic': start['monotonic_s'], 'end_utc_ms': end['observed_ms'],
                'end_monotonic': end['monotonic_s'], 'terminal': str(target / 'terminal.json')}
            sessions[name] = session
            write_exclusive(target / 'session.json', session)
            manifest, release = released_session(config, inputs, deployed, backend, proc, target, report)
            claim.check()
            if (release['observed_ms'] > claim.timing['deadline_utc_ms']
                    or release['monotonic_s'] > claim.deadline):
                raise TimeoutError('Actual release exceeded original Claim deadline')
            archive_endpoints(config, inputs, target, manifest)
            claim.check()
            if cancelled.is_set():
                raise RuntimeError('Selected unit cancelled before completion')
    except BaseException as error:
        failure = {'type': type(error).__name__, 'error': repr(error)}
    finally:
        report = {'state': 'released' if failure is None and len(sessions) == 2 else 'stopped_no_next_unit',
            'failure': failure, 'errors': [], 'sessions': sessions, 'claim': claim.reservation_receipt,
            'formal_admission': 'blocked', 'evidence_state': 'raw_not_independently_reviewed'}
        try:
            sha = write_exclusive(output / 'terminal.json', report)
            active.write_text(json.dumps({'state': report['state'], 'terminal': str(output / 'terminal.json'),
                                          'terminal_sha256': sha}))
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)
    return report
