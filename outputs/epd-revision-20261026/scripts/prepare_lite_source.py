"""Apply only explicit observation metadata and cap8 to this new local source copy."""
import ast
import difflib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/epdserve/epdserve'


def replace(text, before, after):
    if text.count(before) != 1:
        raise RuntimeError('source anchor is not unique')
    return text.replace(before, after, 1)


def run():
    expected = Path('D:/Documents/codex/2026-10-23/new-chat-2/outputs/epd-revision-20261026') if os.name == 'nt' else Path('/var/tmp/boyjiang-epd-revision-20261026')
    if ROOT.resolve() != expected.resolve():
        raise RuntimeError('not the reviewed new source-copy root')
    patch = ROOT / 'lite-observation.patch'
    if patch.exists():
        raise RuntimeError('source already adapted')
    pending, diff = [], []
    for name in ('worker.py', 'engine_common.py', 'api_server.py', 'llm_async.py'):
        path = SOURCE / name
        before = path.read_text()
        after = before
        if name == 'worker.py':
            tree = ast.parse(after)
            insertions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name in ('step_llm', 'step_encoding', 'migrate_blocks_context', 'migrate_blocks_encoding'):
                    lines = after.splitlines(True)
                    close = next(i for i in range(node.lineno, node.body[0].lineno) if lines[i].lstrip().startswith(')'))
                    preceding = close - 1
                    if not lines[preceding].rstrip().endswith(','):
                        lines[preceding] = lines[preceding].rstrip() + ',\n'
                    insertions.append((close, '        repro_meta=None,\n'))
                    after = ''.join(lines)
            if len(insertions) != 4:
                raise RuntimeError('expected four observed worker signatures')
            lines = after.splitlines(True)
            for index, line in sorted(insertions, reverse=True):
                lines.insert(index, line)
            after = ''.join(lines)
            after = replace(after, '    def ready(self):', '''    def repro_lite(self, operation):
        if operation == 'runtime':
            return observe.model_runtime(self)
        if not observe.enabled:
            raise RuntimeError('lite observation disabled')
        if operation == 'reset':
            return observe.reset()
        if operation == 'export':
            return observe.export()
        raise RuntimeError('invalid lite operation')

    def ready(self):''')
        elif name == 'engine_common.py':
            after = replace(after, '        handlers = []\n        for stage in self.workers:', '''        handlers = []
        metadata = None
        if observe.enabled and func_name in ('step_llm', 'step_encoding', 'migrate_blocks_context', 'migrate_blocks_encoding'):
            metadata = observe.worker_metadata(func_name, args)
            observe.mark('engine.dispatch', **metadata)
        for stage in self.workers:''')
            after = replace(after, 'handlers.append(getattr(worker, func_name).remote(*args))', '''if metadata is None:
                    handlers.append(getattr(worker, func_name).remote(*args))
                else:
                    handlers.append(getattr(worker, func_name).remote(*args, repro_meta=metadata))''')
        elif name == 'api_server.py':
            after = replace(after, 'observe.install_api(app)', 'observe.install_api(app, lambda: engine)')
        else:
            after = replace(after, 'max_num_seqs=8,', 'max_num_seqs=8,\n                                    max_model_len=4096,\n                                    max_num_batched_tokens=4096,\n                                    enable_prefix_caching=False,')
        compile(after, str(path), 'exec')
        pending.append((path, after))
        diff.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=name + '.profile-a', tofile=name + '.revision'))
    path = ROOT / 'scripts/baseline_server.py'
    before = path.read_text()
    after = replace(before, 'observe.install_api(app)', 'observe.install_api(app, lambda: engine)')
    after = replace(after, 'limit_mm_per_prompt={"image": 4}', 'limit_mm_per_prompt={"image": 8}')
    compile(after, str(path), 'exec')
    pending.append((path, after))
    diff.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='baseline.profile-a', tofile='baseline.revision'))
    for path, text in pending:
        path.write_text(text, encoding='utf-8')
    patch.write_text(''.join(diff), encoding='utf-8')
    print(json.dumps({'local_source_adapted': True, 'files': len(pending)}))


if __name__ == '__main__':
    run()
