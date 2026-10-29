"""Build new phase manifests from actual local receipts; grants no approval or GPU action."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from runtime_config import context
CONFIG = context()

BATCH = CONFIG.run_root
SOURCE_SHA = CONFIG.config.get('source_manifest_sha256')
INPUT_SHA = CONFIG.config.get('asset_manifest_sha256')
PHASES = {'numeric': 'code-manifest.json', 'model': 'model-code-manifest.json',
          'formal': 'formal-code-manifest.json'}
TARGET_ROOT = str(CONFIG.run_root)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(phase):
    output = BATCH/'configs'/PHASES[phase]
    if output.exists() or output.is_symlink():
        raise RuntimeError('refuse existing phase manifest')
    source = BATCH/'configs/runtime-extension-source-manifest.json'
    if sha(source) != SOURCE_SHA or sha(BATCH/'configs/asset-inputs.json') != INPUT_SHA:
        raise RuntimeError('reviewed source/input manifest changed')
    rows = json.loads(source.read_text())
    required = json.loads((BATCH/'configs/source-files.json').read_text())
    if [row['path'] for row in rows] != [row['path'] for row in required] or len({row['path'] for row in rows}) != len(rows):
        raise RuntimeError('reviewed source membership differs')
    cpu = json.loads((BATCH/'evidence/extension-target-CPU.json').read_text())
    if (cpu['tests_passed'] != len(cpu['test_ids']) or not cpu['test_ids'] or cpu['tests_skipped'] != 0 or cpu['source_manifest_sha256'] != SOURCE_SHA
            or cpu['root'] != TARGET_ROOT or cpu['input_manifest_sha256'] != INPUT_SHA
            or cpu['log_sha256'] != sha(BATCH/'evidence/extension-target-CPU.log')):
        raise RuntimeError('actual CPU receipt missing or incomplete; not a Gate')
    paths = [row['path'] for row in rows] + [
        'configs/runtime-extension-source-manifest.json', 'configs/asset-inputs.json', 'configs/project.json',
        'configs/schedule-v2.json', 'evidence/CPU_STAGED.json',
        'evidence/extension-target-CPU.json', 'evidence/extension-target-CPU.log',
        'build/libsmctrl.so', 'build/service_sm_probe.so',
        'evidence/GIT_DEPLOYED.json', 'reviews/G1-project.md', 'reviews/G2-source.md']
    if phase == 'model':
        paths += ['configs/code-manifest.json', 'configs/input-pins-summary.json',
                  'evidence/G3_NUMERIC_MODEL_CONSUMER.json', 'evidence/MODEL_INPUTS_VERIFIED-attempt1.json']
    if phase == 'formal':
        paths += ['configs/model-code-manifest.json', 'evidence/G3_MODEL_FORMAL_CONSUMER.json']
    manifest = []
    for name in dict.fromkeys(paths):
        path = BATCH/name
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(BATCH.resolve()):
            raise RuntimeError('manifest path escapes the new batch')
        manifest.append({'path': name, 'bytes': path.stat().st_size, 'sha256': sha(path)})
    if manifest[:len(rows)] != rows:
        raise RuntimeError('deployed candidate source bytes differ')
    payload = (json.dumps(manifest, indent=2)+'\n').encode()
    with output.open('xb') as stream:
        stream.write(payload)
    return {'phase': phase, 'members': len(manifest), 'sha256': hashlib.sha256(payload).hexdigest(),
            'grants_no_G2_or_G3_or_GPU': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=PHASES)
    print(json.dumps(freeze(parser.parse_args().phase)))
