"""Save only the actual active owned new-window booking; no reservation changes."""
import datetime
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from runtime_config import context
CONFIG = context()

BATCH = CONFIG.run_root
SCOPE = CONFIG.config.get('booking') or {}
BOOKING_ID = SCOPE.get('id')
START = SCOPE.get('start_ms')
END = SCOPE.get('end_ms')
RESOURCE = 'h20/' + CONFIG.config['host']
EXTENSION_ID = None  # No extension ticket in this window.
AUTHORIZED_END = END


def select_booking(snapshot, now_ms):
    if not BOOKING_ID or type(START) is not int or type(END) is not int:
        raise RuntimeError('No exact current booking configured')
    rows = [b for b in snapshot['bookings'] if b.get('id') == BOOKING_ID
            and b.get('resource_id') == RESOURCE and b.get('node') == CONFIG.config['host']
            and b.get('user') == 'boyjiang' and b.get('kind') == 'gpu'
            and b['start_ms'] == START and b['end_ms'] == END]
    resources = [r for r in snapshot['resources'] if r.get('id') == RESOURCE
                 and r.get('node') == CONFIG.config['host'] and r.get('active') is True]
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
    parser = argparse.ArgumentParser(description='Normalize a freshly fetched read-only booking API snapshot')
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding='utf-8-sig'))
    now_ms = int(time.time()*1000)
    human=(snapshot.get('origin')=='direct-human-reservation-confirmation-20261031'
           and snapshot.get('human_confirmed') is True
           and snapshot.get('authorization_reference')=='user-confirmed-qjh003-20261031-API-network-failure'
           and BOOKING_ID=='bk-20261030T0301-bd62e6dd' and START==1793376000000 and END==1793415600000)
    if (snapshot.get('origin')!='gputime_read_only_api' and not human):
        raise RuntimeError('Actual API or exact current human authorization required')
    if (snapshot.get('read_only') is not True
            or type(snapshot.get('observed_ms')) is not int or not 0 <= now_ms-snapshot['observed_ms'] <= 300000
            or snapshot['observed_ms'] < (START or now_ms+1)):
        raise RuntimeError('API snapshot must include an actual fresh observed_ms; no restamping old data')
    state = select_booking(snapshot, now_ms)
    state['verification_source']=snapshot['origin']
    state['booking_system_verified']=not human
    if human:
        state['authorization_reference']=snapshot['authorization_reference']
        state['authorization_recorded_ms']=snapshot['observed_ms']
    else:
        state['api_observed_ms'] = snapshot['observed_ms']
    state['verified_at_utc'] = datetime.datetime.fromtimestamp(snapshot['observed_ms']/1000,
                                                            datetime.timezone.utc).isoformat()
    target, temporary = (BATCH/'evidence'/name for name in ('BOOKING_VERIFIED.json', '.booking-update.tmp'))
    for path in (temporary, target, *target.parents):
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise RuntimeError('booking output refuses symlink/junction')
    with temporary.open('x', encoding='utf-8') as output:
        json.dump(state, output, indent=2)
    temporary.replace(target)
    print(json.dumps({'id': state['booking']['id'], 'owner': 'boyjiang',
                      'start_ms': state['booking']['start_ms'], 'end_ms': state['booking']['end_ms']}))


if __name__ == '__main__':
    main()
