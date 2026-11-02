"""Receive a fresh read-only booking receipt without exposing credentials to workers."""
import json
from pathlib import Path
import time

from admission import bound_bytes
from live_evidence import write_exclusive
from preflight_guard import load_bound


def for_session(name, config, inputs, owner, claim, output, cancelled):
    if name == 'cold':
        return load_bound(owner, inputs['booking_file'], inputs['booking_sha256'])
    if name != 'restart':
        raise ValueError('Unknown selected booking session')
    output = Path(output)
    write_exclusive(output / 'restart-booking-request.json', {
        'schema': 'epd-restart-booking-request-v1', 'run_id': inputs['run_id'],
        'claim_sha256': claim.reservation_receipt['claim_sha256'],
        'observed_ms': int(time.time() * 1000), 'monotonic_s': time.perf_counter(),
        'deadline_monotonic': min(time.perf_counter() + 60, claim.deadline - config['cleanup_seconds'])})
    request = json.loads((output / 'restart-booking-request.json').read_bytes())
    handoff = output / 'restart-booking-handoff.json'
    while True:
        claim.check()
        if cancelled.is_set() or time.perf_counter() >= request['deadline_monotonic']:
            raise TimeoutError('Fresh restart booking handoff cancelled/expired; no restart')
        try:
            handoff.lstat()
        except FileNotFoundError:
            time.sleep(.1)
            continue
        if handoff.is_symlink():
            raise ValueError('Linked booking handoff refused')
        receipt = json.loads(handoff.read_bytes())
        if (set(receipt) != {'schema', 'run_id', 'claim_sha256', 'raw'}
                or receipt['schema'] != 'epd-restart-booking-handoff-v1'
                or receipt['run_id'] != inputs['run_id']
                or receipt['claim_sha256'] != request['claim_sha256']
                or set(receipt['raw']) != {'path', 'sha256'}):
            raise ValueError('Restart booking handoff identity differs')
        # The original raw API response is retained. Freshness/ticket/window are checked by the caller.
        return json.loads(bound_bytes(handoff, receipt['raw']['path'], receipt['raw']['sha256']))
