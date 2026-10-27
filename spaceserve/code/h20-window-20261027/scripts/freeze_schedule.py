"""Freeze 54 cells with within-load Latin positions and opposing cycles."""
import argparse
import hashlib
import json
from pathlib import Path
import random

ROLES = ('baseline-space', 'space', 'space-mask')
LOADS = tuple((images, concurrency) for images in (1, 4) for concurrency in (1, 4, 8))


def schedule():
    rng = random.Random(20261027)
    load_order = list(LOADS)
    rng.shuffle(load_order)
    directions = [1] * 3 + [-1] * 3
    rng.shuffle(directions)
    base_roles = list(ROLES)
    rng.shuffle(base_roles)
    per_load = {}
    for load, direction in zip(load_order, directions):
        roles = base_roles if direction == 1 else list(reversed(base_roles))
        offset = rng.randrange(3)
        per_load[load] = [[roles[(position + block + offset) % 3]
                           for position in range(3)] for block in range(3)]
    cells = []
    for block in range(3):
        loads = load_order[block:] + load_order[:block]
        for images, concurrency in loads:
            for position, role in enumerate(per_load[(images, concurrency)][block]):
                cells.append({'index': len(cells), 'block': block, 'images': images,
                              'concurrency': concurrency, 'role_position': position,
                              'role': role, 'tokens': 128, 'warmup': 20, 'requests': 100})
    return {'seed': 20261027, 'cells': cells, 'formal_requests': 5400, 'warmup_requests': 1080,
            'limitations': 'Within-load role positions balanced; three repeats cannot balance pair order 1:1. Six loads use opposing Latin cycles. No claim of full carryover balance.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    payload = json.dumps(schedule(), indent=2, ensure_ascii=False).encode() + b'\n'
    with args.output.open('xb') as output:
        output.write(payload)
    print(hashlib.sha256(payload).hexdigest())
