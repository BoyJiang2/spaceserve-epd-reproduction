"""Real POSIX client timeout; reconcile unknown outcomes and preserve existing bytes."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time

BASE = Path("/local/boyjiang/epd/assets/build")
ROOT = Path("/local/boyjiang/epd/runs") / ("cpu-c4-timeout-" + str(time.time_ns()))
ROOT.mkdir()
images = []
for index in range(4):
    path = ROOT / (str(index) + ".jpg")
    path.write_bytes(bytes([index + 1]))
    images.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
(ROOT / "images.json").write_text(json.dumps(images))
(ROOT / "template.json").write_text(json.dumps({"input": {"prompt": "synthetic CPU fixture",
    "multi_modal_data": {"images_paths": [images[0]["path"]]}}, "max_tokens": 128, "stream": False}))
run = ROOT / "client"
run.mkdir()
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_POST(self):
        with self.server.lock:
            self.server.active += 1
        try:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            index = int(Path(payload["input"]["multi_modal_data"]["images_paths"][0]).stem)
            issued = time.perf_counter()
            self.server.barrier.wait(timeout=5)
            time.sleep(.16 if index == 0 else 2)
            body = json.dumps({"output": "image" + str(index),
                "timestamps": [issued + .01 + i * .001 for i in range(128)],
                "lifetime_events": [{"event_type": "issued", "timestamp": issued}],
                "prompt_token_len": 28, "processed_prompt_token_len": 93}).encode()
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Expected CPU-fixture client termination, not process cleanup.
        finally:
            with self.server.lock:
                self.server.active -= 1

server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
server.barrier, server.lock, server.active = threading.Barrier(4), threading.Lock(), 0
thread = threading.Thread(target=server.serve_forever)
thread.start()
try:
    environment = dict(os.environ, RUN=str(run), CLIENT=str(BASE / "official_c4_client.py"),
                       FINALIZER=str(BASE / "official_c4_finalize.py"),
                       ENDPOINT="http://127.0.0.1:" + str(server.server_port) + "/generate",
                       TEMPLATE=str(ROOT / "template.json"), IMAGES=str(ROOT / "images.json"),
                       DEADLINE=str(time.time() + 10))
    # The same if/exit-save/finalize/test ordering used by the GPU runners.
    command = """set -euo pipefail
if timeout --signal=TERM --kill-after=1s .7s /usr/bin/python3 -I -S -B "$CLIENT" --endpoint "$ENDPOINT" --template "$TEMPLATE" --images "$IMAGES" --run "$RUN" --deadline-epoch "$DEADLINE"; then
  client_rc=0
else
  client_rc=$?
fi
echo "$client_rc" >"$RUN/client.exit"
# Inject a truncated terminal after the killed client to test preservation.
echo -n '{"index":1,' >"$RUN/client-1.record.json"
sha256sum "$RUN/client-0.record.json" "$RUN/client-1.record.json" >"$RUN/before.sha256"
/usr/bin/python3 -I -S -B "$FINALIZER" "$RUN" "$client_rc" >"$RUN/finalization.stdout" 2>"$RUN/finalization.stderr"
test "$client_rc" = 0
echo BAD_UNREACHABLE >"$RUN/should-not-exist"
"""
    result = subprocess.run(["bash", "-c", command], env=environment, capture_output=True, text=True, timeout=8)
    (ROOT / "wrapper.stdout").write_text(result.stdout)
    (ROOT / "wrapper.stderr").write_text(result.stderr)
    assert result.returncode == 1 and (run / "client.exit").read_text().strip() == "124"
    assert not (run / "should-not-exist").exists() and not (run / "batch-result.json").exists()
    summary = json.loads((run / "client-finalization.json").read_text())
    assert summary["client_process_exit"] == 124 and summary["incomplete_indices"] == [1, 2, 3]
    assert not summary["measurement_accepted"]
    checked = subprocess.run(["sha256sum", "-c", str(run / "before.sha256")], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr
    assert all((run / ("client-" + str(i) + ".intent.json")).exists() for i in range(4))
    for index in [1, 2, 3]:
        row = json.loads((run / ("client-" + str(index) + ".recovery-record.json")).read_text())
        assert row["http_code"] is None and row["completed_perf"] is None and row["completed_epoch"] is None
        assert row["server_ttft_s"] is None and row["server_tpot_s"] is None and not row["success"]
    until = time.monotonic() + 4
    while server.active and time.monotonic() < until:
        time.sleep(.02)
    assert server.active == 0
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
    assert not thread.is_alive()
record = {"CPU_only": True, "GPU_executed": False, "actual_POSIX_timeout_client_exit": 124,
          "wrapper_exit_after_finalization": result.returncode, "set_e_did_not_skip_finalization": True,
          "existing_success_and_truncated_terminal_bytes_preserved": True,
          "synthetic_partial_terminal_injected_after_timeout": True,
          "four_intents_and_four_reconciled_outcomes": True, "unknown_metrics_are_null": True,
          "test_root": str(ROOT), "finalizer_sha256": hashlib.sha256((BASE / "official_c4_finalize.py").read_bytes()).hexdigest()}
path = BASE / ("official-c4-timeout-result-" + str(time.time_ns()) + ".json")
with path.open("x") as stream:
    json.dump(record, stream, indent=2)
print(json.dumps(record), flush=True)
