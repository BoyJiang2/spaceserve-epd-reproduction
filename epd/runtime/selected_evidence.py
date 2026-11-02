"""Assemble actual selected raw artifacts for independent G3 review; never issue approval."""
import argparse
import hashlib
import json
from pathlib import Path

from admission import bound_bytes
from live_evidence import write_exclusive
from preflight_guard import digest, load_bound, require_prerequisite, validate_static


def build(owner, payload, reference_path):
    owner = Path(owner).resolve(strict=True)
    root = owner.parent

    def descriptor(path):
        path = Path(path).resolve(strict=True)
        relative = path.relative_to(root).as_posix()
        if not path.is_file():
            raise ValueError('Evidence must be an original regular file')
        return {'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def document(value):
        return json.loads(bound_bytes(owner, value['path'], value['sha256']))

    if (payload['schema'] != 'selected-evidence-input-v1'
            or set(payload['units']) != {'replicas', 'pd', 'epd'}):
        raise ValueError('All three actual selected units are mandatory')
    config = document(payload['config'])
    validate_static(config)
    deployment = document(payload['deployment'])
    selection = document(payload['selection'])
    source_sha = payload['source_manifest']['sha256']
    deploy_sha = payload['deployment']['sha256']
    for key in ('source_manifest', 'runtime_binding', 'fixtures'):
        document(payload[key])
    proof = {key: config[key] for key in ('host', 'uid', 'root', 'gpu_uuids', 'numa_by_uuid')}
    proof.update(schema='selected-three-G3-proof-v1', static_config_sha256=digest(config),
        boot_id=deployment['boot_id'], commit=deployment['commit'], source_manifest_sha256=source_sha,
        deploy_sha256=deploy_sha, systems={})
    proof.update({key: payload[key] for key in ('source_manifest', 'deployment', 'runtime_binding', 'selection')})
    native_raw = []
    for system in ('replicas', 'pd', 'epd'):
        unit = payload['units'][system]
        inputs = document(unit['inputs'])
        terminal = document(unit['terminal'])
        output = (root / unit['terminal']['path']).resolve(strict=True).parent
        if (terminal['state'] != 'released' or terminal['failure'] is not None or terminal['errors']
                or set(terminal['sessions']) != {'cold', 'restart'}
                or inputs['source_manifest_sha256'] != source_sha or inputs['deploy_sha256'] != deploy_sha):
            raise ValueError('Selected unit failed, is incomplete, or has different source/deploy')
        cid = selection['selected'][system]['candidate']
        input_owner = (root / unit['inputs']['path']).resolve(strict=True)
        require_prerequisite(input_owner, inputs, 'selected_g3', cid, config)
        prerequisite = load_bound(input_owner, inputs['prerequisite_file'], inputs['prerequisite_sha256'])['proof']
        for key, approved in (('selection', payload['selection']), ('selected_fixtures', payload['fixtures']),
                              ('runtime_binding', payload['runtime_binding'])):
            if prerequisite[key]['sha256'] != approved['sha256']:
                raise ValueError('Selected evidence differs from the original reviewed prerequisite')
        receipt = terminal['claim']
        claim_desc, ledger_desc = descriptor(receipt['claim']), descriptor(receipt['ledger'])
        claim = document(claim_desc)
        execution = document(descriptor(output / 'execution.json'))
        if (claim_desc['sha256'] != receipt['claim_sha256'] or claim['execution'] != execution
                or claim['execution_sha256'] != digest(execution)
                or claim['unit']['phase'] != 'selected_g3' or claim['unit']['unit'] != system
                or claim['unit']['candidate'] != cid or claim['unit']['run_id'] != inputs['run_id']
                or receipt['key'] != 'selected_g3/' + system):
            raise ValueError('Actual selected execution/Claim/system binding differs')
        group = {'candidate': cid, 'candidate_config_sha256': execution['candidate_config_sha256'],
            'inputs': payload['fixtures'], 'claim': claim_desc, 'ledger': ledger_desc, 'sessions': {},
            'admission_booking': descriptor(input_owner.parent / inputs['booking_file'])}
        if group['admission_booking']['sha256'] != inputs['booking_sha256']:
            raise ValueError('Original admission booking bytes changed')
        for name in ('cold', 'restart'):
            folder = output / name
            session = document(descriptor(folder / 'session.json'))
            actual_terminal = document(descriptor(folder / 'terminal.json'))
            if (actual_terminal['state'] != 'released' or actual_terminal['failure'] is not None
                    or actual_terminal['errors'] or actual_terminal['claim'] != receipt
                    or session['run_id'] != inputs['run_id'] or terminal['sessions'][name] != session):
                raise ValueError('Actual session lifecycle/Claim differs')
            for key, relative in (('requests', 'requests.jsonl'), ('client_windows', 'case-windows.jsonl'),
                    ('endpoints', 'endpoints.json'), ('registry', 'memory/process-registry.json'),
                    ('provider', 'memory/provider.json'), ('raw_nvml', 'memory/raw-nvml.jsonl'),
                    ('memory_samples', 'memory/samples.jsonl'), ('booking', 'booking.json'), ('release', 'release.json')):
                session[key] = descriptor(folder / relative)
            group['sessions'][name] = session
            if system == 'replicas':
                raw = bound_bytes(owner, session['requests']['path'], session['requests']['sha256'])
                if not raw.endswith(b'\n'):
                    raise ValueError('Native raw journal has an incomplete final record')
                native_raw.append(raw)
        proof['systems'][system] = group
    raw = b''.join(native_raw)
    rows = [json.loads(line) for line in raw.splitlines()]
    if len(rows) != 120 or len({row['fixture_id'] for row in rows}) != 120 or any(row['success'] is not True for row in rows):
        raise ValueError('Common reference must be all120 actual successful native outputs')
    reference_path = Path(reference_path).resolve()
    reference_path.relative_to(root)
    with reference_path.open('xb') as file:
        file.write(raw)
    reference = descriptor(reference_path)
    for group in proof['systems'].values():
        group['reference'] = reference
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    owner, output = args.inputs.resolve(strict=True), args.output.resolve()
    output.relative_to(owner.parent)
    if output.exists():
        raise FileExistsError('Preserve the existing evidence candidate')
    proof = build(owner, json.loads(owner.read_bytes()), output.with_suffix('.native-reference.jsonl'))
    write_exclusive(output, {'proof': proof, 'state': 'candidate_requires_independent_G3',
                              'formal_admission': 'blocked'})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
