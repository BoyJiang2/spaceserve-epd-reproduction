"""Four different single-image OpenAI requests; correctness diagnostic only."""
import base64
import ctypes
import os
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import threading
import time
import urllib.error
import urllib.request

IMAGES = [
    ("000328", "cc5ceef6348a3d73d5742fc2fe8b3ad3636de1cdaa8b7ca18e5fee83335e93d6"),
    ("000400", "ce04b38a2be66569e8b632197188bada2b38be12bb010ae4f8f2b523b8c50510"),
    ("000623", "802fb23e9766bc23ef9325afc05790b6d41a59f5055aad248b331ed7f8eb3b9a"),
    ("001146", "a05cd4f6d877f70c23da81d554d6435f18b179b6efe1553d37387d82e9c27059"),
]


def save(path, value):
    with path.open("x") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    endpoint, directory = sys.argv[1:]
    assert endpoint.startswith("http://127.0.0.1:")
    run = Path(directory)
    template = json.loads((run / "request.json").read_text())
    assert template["stream"] is False and template["max_tokens"] == 128
    assert template["ignore_eos"] is True and template["temperature"] == 0
    inputs = []
    for index, (suffix, digest) in enumerate(IMAGES):
        image = Path("/local/boyjiang/epd/assets/dataset/COCO_val2014_000000" + suffix + ".jpg")
        raw = image.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
        payload = copy.deepcopy(template)
        payload["messages"][0]["content"][0]["image_url"]["url"] = "data:image/jpeg;base64," + base64.b64encode(raw).decode()
        encoded = (json.dumps(payload, ensure_ascii=False) + "\n").encode()
        (run / f"client-{index}.request.json").open("xb").write(encoded)
        intent = dict(index=index, image_sha256=digest, image_bytes=len(raw),
                      request_sha256=hashlib.sha256(encoded).hexdigest(),
                      endpoint=endpoint, intent_epoch=time.time())
        save(run / f"client-{index}.intent.json", intent)
        inputs.append((encoded, intent))
    lock, barrier = threading.Lock(), threading.Barrier(5)
    active, peak = 0, 0
    records = [None] * 4

    def request(index):
        nonlocal active, peak
        encoded, intent = inputs[index]
        record = dict(intent, success=False, metrics_complete=False,
                      client_ttft_s=None, server_ttft_s=None, server_tpot_s=None,
                      actual_visual_tokens=None, actual_output_tokens=None)
        barrier.wait()
        with lock:
            active += 1
            peak = max(peak, active)
        start = time.perf_counter()
        record["submitted_epoch"] = time.time()
        completed = None
        try:
            req = urllib.request.Request(endpoint, data=encoded, headers={"Content-Type": "application/json"})
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            try:
                response = opener.open(req, timeout=110)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                body = response.read()
                completed = time.perf_counter()
                record["completed_epoch"] = time.time()
                record["http_code"] = response.status
                record["response_headers"] = dict(response.headers)
            (run / f"client-{index}.response.json").open("xb").write(body)
            result = json.loads(body)
            assert record["http_code"] == 200, record["http_code"]
            assert len(result["choices"]) == 1
            output = result["choices"][0]["message"]["content"]
            count = result["usage"]["completion_tokens"]
            record.update(output=output, usage=result["usage"],
                          actual_output_tokens=count, finish_reason=result["choices"][0]["finish_reason"])
            assert isinstance(output, str) and output.strip()
            assert type(count) is int and count == 128
            record["success"] = True
        except Exception as error:
            record["error"] = repr(error)
        finally:
            if completed is None:
                completed = time.perf_counter()
                record["completed_epoch"] = time.time()
            record["client_e2e_s"] = completed - start
            record["metrics_complete"] = math.isfinite(record["client_e2e_s"]) and record["client_e2e_s"] >= 0
            with lock:
                active -= 1
            save(run / f"client-{index}.record.json", record)
            records[index] = record

    marker = ctypes.CDLL("/local/boyjiang/spaceserve/assets/envs/space/lib/python3.10/site-packages/nvidia/nvtx/lib/libnvToolsExt.so.1")
    marker.nvtxRangePushA.argtypes = [ctypes.c_char_p]
    marker.nvtxRangePushA.restype = ctypes.c_int
    marker.nvtxRangePop.argtypes = []
    marker.nvtxRangePop.restype = ctypes.c_int
    label = "SPACESERVE_C4_REQUEST_WINDOW"
    started = time.time()
    marker.nvtxRangePushA(label.encode())
    try:
        threads = [threading.Thread(target=request, args=(i,)) for i in range(4)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()
    finally:
        marker.nvtxRangePop()
        save(run / "request-window.json", dict(label=label, pid=os.getpid(),
             started_epoch=started, ended_epoch=time.time(),
             scope="client request tasks; trace NVTX range required for GPU alignment"))
    successes = sum(bool(r and r["success"]) for r in records)
    batch = dict(diagnostic_not_formal=True, started_epoch=started, ended_epoch=time.time(),
                 successes=successes, concurrency_target=4, observed_peak_inflight=peak, requests=records,
                 metric_definitions={"client_e2e_s": "HTTP submit through complete buffered response",
                     "metrics_complete": "finite client E2E only; TTFT/TPOT not available",
                     "observed_peak_inflight": "client HTTP requests only, not GPU overlap"})
    save(run / "batch-result.json", batch)
    print(json.dumps(dict(successes=successes, observed_peak_inflight=peak)), flush=True)
    raise SystemExit(0 if successes == 4 and peak == 4 else 1)


if __name__ == "__main__":
    main()
