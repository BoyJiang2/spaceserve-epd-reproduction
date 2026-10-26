"""Finish only the two never-started groups of the approved second attempt."""
import asyncio
import json
from pathlib import Path
import subprocess

from correctness_suite import run as check_suite
from resource_guard import ROOT, UUIDS, exclusive, gate, code_identity, sha
from run_cells import services, post, PYTHON

COMPLETED_GROUPS = ['cold-off-baseline-epd', 'cold-off-epd', 'cold-lite-baseline-epd',
                    'cold-lite-epd', 'restart-off-baseline-epd', 'restart-off-epd']
REMAINING_GROUPS = ['restart-lite-baseline-epd', 'restart-lite-epd']


def validate_checkpoint(root, checkpoint):
    if (checkpoint['completed_groups'] != COMPLETED_GROUPS or
            checkpoint['remaining_groups'] != REMAINING_GROUPS or
            checkpoint['reference_requests'] != 17 or checkpoint['target_requests_completed'] != 204 or
            checkpoint['new_target_budget'] != 68):
        raise RuntimeError('checkpoint differs from the approved remaining budget')
    destination = root / 'results/preflight-models'
    if {p.name for p in destination.iterdir() if p.is_dir()} != set(COMPLETED_GROUPS):
        raise RuntimeError('unexpected or already-started preflight group')
    if sha(destination / 'reference.json') != checkpoint['reference_sha256']:
        raise RuntimeError('reference changed')
    reference = json.loads((destination / 'reference.json').read_bytes())
    if reference.get('passed') is not True or len(reference['cases']) != 17:
        raise RuntimeError('reference is not the approved 17-case record')
    if (destination / 'result.json').exists() or (destination / 'RESUME_STARTED.json').exists():
        raise RuntimeError('resume already started or preflight already finalized')
    return reference['cases']


def main():
    with exclusive('preflight-resume') as code:
        gate('G3_NUMERICAL_APPROVED.json', code)
        checkpoint = gate('G3_PREFLIGHT_CHECKPOINT_APPROVED.json', code)
        reference = validate_checkpoint(ROOT, checkpoint)
        destination = ROOT / 'results/preflight-models'
        with (destination / 'RESUME_STARTED.json').open('x') as stream:
            json.dump({'code_manifest_sha256': code, 'only_groups': REMAINING_GROUPS,
                       'new_target_budget': 68, 'no_reference_regeneration': True}, stream)
        generated = 0
        for system in ('baseline-epd', 'epd'):
            folder = destination / ('restart-lite-' + system)
            with services(system, 'lite', folder) as (urls, env, servers):
                for index, url in enumerate(urls):
                    post(url, 'reset')
                    cases = asyncio.run(check_suite(url, str(ROOT / 'models/MiniCPM-V-2_6'), ROOT / 'dataset', folder / f'correctness-{index}.json', reference))
                    generated += len(cases)
                    (folder / f'export-{index}.json').write_text(json.dumps(post(url, 'export'), indent=2))
                subprocess.run([PYTHON, '-B', str(ROOT / 'scripts/check_rgb_cache.py'), '--dataset', str(ROOT / 'dataset'), '--urls', *urls, '--output', str(folder / 'rgb-after.json')], env=env, check=True, timeout=120)
            (folder / 'COMPLETED').write_text('17 cases per endpoint; resumed missing group only')
        if generated != 68 or code_identity() != code:
            raise RuntimeError('remaining budget or code identity mismatch')
        result = {'passed': True, 'requires_independent_G3': True, 'code_manifest_sha256': code,
                  'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'gpu_uuids': UUIDS,
                  'target_requests': 272, 'reference_requests': 17, 'new_target_requests': generated,
                  'checkpoint_target_requests': 204, 'checkpoint_reference_requests': 17,
                  'resumed_same_attempt': True, 'prior_controller_exit': 1,
                  'prior_cleanup_error_preserved': True, 'no_third_round': True}
        with (destination / 'result.json').open('x') as stream:
            json.dump(result, stream, indent=2)
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('optimized resume refused')
    main()
