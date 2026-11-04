"""CPU-only fake API tests for concurrency, result binding, failure retention and metrics."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import time

BASE = Path("/local/boyjiang/epd/assets/build")
ROOT = Path("/local/boyjiang/epd/runs") / ("cpu-c4-client-" + str(time.time_ns()))
ROOT.mkdir()
images = []
for index in range(4):
    path = ROOT / (str(index) + ".jpg")
    path.write_bytes(bytes([index + 1]))
    images.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
(ROOT / "images.json").write_text(json.dumps(images))
template = {"input": {"prompt": "CPU-only synthetic template", "multi_modal_data": {"images_paths": [images[0]["path"]]}},
            "max_tokens": 128, "stream": False}
(ROOT / "template.json").write_text(json.dumps(template))

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        index = int(Path(payload["input"]["multi_modal_data"]["images_paths"][0]).stem)
        issued = time.perf_counter()
        with self.server.lock:
            self.server.received.append(index)
        self.server.barrier.wait(timeout=5)
        time.sleep(.16)
        if self.server.mode == "http500" and index == 2:
            status, result = 500, {"error": "intentional CPU fixture"}
        else:
            status = 200
            result = {"output": "image" + str(index),
                      "timestamps": [issued + .01 + token * .001 for token in range(128)],
                      "lifetime_events": [] if self.server.mode == "missing-issued" and index == 2
                                         else [{"event_type": "issued", "timestamp": issued}],
                      "prompt_token_len": 28, "processed_prompt_token_len": 93}
        body = json.dumps(result).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

cases = []
for mode in ["ok", "http500", "missing-issued"]:
    run = ROOT / mode
    run.mkdir()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.mode, server.received = mode, []
    server.barrier, server.lock = threading.Barrier(4), threading.Lock()
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        command = ["/usr/bin/python3", "-I", "-S", "-B", str(BASE / "official_c4_client.py"),
                   "--endpoint", "http://127.0.0.1:" + str(server.server_port) + "/generate",
                   "--template", str(ROOT / "template.json"), "--images", str(ROOT / "images.json"),
                   "--run", str(run), "--deadline-epoch", str(time.time() + 20)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=25)
        (run / "client.stdout").write_text(result.stdout)
        (run / "client.stderr").write_text(result.stderr)
        batch = json.loads((run / "batch-result.json").read_text())
        assert sorted(server.received) == list(range(4))
        assert batch["observed_peak_inflight"] == 4 and len(batch["requests"]) == 4
        assert all((run / ("client-" + str(i) + ".intent.json")).exists() and
                   (run / ("client-" + str(i) + ".record.json")).exists() and
                   (run / ("client-" + str(i) + ".response.json")).exists() for i in range(4))
        expected_successes = 3 if mode == "http500" else 4
        assert batch["successes"] == expected_successes
        assert result.returncode == (0 if mode == "ok" else 1)
        for record in batch["requests"]:
            index = record["index"]
            if not (mode == "http500" and index == 2):
                assert record["output"] == "image" + str(index)
            if record["metrics_complete"]:
                assert abs(record["server_ttft_s"] - .01) < 1e-8
                assert abs(record["server_tpot_s"] - .001) < 1e-8
        if mode == "http500":
            assert batch["requests"][2]["http_code"] == 500 and not batch["requests"][2]["success"]
        if mode == "missing-issued":
            assert batch["requests"][2]["success"] and not batch["requests"][2]["metrics_complete"]
            assert batch["requests"][2]["server_ttft_s"] is None
        cases.append({"mode": mode, "client_exit": result.returncode, "successes": batch["successes"],
                      "peak_inflight": batch["observed_peak_inflight"], "all_four_intents_terminals_and_raw_responses_preserved": True})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()
record = {"CPU_only": True, "synthetic_HTTP_not_model": True, "target_packages_imported": False,
          "GPU_executed": False, "test_root": str(ROOT), "cases": cases,
          "client_sha256": hashlib.sha256((BASE / "official_c4_client.py").read_bytes()).hexdigest()}
result_path = BASE / ("official-c4-client-cpu-result-" + str(time.time_ns()) + ".json")
with result_path.open("x") as stream:
    stream.write(json.dumps(record, indent=2))
print(json.dumps(record), flush=True)
