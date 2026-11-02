"""Fixed selected-candidate cold/restart vectors; no hardware or budget operations."""
import hashlib
from pathlib import Path

from experiment_plan import CANDIDATES, candidate_id, config_sha256
from preflight_guard import unit_budget

SESSIONS = ('cold', 'restart')
GEOMETRY = tuple((images, tokens, concurrency, 2 if concurrency == 1 else 8)
                 for images in (1, 4, 8) for tokens in (32, 128) for concurrency in (1, 8))


def session_batches(spec, name):
    """Validate the complete 120-request execution before selecting a 60-request view."""
    if (name not in SESSIONS or spec['schema'] != 'epd-fixed-unit-v1'
            or spec['phase'] != 'selected_g3' or type(spec['max_requests']) is not int
            or spec['max_requests'] != 120 or type(spec['wall_seconds']) is not int
            or spec['wall_seconds'] != 1600 or spec['request_diagnostics'] is not True
            or set(spec['sessions']) != set(SESSIONS)):
        raise ValueError('Exact selected cold/restart execution and budget required')
    candidate = next((item for item in CANDIDATES if candidate_id(item) == spec['candidate']), None)
    if (candidate is None or candidate[0] != spec['unit']
            or spec['candidate_config_sha256'] != config_sha256(candidate)
            or unit_budget('selected_g3', spec['unit'], spec['candidate']) != (120, 0, 1600)):
        raise ValueError('Selected system, profile or non-refundable budget differs')
    seen, combined = set(), []
    dataset = Path(spec['dataset']).resolve()
    for session in SESSIONS:
        batches = spec['sessions'][session]
        if not isinstance(batches, list) or len(batches) != len(GEOMETRY):
            raise ValueError('Each selected session requires twelve fixed cases')
        dispatch = 0
        for batch, (images, tokens, concurrency, count) in zip(batches, GEOMETRY):
            if (batch['case'] != f'i{images}-o{tokens}-c{concurrency}'
                    or any(type(batch[key]) is not int for key in ('images', 'tokens', 'concurrency'))
                    or (batch['images'], batch['tokens'], batch['concurrency']) != (images, tokens, concurrency)
                    or batch['warmup'] is not False or len(batch['requests']) != count):
                raise ValueError('Selected image/output/concurrency vector differs')
            for row in batch['requests']:
                fixture = row['fixture_id']
                if (type(fixture) is not str or not fixture or fixture in seen
                        or type(row['dispatch_index']) is not int or row['dispatch_index'] != dispatch):
                    raise ValueError('Repeated fixture or noncontinuous per-session round robin')
                seen.add(fixture)
                dispatch += 1
                value = row['input']
                if (set(value) != {'prompt', 'images'} or type(value['prompt']) is not str
                        or not value['prompt'] or len(value['images']) != images):
                    raise ValueError('Selected prompt/image input differs')
                for image in value['images']:
                    digest = image['rgb_sha256']
                    if (Path(image['path']).resolve().parent != dataset or type(digest) is not str
                            or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)):
                        raise ValueError('Selected image escapes dataset or lacks an RGB binding')
        if dispatch != 60:
            raise ValueError('Selected session must contain sixty requests')
        combined.extend(batches)
    if len(seen) != 120 or spec['batches'] != combined:
        raise ValueError('Full selected execution must preserve both unique ordered sessions')
    return spec['sessions'][name]


def make_batches(fixtures):
    """Use the common frozen fixture order, without generating extra native requests."""
    rows = fixtures['fixtures']
    if len(rows) != 120 or len({row['fixture_id'] for row in rows}) != 120:
        raise ValueError('Exactly 120 unique common fixtures required')
    sessions = {}
    consumed = set()
    for name in SESSIONS:
        batches, dispatch = [], 0
        for images, tokens, concurrency, count in GEOMETRY:
            case = f'i{images}-o{tokens}-c{concurrency}'
            selected = [row for row in rows if row['session'] == name and row['case'] == case]
            if len(selected) != count or any(row['output_tokens'] != tokens for row in selected):
                raise ValueError('Common fixture coverage/output vector differs')
            requests = []
            for row in selected:
                requests.append({'fixture_id': row['fixture_id'], 'dispatch_index': dispatch,
                                 'input': row['input']})
                consumed.add(row['fixture_id'])
                dispatch += 1
            batches.append({'case': case, 'images': images, 'tokens': tokens,
                            'concurrency': concurrency, 'warmup': False, 'requests': requests})
        sessions[name] = batches
    if len(consumed) != 120:
        raise ValueError('Unknown or omitted common fixtures')
    return sessions


def validate_spec(spec, config, source_sha256, selection):
    from fixed_unit import official_servers
    session_batches(spec, 'cold')
    cid = spec['candidate']
    systems = {'replicas', 'pd', 'epd'}
    if set(selection['selected']) != systems or set(selection['required_full_G3']) != systems:
        raise ValueError('Complete three-system calibration selection required')
    for system in sorted(systems):
        chosen = selection['selected'][system]['candidate']
        candidate = next((c for c in CANDIDATES if candidate_id(c) == chosen and c[0] == system), None)
        required = selection['required_full_G3'][system]
        if (candidate is None or required['candidate'] != chosen or required['requests'] != 120
                or required['source_manifest_sha256'] != source_sha256
                or required['runtime_binding_sha256'] != spec['runtime_binding_sha256']
                or required['candidate_config_sha256'] != config_sha256(candidate)):
            raise ValueError('Three-system selection profile/source/runtime differs')
    if (spec['source_manifest_sha256'] != source_sha256
            or selection['selected'][spec['unit']]['candidate'] != cid):
        raise ValueError('Exact calibrated selection/source/runtime differs')
    for key in ('runtime_binding_sha256', 'rgb_manifest_sha256'):
        value = spec[key]
        if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Missing exact selected runtime/RGB binding')
    if ('MiniCPM-V-2_6' not in spec['model'] or spec['servers'] != official_servers(spec, config)
            or hashlib.sha256(Path(spec['rgb_manifest']).read_bytes()).hexdigest() != spec['rgb_manifest_sha256']):
        raise ValueError('Selected model/official argv/visibility/RGB manifest differs')
    return 120
