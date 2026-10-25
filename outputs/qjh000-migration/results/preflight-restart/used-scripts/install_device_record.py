"""Apply identical startup-only device evidence hooks to native and fork workers."""
import difflib
import importlib.metadata
from pathlib import Path
import sys

if not __debug__:
    raise RuntimeError('do not run this patcher with -O')
root = Path(sys.argv[1]).resolve()
if str(root) != '/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023':
    raise RuntimeError('unexpected source root')
distribution = importlib.metadata.distribution('vllm')
if distribution.version != '0.7.2':
    raise RuntimeError('unexpected baseline version')
paths = [Path(distribution.locate_file('vllm/v1/worker/gpu_worker.py')),
         root / 'src/SpaceServe/vllm/v1/worker/gpu_worker.py']
if paths[0].resolve() == paths[1].resolve() or not paths[0].resolve().is_relative_to(root / 'envs/space'):
    raise RuntimeError('native wheel and fork must be separate files in the dedicated environment')
(root / 'results/patches').mkdir(parents=True, exist_ok=True)
old = '            self.model_runner.load_model()'
new = old + '\n            from record_device import record\n            record(self)'
pending, changes = [], []
for path in paths:
    before = path.read_text()
    if new in before:
        continue
    if before.count(old) != 1:
        raise RuntimeError('unexpected load_model implementation: ' + str(path))
    after = before.replace(old, new)
    compile(after, str(path), 'exec')
    pending.append((path, after))
    changes.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=str(path) + '.before', tofile=str(path)))
for path, after in pending:
    path.write_text(after)
if pending:
    (root / 'results/patches/device-record.patch').write_text(''.join(changes))
print('Startup device record hooks ready; inference code unchanged')
