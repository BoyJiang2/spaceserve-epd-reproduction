import ast
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
path = root / "src/epdserve/epdserve/api_server.py"
before = path.read_text()
(root / "tmp/api-before-ready-probe.py").write_text(before)
old = "    async def main_coroutine():\n        task2 = asyncio.create_task(uvicorn_server.serve())"
new = '''    async def main_coroutine():
        # Complete Ray worker readiness on the event loop serving requests.
        ready_refs = []
        for cluster in (engine.orchestrator.encoding_cluster,
                        engine.orchestrator.context_cluster,
                        engine.orchestrator.decoding_cluster):
            for stage_engine in cluster.engines:
                for stage_workers in stage_engine.workers:
                    ready_refs.extend(worker.ready.remote() for worker in stage_workers)
        await asyncio.gather(*ready_refs)
        task2 = asyncio.create_task(uvicorn_server.serve())'''
assert before.count(old) == 1
after = before.replace(old, new)
ast.parse(after)
path.write_text(after)
