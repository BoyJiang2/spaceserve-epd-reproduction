"""Require independent actual model G3 plus formal-only G2 and unchanged foundations."""
import contextlib
import datetime
import json
from pathlib import Path
import signal

from resource_guard import ROOT,UUIDS,sha,gate,run_signals,_exclusive
from model_guard import model_code
from booking_window import require


def record_start_budget(root, remaining):
    estimate = 186 * 60  # Prior 48-cell run extrapolation; scheduling estimate, not a guarantee.
    reserve = 900  # Extra safety buffer; the original per-cell guard remains separate.
    state = {'decision_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'remaining_until_cleanup_seconds': remaining,
             'full_matrix_estimate_seconds': estimate, 'extra_safety_buffer_seconds': reserve,
             'estimated_budget_sufficient': remaining >= estimate + reserve,
             'new_GPU_requests': 0, 'scope': 'formal admission estimate only; no performance result'}
    with (root/'evidence/formal-start-budget.json').open('x') as output:
        json.dump(state, output, indent=2)
    if not state['estimated_budget_sufficient']:
        raise RuntimeError('insufficient estimated budget for the approved full matrix; preserve preflight evidence')


def formal_code():
    manifest=ROOT/'configs/formal-code-manifest.json'
    approval=json.loads((ROOT/'evidence/G2_FORMAL_CODE_APPROVED.json').read_text())
    if approval.get('passed') is not True or approval.get('allowed_actions')!=['formal'] or approval['code_manifest_sha256']!=sha(manifest):
        raise RuntimeError('formal controller not independently G2-approved')
    if approval.get('boot_id')!=Path('/proc/sys/kernel/random/boot_id').read_text().strip() or approval.get('gpu_uuids')!=UUIDS:
        raise RuntimeError('formal boot/GPU identity changed')
    for row in json.loads(manifest.read_text()):
        path=ROOT/row['path']
        if not path.resolve(strict=True).is_relative_to(ROOT) or sha(path)!=row['sha256']:
            raise RuntimeError('formal code or bound inputs changed: '+row['path'])
    return approval['code_manifest_sha256']


@contextlib.contextmanager
def exclusive_formal():
    with run_signals():
        remaining=require(fresh=True)
        if remaining<900:
            raise RuntimeError('less than fifteen minutes before cleanup; preserve checkpoint')
        signal.setitimer(signal.ITIMER_REAL,remaining)
        try:
            with _exclusive(None, 'formal'):
                producer=model_code()
                proof=gate('G3_MODEL_FORMAL_CONSUMER.json',producer)
                if proof.get('scope')!='Space-model-preflight-for-formal' or proof.get('formal_data_approved') is not False:
                    raise RuntimeError('actual model G3 has not approved formal consumer')
                record_start_budget(ROOT, require(fresh=True))
                yield formal_code()
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
