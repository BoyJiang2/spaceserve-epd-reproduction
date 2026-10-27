"""Add a model-only approval without overwriting the actual numeric producer chain."""
import contextlib
import json
from pathlib import Path
import signal

from resource_guard import ROOT,UUIDS,sha,gate,run_signals,_exclusive
from booking_window import require


def model_code():
    manifest=ROOT/'configs/model-code-manifest.json'
    approval=json.loads((ROOT/'evidence/G2_MODEL_CODE_APPROVED.json').read_text())
    if approval.get('passed') is not True or approval.get('allowed_actions')!=['preflight-models'] or approval['code_manifest_sha256']!=sha(manifest):
        raise RuntimeError('model preflight not independently G2-approved')
    if approval.get('boot_id')!=Path('/proc/sys/kernel/random/boot_id').read_text().strip() or approval.get('gpu_uuids')!=UUIDS:
        raise RuntimeError('model deployment boot/GPU identity changed')
    for row in json.loads(manifest.read_text()):
        path=ROOT/row['path']
        if not path.resolve(strict=True).is_relative_to(ROOT) or sha(path)!=row['sha256']:
            raise RuntimeError('model candidate code or bound inputs changed: '+row['path'])
    return approval['code_manifest_sha256']


@contextlib.contextmanager
def exclusive_models():
    with run_signals():
        remaining=require(fresh=True)
        if remaining<1800:
            raise RuntimeError('less than 30 minutes before cleanup; preserve checkpoint')
        signal.setitimer(signal.ITIMER_REAL,remaining)
        try:
            # This verifies the original numeric deployment and holds its shared locks;
            # the separate approval below is mandatory for any model action.
            with _exclusive(None) as numeric_producer:
                numeric=gate('G3_NUMERIC_MODEL_CONSUMER.json',numeric_producer)
                if numeric.get('scope')!='Space-numeric-for-model-preflight' or numeric.get('model_correctness_approved') is not False:
                    raise RuntimeError('numeric consumer scope does not permit this preflight transition')
                yield model_code()
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
