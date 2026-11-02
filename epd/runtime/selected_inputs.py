"""Bind selected execution to committed settings and reviewed calibration artifacts."""
import hashlib
import json
from pathlib import Path

from admission import bound_bytes, validate_runtime
from experiment_plan import CANDIDATES, candidate_id, config_sha256
from fixed_unit import official_servers
from preflight_guard import load_bound, require_prerequisite
from selected_unit import make_batches, validate_spec

SOURCE = Path(__file__).resolve().parent


def load_execution(template_path, config, inputs, owner, system, deployed):
    if system not in ('replicas', 'pd', 'epd'):
        raise ValueError('Exactly one selected system is required')
    template_path = Path(template_path).resolve(strict=True)
    relative = template_path.relative_to(SOURCE).as_posix()
    manifest = load_bound(owner, inputs['source_manifest_file'], inputs['source_manifest_sha256'])
    raw = template_path.read_bytes()
    matches = [item for item in manifest['files'] if item['path'] == relative]
    if len(matches) != 1 or hashlib.sha256(raw).hexdigest() != matches[0]['sha256']:
        raise ValueError('Selected settings are not an exact pinned source member')
    template = json.loads(raw)
    if (set(template) != {'schema', 'phase', 'model', 'dataset', 'urls_by_system'}
            or template['schema'] != 'epd-selected-template-v1' or template['phase'] != 'selected_g3'
            or set(template['urls_by_system']) != {'replicas', 'pd', 'epd'}):
        raise ValueError('Selected settings schema differs or self-references the source manifest')
    prerequisite = load_bound(owner, inputs['prerequisite_file'], inputs['prerequisite_sha256'])
    body = prerequisite['proof']
    artifacts = {}
    for key in ('selection', 'selected_fixtures', 'runtime_binding', 'rgb_manifest'):
        descriptor = body[key]
        if set(descriptor) != {'path', 'sha256'} or descriptor not in body['raw_files']:
            raise ValueError('Selected artifact is outside independently reviewed raw files')
        artifacts[key] = bound_bytes(owner, descriptor['path'], descriptor['sha256'])
    selection = json.loads(artifacts['selection'])
    cid = selection['selected'][system]['candidate']
    candidate = next((item for item in CANDIDATES if candidate_id(item) == cid and item[0] == system), None)
    if candidate is None:
        raise ValueError('Selection is not a supported candidate for this system')
    require_prerequisite(owner, inputs, 'selected_g3', cid, config)
    runtime = json.loads(artifacts['runtime_binding'])
    validate_runtime(runtime)
    if (any(runtime[key] != deployed[key] for key in ('host', 'uid', 'boot_id'))
            or set(runtime['gpu_capacity_bytes']) != set(config['gpu_uuids'])):
        raise ValueError('Reviewed runtime differs from the actual deployment')
    sessions = make_batches(json.loads(artifacts['selected_fixtures']))
    spec = {'schema': 'epd-fixed-unit-v1', 'phase': 'selected_g3', 'unit': system, 'candidate': cid,
        'candidate_config_sha256': config_sha256(candidate), 'source_manifest_sha256': inputs['source_manifest_sha256'],
        'runtime_binding_sha256': body['runtime_binding']['sha256'],
        'model': template['model'], 'dataset': template['dataset'], 'urls': template['urls_by_system'][system],
        'rgb_manifest': str((Path(owner).resolve().parent / body['rgb_manifest']['path']).resolve(strict=True)),
        'rgb_manifest_sha256': body['rgb_manifest']['sha256'], 'max_requests': 120, 'wall_seconds': 1600,
        'request_diagnostics': True, 'sessions': sessions, 'batches': sessions['cold'] + sessions['restart']}
    spec['servers'] = official_servers(spec, config)
    validate_spec(spec, config, inputs['source_manifest_sha256'], selection)
    return spec
