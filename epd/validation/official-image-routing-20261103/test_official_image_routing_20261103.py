"""Exercise the actual handler prefix with CPU fixtures; never import model code."""
import ast
import asyncio
import base64
import copy
import difflib
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
OLD = '[load_image_cache(ps[0])] * len(ps)'
NEW = '[load_image_cache(path) for path in ps]'


def handler(source):
    node = next(n for n in ast.parse(source).body
                if isinstance(n, ast.AsyncFunctionDef) and n.name == 'generate')
    node.decorator_list = []
    node.returns = None
    for argument in node.args.args:
        argument.annotation = None
    prefix = []
    for statement in node.body:
        if isinstance(statement, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == 'sampling_params'
                for t in statement.targets):
            break
        prefix.append(statement)
    else:
        raise AssertionError('sampling_params boundary missing')
    node.body = prefix + [ast.Return(value=ast.Name(id='input_dict', ctx=ast.Load()))]
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    namespace = {'logger': SimpleNamespace(info=lambda *_: None),
                 'load_image_cache': lambda path: 'CPU_FIXTURE:' + path}
    exec(compile(module, '<official-handler-prefix>', 'exec'), namespace)
    return namespace['generate']


async def route(function, paths):
    payload = {'stream': False, 'input': {'prompt': 'fixture',
               'multi_modal_data': {'images_paths': paths}}}

    async def request_json():
        return copy.deepcopy(payload)

    result = await function(SimpleNamespace(json=request_json))
    return result['multi_modal_data']['image']


async def main():
    baseline = json.loads((ROOT / 'official-three-handlers-source-20261103.json').read_text(encoding='utf-8-sig'))
    for item in baseline['source_files']:
        raw = base64.b64decode(item['base64'])
        assert len(raw) == item['bytes']
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
    sources = {item['path']: base64.b64decode(item['base64'])
               for item in baseline['source_files'] if item['path'].endswith('/api_server.py')}
    assert len(sources) == 3
    patch, results = [], []
    for path, raw in sorted(sources.items()):
        source = raw.decode('utf-8')
        assert source.count(OLD) == 1, path
        fixed = source.replace(OLD, NEW)
        before, after = handler(source), handler(fixed)
        paths = ['A.jpg', 'B.jpg', 'C.jpg', 'D.jpg']
        expected = ['CPU_FIXTURE:' + path for path in paths]
        original = await route(before, paths)
        corrected = await route(after, paths)
        assert original != expected
        assert corrected == expected
        assert await route(before, paths[:1]) == await route(after, paths[:1])
        parallel = await asyncio.gather(route(after, ['A.jpg']), route(after, ['B.jpg']))
        assert parallel == [['CPU_FIXTURE:A.jpg'], ['CPU_FIXTURE:B.jpg']]
        patch.extend(difflib.unified_diff(source.splitlines(True), fixed.splitlines(True),
                     fromfile='a/' + path, tofile='b/' + path))
        results.append({'path': path, 'source_sha256': hashlib.sha256(raw).hexdigest(),
                        'patched_sha256': hashlib.sha256(fixed.encode()).hexdigest(),
                        'original': original, 'expected': expected, 'patched': corrected,
                        'single_image_unchanged': True, 'concurrent_fixture_passed': True})
    (ROOT / 'official-three-handlers-image-routing-20261103.patch').write_text(''.join(patch), encoding='utf-8', newline='')
    report = {'official_commit': baseline['official_commit'], 'handlers': results,
              'scope': 'Actual AST handler prefixes; synthetic loader/request only. No imports, HTTP, image decoding or GPU.',
              'applied_to_server': False, 'gpu_operations': 0}
    (ROOT / 'official-three-handlers-image-routing-cpu-20261103.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('PASS: three original routing failures reproduced; three patched prefixes, single-image and concurrent fixtures passed. Server source unchanged.')


if __name__ == '__main__':
    asyncio.run(main())
