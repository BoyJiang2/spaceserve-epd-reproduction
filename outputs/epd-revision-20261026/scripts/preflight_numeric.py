"""Approved numerical probes only; this does not start the model or formal benchmark."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from resource_guard import ROOT, UUIDS, DEVICES, exclusive, idle
from owned_processes import stop


def run():
    destination = ROOT / 'results/preflight-numeric'
    with exclusive('numeric') as code:
        destination.mkdir(parents=True, exist_ok=False)
        python = ROOT / 'envs/epd/bin/python'
        identity = str(ROOT) + ':numeric:' + uuid.uuid4().hex
        environment = dict(os.environ, REPRO_RUN_ID=identity)
        try:
            with (destination / 'iommu.json').open('w') as log:
                subprocess.run([str(python), '-B', str(ROOT / 'scripts/check_iommu.py'), '--devices', ','.join(map(str, DEVICES)), '--require-compatible'], stdout=log, stderr=subprocess.STDOUT, check=True, env=environment, timeout=60)
            with (destination / 'blas.log').open('w') as log:
                for device in DEVICES:
                    subprocess.run([str(python), '-B', str(ROOT / 'scripts/probe_h20_blas.py'), '--device', str(device)], stdout=log, stderr=subprocess.STDOUT, check=True, env=environment, timeout=300)
                    idle()
            library = ROOT / 'build/epd-cuda/libcuda_ipc_utils.so'
            for label, script, source, target in [('embedding', 'probe_epd_embedding_ipc.py', DEVICES[0], DEVICES[1]), ('kv', 'probe_epd_kv_ipc.py', DEVICES[1], DEVICES[2])]:
                with (destination / (label + '.log')).open('w') as log:
                    subprocess.run([str(python), '-B', str(ROOT / 'scripts' / script), '--source', str(source), '--destination', str(target), '--library', str(library), '--output', str(destination / (label + '.json'))], stdout=log, stderr=subprocess.STDOUT, check=True, env=environment, timeout=300)
                idle()
        finally:
            stop(identity)
        result = {'passed': True, 'code_manifest_sha256': code, 'gpu_uuids': UUIDS,
                  'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  'models_started': False, 'requires_independent_G3': True}
        (destination / 'result.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('optimized preflight refused')
    run()
