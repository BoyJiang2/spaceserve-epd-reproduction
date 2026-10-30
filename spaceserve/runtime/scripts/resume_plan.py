"""Pure resume planning for the fixed formal matrix.

No GPU, no Ray, no psutil: only marker files under the run's results/formal.
Every decision is derived from COMPLETED.json, never from directory presence alone.
"""
import json
from pathlib import Path


def cell_dirname(row):
    return '%03d-b%d-i%d-c%d-%s' % (row['index'], row['block'], row['images'],
                                    row['concurrency'], row['role'])


def _read_marker(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as error:
        return {'__unreadable__': repr(error)}


def classify(output, cells, code, verify_code=True):
    """Split schedule cells into done / pending / blocked.

    done     - directory exists, COMPLETED.json parses, is bound to `code` and to this schedule row
    pending  - directory does not exist
    blocked  - directory exists but is incomplete, foreign or unreadable (never auto-handled)
    """
    done, pending, blocked = [], [], []
    for row in cells:
        path = Path(output) / cell_dirname(row)
        marker = path / 'COMPLETED.json'
        if not path.exists():
            pending.append(row)
            continue
        if not marker.is_file():
            blocked.append({'index': row['index'], 'path': str(path),
                            'reason': 'cell directory exists without COMPLETED.json'})
            continue
        state = _read_marker(marker)
        if '__unreadable__' in state:
            blocked.append({'index': row['index'], 'path': str(path),
                            'reason': 'unreadable COMPLETED.json: ' + state['__unreadable__']})
            continue
        if verify_code and state.get('formal_code_manifest_sha256') != code:
            blocked.append({'index': row['index'], 'path': str(path),
                            'reason': 'COMPLETED.json bound to another code manifest'})
            continue
        if state.get('schedule_index') != row['index']:
            blocked.append({'index': row['index'], 'path': str(path),
                            'reason': 'COMPLETED.json schedule_index differs from this row'})
            continue
        if state.get('formal_requests') != row.get('requests'):
            blocked.append({'index': row['index'], 'path': str(path),
                            'reason': 'COMPLETED.json formal_requests differs from schedule'})
            continue
        done.append(row)
    return done, pending, blocked


def summary(done, pending, blocked):
    return {'done': [row['index'] for row in done],
            'pending': [row['index'] for row in pending],
            'blocked': blocked,
            'complete': not pending and not blocked}
