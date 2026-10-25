"""Patch only the dedicated profiling copy; keep an exact before/after diff."""
import ast
import difflib
import pathlib
import sys

if not __debug__:
    raise RuntimeError('instrumentation requires Python assertions; do not use -O')

root = pathlib.Path(sys.argv[1]).resolve()
assert root.name == 'epd-profile-a-20261023'
source = root / 'src/epdserve/epdserve'
changes = []
pending = []
assert not (root / 'instrumentation.patch').exists(), 'already instrumented'


def edit(path, transform):
    before = path.read_text(encoding='utf-8')
    after = transform(before)
    compile(after, str(path), 'exec')
    pending.append((path, after))
    changes.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=str(path) + '.before', tofile=str(path)))


def once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def decorators(text, names):
    assert 'import observe' not in text
    tree = ast.parse(text)
    lines = text.splitlines(True)
    positions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            first = min([node.lineno] + [item.lineno for item in node.decorator_list])
            indent = ' ' * node.col_offset
            positions.append((first - 1, indent + f'@observe.call("{node.name}")\n'))
    assert len(positions) == len(names)
    for index, line in sorted(positions, reverse=True):
        lines.insert(index, line)
    return 'import observe\n' + ''.join(lines)


edit(source / 'worker.py', lambda text: decorators(text, ['step_llm', 'step_encoding', 'migrate_blocks_context', 'migrate_blocks_encoding']))
edit(source / 'engine_common.py', lambda text: decorators(text, ['_remote_call_all_workers_async']))
for filename, names in [('engine_encoding.py', []), ('engine_context.py', ['_migrate_blocks_encoding']), ('engine_decoding.py', ['_migrate_blocks_context'])]:
    def engine(text, names=names):
        text = decorators(text, names)
        return once(text, '            batched_requests.start_one_iteration(time.perf_counter())', '''            if observe.enabled:
                observe.mark('engine.batch', component=type(self).__name__, request_ids=list(map(str, batched_requests.get_request_ids())), batch=len(batched_requests))
            batched_requests.start_one_iteration(time.perf_counter())''')
    edit(source / filename, engine)


def orchestrator(text):
    text = 'import observe\n' + text
    return once(text, '        if dont_add_if_dup and \\', '''        if observe.enabled:
            observe.mark('lifetime', request_id=str(request_id), event=event.event_type.value, event_stamp=event.timestamp)
        if dont_add_if_dup and \\''')


edit(source / 'orchestrator.py', orchestrator)


def epd_api(text):
    text = 'import observe\n' + text
    text = once(text, '@app.post("/generate")', 'observe.install_api(app)\n\n@app.post("/generate")')
    text = once(text, '        if await request.is_disconnected():', '''        if observe.enabled:
            with observe.span('api.disconnect', rid=str(request_id), token=len(final_outputs)):
                disconnected = await request.is_disconnected()
        else:
            disconnected = await request.is_disconnected()
        if disconnected:''')
    text = once(text, '        final_outputs.append((step_output, time.perf_counter()))', '''        final_outputs.append((step_output, time.perf_counter()))
        if observe.enabled:
            observe.mark('api.output', rid=str(request_id), token=len(final_outputs), api_stamp=final_outputs[-1][1], callback_stamp=step_output.timestamp)''')
    return once(text, '        "timestamps": [step_output[1] for step_output in final_outputs],', '        "repro_request_id": str(request_id),\n        "timestamps": [step_output[1] for step_output in final_outputs],')


edit(source / 'api_server.py', epd_api)


def baseline(text):
    text = once(text, '    engine = AsyncLLMEngine.from_engine_args(engine_args)', '''    import observe
    if observe.enabled:
        from vllm.worker.worker import Worker
        Worker.execute_model = observe.call('baseline.execute_model')(Worker.execute_model)
    engine = AsyncLLMEngine.from_engine_args(engine_args)''')
    text = once(text, '    @app.get("/health")', '    observe.install_api(app)\n\n    @app.get("/health")')
    text = once(text, '        async for output in engine.generate(prompt, sampling, uuid.uuid4().hex):', '''        repro_id = uuid.uuid4().hex
        async for output in engine.generate(prompt, sampling, repro_id):''')
    text = once(text, '            previous_count = token_count', '''            if observe.enabled:
                observe.mark('api.output', rid=repro_id, token=token_count, api_stamp=timestamps[-1])
            previous_count = token_count''')
    return once(text, '        return JSONResponse({"output": final.outputs[0].text,', '        return JSONResponse({"repro_request_id": repro_id, "output": final.outputs[0].text,')


edit(root / 'scripts/baseline_server.py', baseline)
for path, after in pending:
    path.write_text(after, encoding='utf-8')
(root / 'instrumentation.patch').write_text(''.join(changes), encoding='utf-8')
print('Dedicated copy instrumented; no CUDA communication or sampling changes')
