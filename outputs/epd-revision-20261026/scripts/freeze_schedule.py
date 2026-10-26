"""Freeze global blocks before any new measurements; never overwrite a schedule."""
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
LOADS = {'A': (1, 128, 1), 'B': (4, 128, 8), 'C': (1, 128, 8), 'D': (8, 128, 8), 'E': (8, 32, 8)}


def schedule():
    rng = random.Random(20261026)
    base = list(LOADS)
    rng.shuffle(base)
    rotations = list(range(5))
    rng.shuffle(rotations)
    orders = [base[offset:] + base[:offset] for offset in rotations]
    extra = list(LOADS)
    rng.shuffle(extra)
    orders.append(extra)
    rows = []
    for block, loads in enumerate(orders):
        for load in loads:
            first = (block + list(LOADS).index(load)) % 2
            roles = ('epd', 'baseline-epd') if first == 0 else ('baseline-epd', 'epd')
            for role in roles:
                rows.append({'block': block, 'load': load, 'images': LOADS[load][0],
                             'tokens': LOADS[load][1], 'concurrency': LOADS[load][2], 'system': role,
                             'mode': 'off', 'warmup': 20, 'formal': 100})
    if len(rows) != 60 or sum(row['formal'] for row in rows) != 6000:
        raise RuntimeError('wrong schedule budget')
    for load in LOADS:
        first = [next(row for row in rows if row['block'] == block and row['load'] == load)['system'] for block in range(6)]
        if first.count('epd') != 3:
            raise RuntimeError('system order imbalance')
        positions = [orders[block].index(load) for block in range(5)]
        if sorted(positions) != list(range(5)):
            raise RuntimeError('Latin load-position imbalance')
    return {'seed': 20261026, 'global_blocks': 6, 'load_orders': orders, 'rows': rows,
            'formal_requests': 6000, 'warmup_requests': 1200, 'approved_for_gpu': False}


if __name__ == '__main__':
    destination = ROOT / 'configs/C-schedule.json'
    payload = (json.dumps(schedule(), indent=2) + '\n').encode()
    with destination.open('xb') as output:
        output.write(payload)
    destination.with_suffix('.sha256').write_text(hashlib.sha256(payload).hexdigest() + '  ' + destination.name + '\n')
    print('C schedule frozen; not a GPU approval')
