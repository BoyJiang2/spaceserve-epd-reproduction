"""Save only the actual active owned new-window booking; no reservation changes."""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import time

BATCH = Path(__file__).resolve().parents[2]/'outputs/spaceserve-window-20261028-2300'
BOOKING_ID = 'bk-20261028T0700-987277c5'
START = 1793199600000
END = 1793232000000
EXTENSION_ID = None  # No extension ticket in this window.
AUTHORIZED_END = END


def select_booking(snapshot, now_ms):
    rows = [b for b in snapshot['bookings'] if b.get('id') == BOOKING_ID
            and b.get('resource_id') == 'h20/qjh000' and b.get('node') == 'qjh000'
            and b.get('user') == 'boyjiang' and b.get('kind') == 'gpu'
            and b['start_ms'] == START and b['end_ms'] == END]
    resources = [r for r in snapshot['resources'] if r.get('id') == 'h20/qjh000' and r.get('active') is True]
    if len(rows) != 1 or len(resources) != 1:
        raise RuntimeError('no unique actual active owned new-window GPU booking/resource')
    result = {'verified_at_utc': datetime.datetime.fromtimestamp(now_ms/1000, datetime.timezone.utc).isoformat(),
            'booking': {key: rows[0][key] for key in
                        ('id', 'resource_id', 'node', 'user', 'kind', 'start_ms', 'end_ms')},
            'resource': {key: resources[0][key] for key in ('id', 'node', 'active', 'gpu_count')},
            'read_only': True}
    extensions = [b for b in snapshot['bookings']
                  if EXTENSION_ID is not None and b.get('id') == EXTENSION_ID]
    effective_end = END
    if extensions:
        if len(extensions) != 1:
            raise RuntimeError('duplicate extension booking')
        extension = extensions[0]
        if (any(extension.get(k) != result['booking'][k] for k in ('resource_id','node','user','kind'))
                or extension.get('start_ms') != END or extension.get('end_ms',0) < AUTHORIZED_END):
            raise RuntimeError('extension owner/lane/continuity/coverage differs')
        result['extension'] = {key:extension[key] for key in
                              ('id','resource_id','node','user','kind','start_ms','end_ms')}
        effective_end = AUTHORIZED_END
    if not START <= now_ms < effective_end:
        raise RuntimeError('outside actual owned and user-authorized coverage')
    result['authorized_effective_end_ms'] = effective_end
    return result


def main():
    helper = Path('C:/Users/23520/.codex/skills/gputime-booking-agent/scripts/gputime_agent.py')
    response = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(helper), 'snapshot'],
        capture_output=True, text=True, encoding='utf-8', check=True)
    state = select_booking(json.loads(response.stdout), time.time()*1000)
    target, temporary = (BATCH/'evidence'/name for name in ('BOOKING_VERIFIED.json', '.booking-update.tmp'))
    for path in (temporary, target, *target.parents):
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise RuntimeError('booking output refuses symlink/junction')
        if path == BATCH.parent.parent:
            break
    with temporary.open('x', encoding='utf-8') as output:
        json.dump(state, output, indent=2)
    temporary.replace(target)
    print(json.dumps({'id': state['booking']['id'], 'owner': 'boyjiang',
                      'start_ms': state['booking']['start_ms'], 'end_ms': state['booking']['end_ms']}))


if __name__ == '__main__':
    main()
