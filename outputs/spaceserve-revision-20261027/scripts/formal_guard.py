"""Require independent actual model G3 plus formal-only G2 and unchanged foundations."""
import contextlib
import json
from pathlib import Path
import signal

from resource_guard import ROOT,UUIDS,sha,gate,run_signals,_exclusive
from model_guard import model_code
from booking_window import require


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
            with _exclusive(None):
                producer=model_code()
                proof=gate('G3_MODEL_FORMAL_CONSUMER.json',producer)
                if proof.get('scope')!='Space-model-preflight-for-formal' or proof.get('formal_data_approved') is not False:
                    raise RuntimeError('actual model G3 has not approved formal consumer')
                yield formal_code()
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
