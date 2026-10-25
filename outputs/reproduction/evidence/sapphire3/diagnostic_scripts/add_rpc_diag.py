import ast
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
path = root / "src/epdserve/epdserve/api_server.py"
before = path.read_text()
(root / "tmp/api-before-rpc-diag.py").write_text(before)
diagnostic = '''
@app.get("/repro/worker-times")
async def repro_worker_times():
    result = {}
    for name in ("encoding", "context", "decoding"):
        cluster = getattr(engine.orchestrator, name + "_cluster")
        worker = cluster.engines[0].workers[0][0]
        execution_time = await worker.self.remote("execution_time")
        started = time.perf_counter()
        for _ in range(10):
            gpu_id = await worker.self.remote("gpu_id")
        result[name] = {"gpu_id": gpu_id, "execution_time_s": execution_time,
                        "ten_echo_rpc_s": time.perf_counter() - started}
    return JSONResponse(result)

'''
marker = 'if __name__ == "__main__":'
assert before.count(marker) == 1
after = before.replace(marker, diagnostic + marker)
ast.parse(after)
path.write_text(after)
