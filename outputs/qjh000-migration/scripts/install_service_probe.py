"""Add opt-in startup probes around the existing encoder stream mask call."""
import ast
import difflib
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
if str(root) != '/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023':
    raise RuntimeError('unexpected source root')
path = root / 'src/SpaceServe/vllm/v1/engine/core.py'
before = path.read_text()
old = '        self.encoder_stream = torch.cuda.Stream("cuda")\n        if libsmctrl_path is not None:'
new = ('        self.encoder_stream = torch.cuda.Stream("cuda")\n'
       '        if os.environ.get("REPRO_SM_PROBE") == "1":\n'
       '            from service_sm_probe import measure\n'
       '            measure(self.encoder_stream, "before-existing-mask")\n'
       '        if libsmctrl_path is not None:')
tail = ('            logger.info("libsmctrl is unavailable; skipping encoder SM "\n'
        '                        "partitioning.")')
new_tail = tail + ('\n        if os.environ.get("REPRO_SM_PROBE") == "1":\n'
                   '            measure(self.encoder_stream, "after-existing-mask")\n'
                   '            if libsmctrl_path is not None:\n'
                   '                stream_lzc_mask(self.encoder_stream, [0, 0, 0, 0])\n'
                   '                measure(self.encoder_stream, "restored-to-zero-mask")\n'
                   '                stream_lzc_mask(self.encoder_stream, encoder_mask)\n'
                   '                measure(self.encoder_stream, "reapplied-existing-mask")')
if new not in before:
    if before.count(old) != 1 or before.count(tail) != 1:
        raise RuntimeError('fixed encoder stream implementation differs')
    after = before.replace(old, new).replace(tail, new_tail)
    if not any(isinstance(node, ast.Import) and any(alias.name == 'os' for alias in node.names) for node in ast.parse(after).body):
        if 'import sys\n' not in after:
            raise RuntimeError('cannot place diagnostic environment import')
        after = after.replace('import sys\n', 'import sys\nimport os\n', 1)
    ast.parse(after)
    path.write_text(after)
    (root / 'results/patches/service-stream-probe.patch').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile='a/vllm/v1/engine/core.py', tofile='b/vllm/v1/engine/core.py')))
elif new_tail not in before:
    raise RuntimeError('partial diagnostic patch')
print('Opt-in probes ready; original mask call and inference path preserved')
