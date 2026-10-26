"""Read the booking service and save only our unique active GPU booking."""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import time

helper = Path('C:/Users/23520/.codex/skills/gputime-booking-agent/scripts/gputime_agent.py')
response = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(helper), 'snapshot'],
                          capture_output=True, text=True, encoding='utf-8', check=True)
snapshot = json.loads(response.stdout)
now = time.time() * 1000
bookings = [b for b in snapshot['bookings'] if b.get('resource_id') == 'h20/qjh000'
            and b.get('user') == 'boyjiang' and b.get('kind') == 'gpu'
            and b['start_ms'] <= now < b['end_ms']]
assert len(bookings) == 1, 'No unique current owned GPU booking'
resource = next(r for r in snapshot['resources'] if r['id'] == 'h20/qjh000')
assert resource['active']
state = {'verified_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'booking': bookings[0], 'resource': {k: resource[k] for k in ('id', 'node', 'active', 'gpu_count')},
         'read_only': True}
Path('outputs/epd-revision-20261026/evidence/BOOKING_VERIFIED.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps({'id': bookings[0]['id'], 'start_ms': bookings[0]['start_ms'], 'end_ms': bookings[0]['end_ms'], 'owner': 'boyjiang'}))
